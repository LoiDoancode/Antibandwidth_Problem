"""SAT Encoder for the Antibandwidth Problem (ABP).

Encodes the problem of finding a bijective labeling f: V -> {1, ..., n}
such that for every edge (u, v) in E, |f(u) - f(v)| >= k into CNF.
"""

from typing import Dict, List, Optional, Tuple, Set
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
            graph: Undirected NetworkX graph with vertices 0..n-1.
            break_symmetry: If True, adds symmetry-breaking constraints to eliminate
                            reflection symmetry (f(v) vs n + 1 - f(v)).
        """
        self.graph = graph
        self.n = graph.number_of_nodes()
        self.edges = list(graph.edges())
        self.break_symmetry = break_symmetry

        # Pick vertex with highest degree for symmetry breaking
        if self.n > 0:
            degrees = dict(graph.degree())
            self.pivot_vertex = max(degrees, key=degrees.get)
        else:
            self.pivot_vertex = 0

    def var(self, v: int, p: int) -> int:
        """Map vertex v in [0, n-1] and position p in [1, n] to a 1-based SAT variable.

        Index formula: v * n + p
        """
        assert 0 <= v < self.n, f"Vertex {v} out of range [0, {self.n - 1}]"
        assert 1 <= p <= self.n, f"Position {p} out of range [1, {self.n}]"
        return v * self.n + p

    def decode_var(self, lit: int) -> Tuple[int, int]:
        """Convert a positive SAT variable back to (vertex, position)."""
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
        # -------------------------------------------------------------
        if k > 1:
            for u, v in self.edges:
                for p in range(1, n + 1):
                    # We only need to check positions q where |p - q| < k and p != q
                    # (p == q is already forbidden by AMO vertex per position)
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

    def decode_model(self, model: List[int]) -> Dict[int, int]:
        """Decode a satisfying SAT assignment into a labeling dictionary {vertex: position}."""
        labeling = {}
        for lit in model:
            if lit > 0 and lit <= self.n * self.n:
                v, p = self.decode_var(lit)
                labeling[v] = p
        return labeling

    def export_dimacs(self, k: int, filepath: str) -> None:
        """Export the CNF formula for target k directly to a DIMACS file."""
        cnf = self.encode(k)
        with open(filepath, "w", encoding="utf-8") as f:
            if hasattr(cnf, "to_dimacs"):
                f.write(cnf.to_dimacs())
            elif hasattr(cnf, "to_file"):
                cnf.to_file(filepath)
            else:
                num_vars = self.n * self.n
                f.write(f"p cnf {num_vars} {len(cnf.clauses)}\n")
                for c in cnf.clauses:
                    f.write(" ".join(map(str, c)) + " 0\n")
