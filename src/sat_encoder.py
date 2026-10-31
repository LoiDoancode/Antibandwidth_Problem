"""SAT Encoder for the Antibandwidth Problem (ABP).

Encodes the problem of finding a bijective labeling f: V -> {1, ..., n}
such that for every edge (u, v) in E, |f(u) - f(v)| >= k into CNF.
"""

from typing import Any, Dict, List, Optional, Tuple, Set
import networkx as nx

try:
    from pysat.formula import CNF
except ImportError:
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


class AntibandwidthSATEncoder:
    """Encodes the Antibandwidth decision problem for a graph G and target k into CNF."""

    def __init__(self, graph: nx.Graph, break_symmetry: bool = True):
        """
        Args:
            graph: Undirected NetworkX graph.
            break_symmetry: If True, adds symmetry-breaking constraints to eliminate
                            reflection symmetry (f(v) vs n + 1 - f(v)).
        """
        self.graph = graph
        self.nodes = list(graph.nodes())
        self.n = len(self.nodes)
        self.break_symmetry = break_symmetry

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

        # -------------------------------------------------------------
        # 1. Bijective mapping constraints
        # -------------------------------------------------------------
        # 1a. At-least-one (ALO) position for each vertex v
        for v in range(n):
            cnf.append([self.var(v, p) for p in range(1, n + 1)])

        # 1b. At-most-one (AMO) position for each vertex v
        for v in range(n):
            for p in range(1, n + 1):
                for q in range(p + 1, n + 1):
                    cnf.append([-self.var(v, p), -self.var(v, q)])

        # 1c. At-most-one (AMO) vertex for each position p
        for p in range(1, n + 1):
            for u in range(n):
                for v in range(u + 1, n):
                    cnf.append([-self.var(u, p), -self.var(v, p)])

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

    def get_stats(self, k: int) -> Dict[str, int]:
        """Compute theoretical counts of variables and clauses for target k.

        Returns:
            Dictionary with breakdown of variables and clauses.
        """
        n = self.n
        num_vars = n * n
        alo_vertex = n
        amo_vertex = n * (n * (n - 1) // 2)
        amo_position = n * (n * (n - 1) // 2)

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
            "num_variables": num_vars,
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
                num_vars = self.n * self.n
                f.write(f"p cnf {num_vars} {len(cnf.clauses)}\n")
                for c in cnf.clauses:
                    f.write(" ".join(map(str, c)) + " 0\n")
