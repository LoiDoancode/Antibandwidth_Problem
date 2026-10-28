"""Order Encoding for the Antibandwidth Problem (ABP).

In Order Encoding (Tamura et al.), each integer variable f(v) in {1, ..., n}
is encoded using n - 1 boolean variables y_{v, p} representing the proposition f(v) <= p:
    y_{v, p} is True  <=>  f(v) <= p  (for 1 <= p <= n - 1)
By convention:
    f(v) <= 0 is identically False.
    f(v) <= n is identically True.

Order encoding typically produces more compact clauses and stronger unit propagation
for distance / interval constraints |f(u) - f(v)| >= k.
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


class AntibandwidthOrderEncoder:
    """Encodes the Antibandwidth decision problem using Order Encoding into CNF."""

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
        """Map vertex v in [0, n-1] and position p in [1, n-1] to a 1-based SAT variable.

        Index formula: v * (n - 1) + p
        """
        assert 0 <= v < self.n, f"Vertex {v} out of range [0, {self.n - 1}]"
        assert 1 <= p <= self.n - 1, f"Position {p} out of range [1, {self.n - 1}]"
        return v * (self.n - 1) + p

    def decode_var(self, lit: int) -> Tuple[int, int]:
        """Convert a positive SAT variable back to (vertex, position)."""
        idx = abs(lit) - 1
        m = self.n - 1
        v = idx // m
        p = (idx % m) + 1
        return v, p

    def encode(self, k: int) -> CNF:
        """Construct the CNF formula for the antibandwidth target k using Order Encoding.

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
        # 1. Monotonicity constraints (Validity of order variables):
        # f(v) <= p implies f(v) <= p + 1:
        # y_{v, p} -> y_{v, p+1}  ===  NOT y_{v, p} OR y_{v, p+1}
        # -------------------------------------------------------------
        for v in range(n):
            for p in range(1, n - 1):
                cnf.append([-self.var(v, p), self.var(v, p + 1)])

        # -------------------------------------------------------------
        # 2. Injective mapping constraints (At-most-one vertex per position):
        # For each position p in {1, ..., n}, at most one vertex takes value p.
        # - For p = 1: f(v) = 1 <=> y_{v, 1}.
        #   AMO: NOT y_{u, 1} OR NOT y_{v, 1} for u < v.
        # - For p = n: f(v) = n <=> NOT y_{v, n-1}.
        #   AMO: y_{u, n-1} OR y_{v, n-1} for u < v.
        # - For 1 < p < n: f(v) = p <=> y_{v, p} AND NOT y_{v, p-1}.
        #   AMO: NOT (f(u) = p AND f(v) = p)
        #        === NOT y_{u, p} OR y_{u, p-1} OR NOT y_{v, p} OR y_{v, p-1}
        # -------------------------------------------------------------
        for u in range(n):
            for v in range(u + 1, n):
                # Position 1
                cnf.append([-self.var(u, 1), -self.var(v, 1)])
                # Position n
                cnf.append([self.var(u, n - 1), self.var(v, n - 1)])
                # Positions 2 .. n-1
                for p in range(2, n):
                    cnf.append([
                        -self.var(u, p),
                        self.var(u, p - 1),
                        -self.var(v, p),
                        self.var(v, p - 1),
                    ])

        # -------------------------------------------------------------
        # 3. Antibandwidth Distance Constraints: |f(u) - f(v)| >= k
        # If f(u) <= p and f(v) > p, then f(v) >= p + k (i.e. NOT y_{v, p+k-1}):
        # (y_{u, p} AND NOT y_{v, p}) -> NOT y_{v, p+k-1}
        # === NOT y_{u, p} OR y_{v, p} OR NOT y_{v, p+k-1}
        # By symmetry, this applies when swapping u and v.
        #
        # For p in [1, n-k]:
        #   NOT y_{u, p} OR y_{v, p} OR NOT y_{v, p+k-1}
        #   NOT y_{v, p} OR y_{u, p} OR NOT y_{u, p+k-1}
        #
        # For boundary positions where |p - q| < k:
        # Also forbid adjacent vertices taking values with difference < k:
        # -------------------------------------------------------------
        if k > 1:
            for u, v in self.edges:
                # Order interval propagation clauses (Tamura et al.)
                for p in range(1, n - k + 1):
                    # u <= p and v > p  ==>  v > p + k - 1
                    cnf.append([-self.var(u, p), self.var(v, p), -self.var(v, p + k - 1)])
                    # v <= p and u > p  ==>  u > p + k - 1
                    cnf.append([-self.var(v, p), self.var(u, p), -self.var(u, p + k - 1)])

                # Also enforce direct pairwise window exclusions for values |p - q| < k
                for p in range(1, n + 1):
                    min_q = max(1, p - k + 1)
                    max_q = min(n, p + k - 1)
                    for q in range(min_q, max_q + 1):
                        if p < q:
                            # Cannot have (f(u) == p AND f(v) == q) or (f(u) == q AND f(v) == p)
                            self._add_forbid_pair_clause(cnf, u, p, v, q)
                            self._add_forbid_pair_clause(cnf, u, q, v, p)

        # -------------------------------------------------------------
        # 4. Symmetry Breaking Constraints (Order Encoding):
        # f(pivot) <= ceil(n / 2)
        # In order encoding, this is simply: y_{pivot, ceil(n / 2)} is TRUE!
        # This adds a single unit clause!
        # -------------------------------------------------------------
        if self.break_symmetry and n >= 2:
            half = (n + 1) // 2
            if half <= n - 1:
                cnf.append([self.var(self.pivot_vertex, half)])

        return cnf

    def _add_forbid_pair_clause(self, cnf: CNF, u: int, p: int, v: int, q: int) -> None:
        """Helper: forbid f(u) == p AND f(v) == q in order encoding."""
        n = self.n
        # f(u) == p is:
        # if p == 1: y_{u, 1}
        # if p == n: NOT y_{u, n-1}
        # else: y_{u, p} AND NOT y_{u, p-1}
        lits = []
        if p == 1:
            lits.append(-self.var(u, 1))
        elif p == n:
            lits.append(self.var(u, n - 1))
        else:
            lits.append(-self.var(u, p))
            lits.append(self.var(u, p - 1))

        if q == 1:
            lits.append(-self.var(v, 1))
        elif q == n:
            lits.append(self.var(v, n - 1))
        else:
            lits.append(-self.var(v, q))
            lits.append(self.var(v, q - 1))

        cnf.append(lits)

    def decode_model(self, model: List[int]) -> Dict[int, int]:
        """Decode an order-encoding satisfying assignment into {vertex: position}.

        For each vertex v, f(v) is the smallest position p in {1, ..., n-1}
        such that y_{v, p} is True. If none is True, f(v) = n.
        """
        n = self.n
        model_set = set(model)
        labeling = {}

        for v in range(n):
            assigned_pos = n  # Default if all order vars are False (meaning > n-1)
            for p in range(1, n):
                var_id = self.var(v, p)
                if var_id in model_set:
                    assigned_pos = p
                    break
            labeling[v] = assigned_pos

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
                num_vars = self.n * (self.n - 1)
                f.write(f"p cnf {num_vars} {len(cnf.clauses)}\n")
                for c in cnf.clauses:
                    f.write(" ".join(map(str, c)) + " 0\n")
