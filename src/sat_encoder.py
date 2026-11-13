"""SAT Encoder for the Antibandwidth Problem (ABP).

Encodes the problem of finding a bijective labeling f: V -> {1, ..., n}
such that for every edge (u, v) in E, |f(u) - f(v)| >= k into CNF.
"""

from typing import Any, Dict, List, Optional, Tuple, Set
import networkx as nx

try:
    from pysat.formula import CNF
    from pysat.card import CardEnc, EncType
    HAS_PYSAT_CARD = True
except ImportError:
    HAS_PYSAT_CARD = False
    # Minimal fallback CNF container if python-sat is not installed yet
    class CNF:
        def __init__(self):
            self.clauses = []
            self.nv = 0

        def append(self, clause):
            self.clauses.append(clause)
            for lit in clause:
                self.nv = max(self.nv, abs(lit))

        def extend(self, clauses):
            for c in clauses:
                self.append(c)

        def to_dimacs(self):
            out = [f"p cnf {self.nv} {len(self.clauses)}"]
            for c in self.clauses:
                out.append(" ".join(map(str, c)) + " 0")
            return "\n".join(out)


SUPPORTED_AMO_ENCODINGS = (
    "pairwise",
    "seqcounter",
    "commander",
    "totalizer",
    "ladder",
    "bitwise",
)


class AntibandwidthSATEncoder:
    """Encodes the Antibandwidth decision problem for a graph G and target k into CNF."""

    def __init__(
        self,
        graph: nx.Graph,
        break_symmetry: bool = True,
        amo_encoding: str = "pairwise",
    ):
        """
        Args:
            graph: Undirected NetworkX graph.
            break_symmetry: If True, adds symmetry-breaking constraints to eliminate
                            reflection symmetry (f(v) vs n + 1 - f(v)).
            amo_encoding: At-Most-One constraint encoding for bijectivity:
                          'pairwise' (O(n^2) clauses per constraint, no aux vars),
                          'seqcounter' (Sequential Counter via PySAT CardEnc, O(n) clauses),
                          'commander' (Commander grouping AMO, O(n) clauses),
                          'totalizer', 'ladder', or 'bitwise' (via PySAT CardEnc).
        """
        amo_key = amo_encoding.lower()
        if amo_key not in SUPPORTED_AMO_ENCODINGS:
            raise ValueError(
                f"Unsupported amo_encoding '{amo_encoding}'. "
                f"Choose from: {', '.join(SUPPORTED_AMO_ENCODINGS)}"
            )

        self.graph = graph
        self.nodes = list(graph.nodes())
        self.n = len(self.nodes)
        self.break_symmetry = break_symmetry
        self.amo_encoding = amo_key

        # Map graph nodes to internal 0-based indices [0, n-1] for robustness
        self.node_to_idx = {node: idx for idx, node in enumerate(self.nodes)}
        self.idx_to_node = {idx: node for idx, node in enumerate(self.nodes)}

        # Internal edges stored as pairs of indices in [0, n-1]
        self.edges = [
            (self.node_to_idx[u], self.node_to_idx[v])
            for u, v in graph.edges()
            if u in self.node_to_idx and v in self.node_to_idx
        ]

        # Pick vertex with highest degree for symmetry breaking
        if self.n > 0:
            degrees = dict(graph.degree())
            self.pivot_node = max(degrees, key=degrees.get)
            self.pivot_vertex = self.node_to_idx[self.pivot_node]
        else:
            self.pivot_node = 0
            self.pivot_vertex = 0

    def var(self, v: int, p: int) -> int:
        """Map vertex v in [0, n-1] and position p in [1, n] to a 1-based SAT variable.

        Index formula: v * n + p
        """
        assert 0 <= v < self.n, f"Vertex {v} out of range [0, {self.n - 1}]"
        assert 1 <= p <= self.n, f"Position {p} out of range [1, {self.n}]"
        return v * self.n + p

    def decode_var(self, lit: int) -> Tuple[int, int]:
        """Convert a positive SAT variable back to (vertex_index, position)."""
        idx = abs(lit) - 1
        v = idx // self.n
        p = (idx % self.n) + 1
        return v, p

    @staticmethod
    def _add_pairwise_amo(cnf: CNF, lits: List[int]) -> None:
        """Add pairwise At-Most-One clauses for a literal list: O(m^2) clauses, 0 aux vars."""
        m = len(lits)
        for i in range(m):
            for j in range(i + 1, m):
                cnf.append([-lits[i], -lits[j]])

    def _add_commander_amo(self, cnf: CNF, lits: List[int], top_id: int, group_size: int = 3) -> int:
        """Add Commander At-Most-One encoding (Klieber & Kwon, 2007): O(m) clauses & aux vars."""
        if len(lits) <= group_size:
            self._add_pairwise_amo(cnf, lits)
            return top_id

        commanders: List[int] = []
        for idx in range(0, len(lits), group_size):
            group = lits[idx : idx + group_size]
            if len(group) == 1:
                commanders.append(group[0])
                continue

            top_id += 1
            cmd = top_id
            commanders.append(cmd)

            # At most one literal in the group can be True
            self._add_pairwise_amo(cnf, group)
            # cmd <=> OR(group): (x -> cmd) and (cmd -> OR(group))
            for lit in group:
                cnf.append([-lit, cmd])
            cnf.append([-cmd] + group)

        return self._add_commander_amo(cnf, commanders, top_id, group_size=group_size)

    def _add_amo(self, cnf: CNF, lits: List[int], top_id: int) -> int:
        """Encode At-Most-One constraint on `lits` using the configured `amo_encoding`."""
        if len(lits) <= 1:
            return top_id

        if self.amo_encoding == "pairwise":
            self._add_pairwise_amo(cnf, lits)
            return top_id

        if self.amo_encoding == "commander":
            return self._add_commander_amo(cnf, lits, top_id)

        if not HAS_PYSAT_CARD:
            raise RuntimeError(
                f"python-sat is required for amo_encoding='{self.amo_encoding}'. "
                "Run: pip install python-sat"
            )

        enc_map = {
            "seqcounter": EncType.seqcounter,
            "totalizer": EncType.totalizer,
            "ladder": EncType.ladder,
            "bitwise": EncType.bitwise,
        }
        card_cnf = CardEnc.atmost(
            lits=lits,
            bound=1,
            top_id=top_id,
            encoding=enc_map[self.amo_encoding],
        )
        cnf.extend(card_cnf.clauses)
        return max(top_id, card_cnf.nv)

    def encode(self, k: int) -> CNF:
        """Construct the CNF formula for the antibandwidth target k.

        Args:
            k: The desired minimum bandwidth distance between adjacent vertices.

        Returns:
            CNF formula object.
        """
        cnf = CNF()
        n = self.n

        if n <= 1:
            return cnf

        top_id = n * n

        # -------------------------------------------------------------
        # 1. Bijective mapping constraints
        # -------------------------------------------------------------
        # 1a. At-least-one (ALO) position for each vertex v
        for v in range(n):
            cnf.append([self.var(v, p) for p in range(1, n + 1)])

        # 1b. At-most-one (AMO) position for each vertex v
        for v in range(n):
            vertex_lits = [self.var(v, p) for p in range(1, n + 1)]
            top_id = self._add_amo(cnf, vertex_lits, top_id)

        # 1c. At-most-one (AMO) vertex for each position p
        for p in range(1, n + 1):
            pos_lits = [self.var(u, p) for u in range(n)]
            top_id = self._add_amo(cnf, pos_lits, top_id)

        # -------------------------------------------------------------
        # 2. Antibandwidth Distance Constraints:
        # For each edge (u, v) in E: |p(u) - p(v)| >= k
        # Equivalent to: NOT (u at p AND v at q) whenever |p - q| < k
        # When k <= 1, |p(u) - p(v)| >= 1 is trivially satisfied by AMO.
        # -------------------------------------------------------------
        if k > 1:
            for u, v in self.edges:
                for p in range(1, n + 1):
                    min_q = max(1, p - k + 1)
                    max_q = min(n, p + k - 1)
                    for q in range(min_q, max_q + 1):
                        if p != q:
                            cnf.append([-self.var(u, p), -self.var(v, q)])

        # -------------------------------------------------------------
        # 3. Symmetry Breaking Constraints (Optional):
        # Antibandwidth is symmetric under reflection p -> (n + 1 - p).
        # We enforce pivot vertex to be placed in the first half:
        # pos(pivot) <= ceil(n / 2)
        # -------------------------------------------------------------
        if self.break_symmetry and n >= 2:
            half = (n + 1) // 2
            for p in range(half + 1, n + 1):
                cnf.append([-self.var(self.pivot_vertex, p)])

        cnf.nv = max(getattr(cnf, "nv", 0), top_id)
        return cnf

    def decode_model(self, model: List[int]) -> Dict[Any, int]:
        """Decode a satisfying SAT assignment into a labeling dictionary {node: position}."""
        labeling = {}
        for lit in model:
            if 0 < lit <= self.n * self.n:
                v_idx, p = self.decode_var(lit)
                orig_node = self.idx_to_node[v_idx]
                labeling[orig_node] = p
        return labeling

    def get_stats(self, k: int) -> Dict[str, Any]:
        """Compute counts of variables and clauses for target k.

        Returns:
            Dictionary with breakdown of variables and clauses.
        """
        n = self.n
        base_vars = n * n
        alo_vertex = n

        if self.amo_encoding == "pairwise":
            num_vars = base_vars
            amo_vertex = n * (n * (n - 1) // 2)
            amo_position = n * (n * (n - 1) // 2)
        else:
            tmp_cnf = CNF()
            top_id = base_vars
            for v in range(n):
                top_id = self._add_amo(tmp_cnf, [self.var(v, p) for p in range(1, n + 1)], top_id)
            amo_vertex = len(tmp_cnf.clauses)
            for p in range(1, n + 1):
                top_id = self._add_amo(tmp_cnf, [self.var(u, p) for u in range(n)], top_id)
            amo_position = len(tmp_cnf.clauses) - amo_vertex
            num_vars = top_id

        num_dist_clauses = 0
        if k > 1:
            for _ in self.edges:
                for p in range(1, n + 1):
                    min_q = max(1, p - k + 1)
                    max_q = min(n, p + k - 1)
                    num_dist_clauses += sum(1 for q in range(min_q, max_q + 1) if p != q)

        sb_clauses = (n - (n + 1) // 2) if (self.break_symmetry and n >= 2) else 0
        total_clauses = alo_vertex + amo_vertex + amo_position + num_dist_clauses + sb_clauses

        return {
            "num_nodes": n,
            "num_edges": len(self.edges),
            "target_k": k,
            "amo_encoding": self.amo_encoding,
            "num_variables": num_vars,
            "aux_variables": num_vars - base_vars,
            "alo_vertex_clauses": alo_vertex,
            "amo_vertex_clauses": amo_vertex,
            "amo_position_clauses": amo_position,
            "distance_clauses": num_dist_clauses,
            "symmetry_breaking_clauses": sb_clauses,
            "total_clauses": total_clauses,
        }

    def export_dimacs(self, k: int, filepath: str) -> None:
        """Export the CNF formula for target k directly to a DIMACS file."""
        cnf = self.encode(k)

        # If python-sat CNF has built-in to_file, use it directly without double-opening
        if hasattr(cnf, "to_file"):
            cnf.to_file(filepath)
            return

        with open(filepath, "w", encoding="utf-8") as f:
            if hasattr(cnf, "to_dimacs"):
                f.write(cnf.to_dimacs())
            else:
                num_vars = getattr(cnf, "nv", self.n * self.n)
                f.write(f"p cnf {num_vars} {len(cnf.clauses)}\n")
                for c in cnf.clauses:
                    f.write(" ".join(map(str, c)) + " 0\n")
