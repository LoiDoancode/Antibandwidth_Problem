"""Solver for Antibandwidth Problem using SAT and Binary Search.

Orchestrates the SAT encoding and binary search to find the optimal
Antibandwidth B*(G) = max_f min_{(u, v) in E} |f(u) - f(v)|.
"""

import time
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

from .sat_encoder import AntibandwidthSATEncoder

# Try importing PySAT solvers
try:
    from pysat.solvers import Solver as PySATSolver
    HAS_PYSAT = True
except ImportError:
    HAS_PYSAT = False


class AntibandwidthSolver:
    """Solves the Antibandwidth Problem (ABP) using SAT-based Binary Search."""

    def __init__(
        self,
        graph: nx.Graph,
        solver_name: str = "glucose4",
        break_symmetry: bool = True,
        verbose: bool = True,
    ):
        """
        Args:
            graph: Undirected graph with vertices 0..n-1.
            solver_name: Name of PySAT solver (e.g., 'glucose4', 'cadical153', 'minisat22').
            break_symmetry: Enable symmetry breaking.
            verbose: Print step-by-step solver progress.
        """
        self.graph = graph
        self.n = graph.number_of_nodes()
        self.solver_name = solver_name
        self.break_symmetry = break_symmetry
        self.verbose = verbose
        self.encoder = AntibandwidthSATEncoder(graph, break_symmetry=break_symmetry)

    def check_sat(self, k: int) -> Tuple[bool, Optional[Dict[int, int]], float, int]:
        """Check if there exists a valid labeling with antibandwidth >= k.

        Returns:
            (is_sat, labeling_dict, solve_time_seconds, num_clauses)
        """
        if not HAS_PYSAT:
            raise RuntimeError(
                "python-sat (pysat) is not installed. Please run: pip install python-sat"
            )

        start_time = time.perf_counter()
        cnf = self.encoder.encode(k)
        num_clauses = len(cnf.clauses)

        is_sat = False
        labeling = None

        with PySATSolver(name=self.solver_name, bootstrap_with=cnf.clauses) as s:
            if s.solve():
                is_sat = True
                model = s.get_model()
                labeling = self.encoder.decode_model(model)

        elapsed = time.perf_counter() - start_time
        return is_sat, labeling, elapsed, num_clauses

    def verify_solution(self, labeling: Dict[int, int], expected_k: int) -> Tuple[bool, int, Optional[str]]:
        """Verify that a given labeling is valid and achieves minimum distance >= expected_k.

        Returns:
            (is_valid, actual_min_dist, error_message)
        """
        n = self.n
        # 1. Check permutation validity
        positions = list(labeling.values())
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False, 0, f"Labeling is not a valid permutation of 1..{n}"

        # 2. Check edge distance
        min_dist = n
        for u, v in self.graph.edges():
            dist = abs(labeling[u] - labeling[v])
            if dist < min_dist:
                min_dist = dist
            if dist < expected_k:
                return False, dist, f"Edge ({u}, {v}) violated constraint: |{labeling[u]} - {labeling[v]}| = {dist} < {expected_k}"

        return True, min_dist, None

    def solve(self, method: str = "binary_search") -> Dict[str, Any]:
        """Find the optimal Antibandwidth B*(G).

        Args:
            method: 'binary_search' or 'linear_search'.

        Returns:
            Dictionary containing:
            - optimal_k: Optimal antibandwidth value
            - labeling: Best vertex-to-position mapping
            - total_time: Total elapsed seconds
            - iterations: List of per-k search history
            - verified: Boolean verification result
        """
        n = self.n
        m = self.graph.number_of_edges()

        # Handle trivial corner cases
        if n <= 1:
            return {
                "optimal_k": 0,
                "labeling": {0: 1} if n == 1 else {},
                "total_time": 0.0,
                "iterations": [],
                "verified": True,
            }

        if m == 0:
            # Empty graph: any permutation yields maximum possible difference n - 1
            labeling = {i: i + 1 for i in range(n)}
            return {
                "optimal_k": n - 1,
                "labeling": labeling,
                "total_time": 0.0,
                "iterations": [],
                "verified": True,
            }

        # Safe bounds:
        # Lower bound: 1 (any graph with edges has at least distance 1)
        # Upper bound: n - 1
        low = 1
        high = n - 1

        best_k = 1
        best_labeling = None
        iterations = []
        total_start = time.perf_counter()

        if self.verbose:
            print(f"\n[ABP Solver] Nodes: {n}, Edges: {m}")
            print(f"[ABP Solver] Search space: k in [{low}, {high}] using {method.upper()} with {self.solver_name}")
            print("-" * 65)
            print(f"{'Target k':>10} | {'Status':>8} | {'Clauses':>10} | {'Time (s)':>10}")
            print("-" * 65)

        if method == "binary_search":
            while low <= high:
                mid = (low + high) // 2
                is_sat, labeling, solve_time, num_clauses = self.check_sat(mid)

                status_str = "SAT" if is_sat else "UNSAT"
                iterations.append({
                    "k": mid,
                    "sat": is_sat,
                    "time": solve_time,
                    "clauses": num_clauses,
                })

                if self.verbose:
                    print(f"{mid:>10} | {status_str:>8} | {num_clauses:>10} | {solve_time:>10.4f}")

                if is_sat:
                    best_k = mid
                    best_labeling = labeling
                    low = mid + 1  # Try searching for larger antibandwidth
                else:
                    high = mid - 1  # Target is too large, reduce high bound

        elif method == "linear_search":
            # Search from high bound down to low bound
            for k in range(high, low - 1, -1):
                is_sat, labeling, solve_time, num_clauses = self.check_sat(k)
                status_str = "SAT" if is_sat else "UNSAT"
                iterations.append({
                    "k": k,
                    "sat": is_sat,
                    "time": solve_time,
                    "clauses": num_clauses,
                })

                if self.verbose:
                    print(f"{k:>10} | {status_str:>8} | {num_clauses:>10} | {solve_time:>10.4f}")

                if is_sat:
                    best_k = k
                    best_labeling = labeling
                    break

        total_time = time.perf_counter() - total_start

        # Verification step
        is_valid, actual_min, err = (True, best_k, None)
        if best_labeling:
            is_valid, actual_min, err = self.verify_solution(best_labeling, best_k)

        if self.verbose:
            print("-" * 65)
            print(f"[ABP Solver] Optimal Antibandwidth B*(G) = {best_k}")
            print(f"[ABP Solver] Total time: {total_time:.4f}s (Verified: {'PASSED' if is_valid else f'FAILED: {err}'})\n")

        return {
            "optimal_k": best_k,
            "labeling": best_labeling,
            "total_time": total_time,
            "iterations": iterations,
            "verified": is_valid,
            "actual_min_dist": actual_min,
            "error": err,
        }
