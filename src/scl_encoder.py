"""Staircase Sequential Counter (SCL) SAT Encoder for the Antibandwidth Problem.

Implements the SCL (Sequential Counter encoding for Ladder / Staircase At-Most-One)
approach from:
    Truong, H. X., Van Kieu, T., & Van To, K. (2025).
    "Sequential Counter Encoding for Staircase At-Most-One Constraints" (ICAART 2025).

Key ideas:
1. Window-based SCAMO Decomposition:
   The constraint |pos(u) - pos(v)| >= k is equivalent to forbidding adjacent vertices
   (u, v) from both appearing in any sliding window of width w = k consecutive positions.
2. Vertex-level Reuse (Proposition 1 & 2 in the paper):
   Instead of encoding O(|E| * n * k) pairwise edge conflict clauses, we build one
   staircase Sequential Counter per vertex (O(|V| * n) clauses), and connect adjacent
   vertices (u, v) using compact binary At-Most-Zero (AMZ) clauses on window registers.
3. Bijectivity Reuse:
   Subset register bits constructed for SCAMO are reused for vertex uniqueness (LABELS),
   and Sequential Counter AMO is used for position uniqueness (VERTICES).
"""

import math
from typing import Dict, List, Tuple
import networkx as nx
from pysat.formula import CNF
from pysat.card import CardEnc, EncType


class AntibandwidthSCLEncoder:
    """Encodes the Antibandwidth Problem into CNF using Staircase SCL encoding."""

    def __init__(self, graph: nx.Graph, break_symmetry: bool = True):
        """
        Args:
            graph: Undirected NetworkX graph.
            break_symmetry: If True, fixes pivot vertex (highest degree) to pos <= ceil(n/2).
        """
        self.graph = graph
        self.n = graph.number_of_nodes()
        self.nodes = list(graph.nodes())
        self.node_to_idx: Dict[int, int] = {node: idx for idx, node in enumerate(self.nodes)}
        self.idx_to_node: Dict[int, int] = {idx: node for idx, node in enumerate(self.nodes)}
        self.edges: List[Tuple[int, int]] = [
            (self.node_to_idx[u], self.node_to_idx[v]) for u, v in graph.edges()
        ]
        self.break_symmetry = break_symmetry

        if self.n > 0:
            degrees = {self.node_to_idx[v]: deg for v, deg in graph.degree()}
            self.pivot_idx = max(degrees.keys(), key=lambda i: degrees[i])
        else:
            self.pivot_idx = 0

    def var(self, v_idx: int, pos: int) -> int:
        """Map (vertex_idx in 0..n-1, pos in 1..n) -> SAT variable ID (1..n^2)."""
        return v_idx * self.n + pos

    def _build_sc_block(
        self, cnf: CNF, ordered_lits: List[int], top_id: int, is_amo: bool
    ) -> Tuple[List[int], int]:
        """Build a Sequential Counter block for a list of literals.

        Returns:
            (register_bits, new_top_id) where register_bits[j] (0-indexed) represents
            the OR of ordered_lits[0..j].
        """
        m = len(ordered_lits)
        if m == 0:
            return [], top_id
        if m == 1:
            return [ordered_lits[0]], top_id

        reg_bits = [ordered_lits[0]]
        for _ in range(1, m):
            top_id += 1
            reg_bits.append(top_id)

        for j in range(1, m):
            x_j = ordered_lits[j]
            r_prev = reg_bits[j - 1]
            r_curr = reg_bits[j]

            # (1) x_j -> R_j
            cnf.append([-x_j, r_curr])
            # (2) R_{j-1} -> R_j
            cnf.append([-r_prev, r_curr])
            # (3) ~x_j & ~R_{j-1} -> ~R_j
            cnf.append([x_j, r_prev, -r_curr])
            if is_amo:
                # (4) x_j -> ~R_{j-1} (only needed for AMO blocks, not AMZ blocks)
                cnf.append([-x_j, -r_prev])

        return reg_bits, top_id

    def _encode_vertex_staircase(
        self, cnf: CNF, v_idx: int, w: int, top_id: int
    ) -> Tuple[List[int], int]:
        """Build SCL register blocks for vertex v_idx over positions 1..n with width w.

        Returns:
            (window_lits, new_top_id) where each literal in window_lits is True
            whenever vertex v_idx is placed inside that sliding window of width w.
        """
        n = self.n
        pos_lits = [self.var(v_idx, p) for p in range(1, n + 1)]

        # Partition positions into M consecutive chunks of size at most w
        subsets = [pos_lits[i : i + w] for i in range(0, n, w)]
        num_subsets = len(subsets)

        r_left: List[List[int]] = [[] for _ in range(num_subsets)]
        r_right: List[List[int]] = [[] for _ in range(num_subsets)]

        for idx, sub in enumerate(subsets):
            if idx == 0:
                # First subset: only needs right-to-left AMO block
                r_right[idx], top_id = self._build_sc_block(
                    cnf, list(reversed(sub)), top_id, is_amo=True
                )
            elif idx == num_subsets - 1:
                # Last subset: only needs left-to-right AMO block
                r_left[idx], top_id = self._build_sc_block(
                    cnf, sub, top_id, is_amo=True
                )
            else:
                # Middle subset: left-to-right AMO block + right-to-left AMZ block
                r_left[idx], top_id = self._build_sc_block(
                    cnf, sub, top_id, is_amo=True
                )
                # Reuse the top register bit (sum of all variables in sub)
                sub_rev = list(reversed(sub))
                if len(sub_rev) > 1:
                    r_rev = [sub_rev[0]]
                    for _ in range(1, len(sub_rev) - 1):
                        top_id += 1
                        r_rev.append(top_id)
                    r_rev.append(r_left[idx][-1])  # Reuse highest bit!

                    for j in range(1, len(sub_rev)):
                        x_j = sub_rev[j]
                        r_prev = r_rev[j - 1]
                        r_curr = r_rev[j]
                        cnf.append([-x_j, r_curr])
                        cnf.append([-r_prev, r_curr])
                        cnf.append([x_j, r_prev, -r_curr])
                    r_right[idx] = r_rev
                else:
                    r_right[idx] = [sub_rev[0]]

        # Build indicator literal for every sliding window of width w
        window_lits: List[int] = []

        # Full-subset windows (for subsets of full width w, or the only subset)
        for idx in range(num_subsets):
            full_bit = r_right[idx][-1] if idx == 0 else r_left[idx][-1]
            window_lits.append(full_bit)

        # Overlapping windows spanning subset idx and subset idx + 1
        for idx in range(num_subsets - 1):
            next_len = len(subsets[idx + 1])
            max_j = min(w - 1, next_len)
            for j_next in range(1, max_j + 1):
                j_prev = w - j_next
                if j_prev <= 0 or j_prev > len(r_right[idx]):
                    continue
                left_tail = r_right[idx][j_prev - 1]
                right_head = r_left[idx + 1][j_next - 1]

                # Auxiliary window indicator: W <-> (left_tail OR right_head)
                top_id += 1
                w_var = top_id
                cnf.append([-left_tail, w_var])
                cnf.append([-right_head, w_var])
                window_lits.append(w_var)

        return window_lits, top_id

    def encode(self, k: int) -> CNF:
        """Construct the CNF formula for antibandwidth >= k using Staircase SCL."""
        cnf = CNF()
        n = self.n

        if n <= 1:
            return cnf

        top_id = n * n

        # -------------------------------------------------------------
        # 1. Bijective mapping constraints (VERTICES and LABELS)
        # -------------------------------------------------------------
        # 1a. Each vertex v gets at least one position (ALO)
        for v in range(n):
            cnf.append([self.var(v, p) for p in range(1, n + 1)])

        # 1b. Each position p gets at most one vertex (AMO via SeqCounter)
        for p in range(1, n + 1):
            pos_lits = [self.var(u, p) for u in range(n)]
            card_cnf = CardEnc.atmost(
                lits=pos_lits, bound=1, top_id=top_id, encoding=EncType.seqcounter
            )
            cnf.extend(card_cnf.clauses)
            top_id = max(top_id, card_cnf.nv)

        # -------------------------------------------------------------
        # 2. Staircase SCAMO constraints for |pos(u) - pos(v)| >= k
        # -------------------------------------------------------------
        w = min(k, n)
        if w <= 1:
            # When k <= 1, bijectivity already guarantees |pos(u) - pos(v)| >= 1
            for v in range(n):
                v_lits = [self.var(v, p) for p in range(1, n + 1)]
                card_cnf = CardEnc.atmost(
                    lits=v_lits, bound=1, top_id=top_id, encoding=EncType.seqcounter
                )
                cnf.extend(card_cnf.clauses)
                top_id = max(top_id, card_cnf.nv)
        else:
            # Build vertex staircase blocks (also covers AMO inside each subset)
            num_subsets = (n + w - 1) // w
            vertex_windows: List[List[int]] = []
            for v in range(n):
                w_lits, top_id = self._encode_vertex_staircase(cnf, v, w, top_id)
                vertex_windows.append(w_lits)

                # Reuse the M subset OR-bits for LABELS AMO (Section 4.2 of paper)
                subset_full_bits = w_lits[:num_subsets]
                if len(subset_full_bits) > 1:
                    card_cnf = CardEnc.atmost(
                        lits=subset_full_bits, bound=1, top_id=top_id, encoding=EncType.seqcounter
                    )
                    cnf.extend(card_cnf.clauses)
                    top_id = max(top_id, card_cnf.nv)

            # Connect adjacent vertices (u, v) using binary AMZ clauses on windows
            num_windows = len(vertex_windows[0])
            for u, v in self.edges:
                wu = vertex_windows[u]
                wv = vertex_windows[v]
                for idx in range(num_windows):
                    cnf.append([-wu[idx], -wv[idx]])

        # -------------------------------------------------------------
        # 3. Symmetry Breaking: pos[pivot] <= ceil(n / 2)
        # -------------------------------------------------------------
        if self.break_symmetry and n > 1:
            half_pos = (n + 1) // 2
            for p in range(half_pos + 1, n + 1):
                cnf.append([-self.var(self.pivot_idx, p)])

        return cnf

    def decode_model(self, model: List[int]) -> Dict[int, int]:
        """Decode a satisfying SAT assignment back into {vertex: position}."""
        true_vars = {lit for lit in model if lit > 0 and lit <= self.n * self.n}
        labeling: Dict[int, int] = {}

        for v_idx in range(self.n):
            node = self.idx_to_node[v_idx]
            for p in range(1, self.n + 1):
                if self.var(v_idx, p) in true_vars:
                    labeling[node] = p
                    break
        return labeling

    def get_stats(self, k: int) -> Dict[str, int]:
        """Return CNF size statistics for target k."""
        cnf = self.encode(k)
        return {
            "num_vars": cnf.nv,
            "num_clauses": len(cnf.clauses),
        }

    def export_dimacs(self, k: int, filepath: str) -> None:
        """Export the encoded CNF for target k to a DIMACS file."""
        cnf = self.encode(k)
        cnf.to_file(filepath)
