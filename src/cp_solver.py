"""Constraint Programming (CP) Solver for Antibandwidth Problem using Google OR-Tools CP-SAT.

Implements the exact constraint programming formulation:
- Integer variables pos[v] in {1, ..., n} representing the position of each vertex v in V.
- Global AllDifferent constraint: AddAllDifferent([pos[v] for v in V]).
- Absolute distance constraints for all edges (u, v) in E: |pos[u] - pos[v]| >= k.
- Symmetry breaking constraint: pos[v0] <= ceil(n / 2) for pivot vertex v0 = argmax deg(v).
- Dual modes:
  1. Decision solving: check_sat(k) to determine if ABP(G, k) is feasible.
  2. Direct optimization: solve() to maximize k = min_{(u, v) in E} |pos[u] - pos[v]|.
"""

import math
import time
from typing import Dict, List, Optional, Tuple, Any
import networkx as nx

try:
    from ortools.sat.python import cp_model
    HAS_ORTOOLS = True
except ImportError:
    HAS_ORTOOLS = False


class AntibandwidthCPSolver:
    """Solves the Antibandwidth Problem (ABP) using Google OR-Tools CP-SAT."""

    def __init__(
        self,
        graph: nx.Graph,
        break_symmetry: bool = True,
        time_limit_seconds: Optional[float] = None,
        num_workers: int = 4,
        verbose: bool = False,
    ):
        """
        Args:
            graph: Undirected NetworkX graph with vertices 0..n-1.
            break_symmetry: If True, restricts highest-degree vertex to pos <= ceil(n / 2).
            time_limit_seconds: Maximum solving time per invocation.
            num_workers: Number of parallel search workers for CP-SAT solver.
            verbose: Enable verbose solver search logging.
        """
        if not HAS_ORTOOLS:
            raise ImportError(
                "Google OR-Tools is required for AntibandwidthCPSolver. Run: pip install ortools"
            )

        self.graph = graph
        self.n = graph.number_of_nodes()
        self.m = graph.number_of_edges()
        self.break_symmetry = break_symmetry
        self.time_limit_seconds = time_limit_seconds
        self.num_workers = num_workers
        self.verbose = verbose

        # Determine pivot vertex for symmetry breaking: argmax deg(v)
        if self.n > 0:
            degrees = dict(self.graph.degree())
            self.pivot_vertex = max(degrees.keys(), key=lambda v: degrees[v])
        else:
            self.pivot_vertex = None

    def check_sat(self, target_k: int) -> Tuple[bool, Optional[Dict[int, int]], float, int]:
        """Solve the decision problem ABP(G, target_k) using CP-SAT.

        Returns:
            (is_feasible, labeling, elapsed_seconds, num_constraints)
        """
        n = self.n
        if n <= 1:
            return True, {0: 1} if n == 1 else {}, 0.0, 0

        model = cp_model.CpModel()
        pos_vars = {v: model.NewIntVar(1, n, f"pos_{v}") for v in self.graph.nodes()}

        # 1. Bijectivity: All positions must be distinct
        model.AddAllDifferent(list(pos_vars.values()))
        num_constraints = 1

        # 2. Distance constraints: |pos[u] - pos[v]| >= target_k for all (u, v) in E
        for u, v in self.graph.edges():
            diff = model.NewIntVar(-(n - 1), n - 1, f"diff_{u}_{v}")
            model.Add(diff == pos_vars[u] - pos_vars[v])
            abs_diff = model.NewIntVar(0, n - 1, f"abs_diff_{u}_{v}")
            model.AddAbsEquality(abs_diff, diff)
            model.Add(abs_diff >= target_k)
            num_constraints += 3

        # 3. Symmetry breaking: pos[v0] <= ceil(n / 2)
        if self.break_symmetry and self.pivot_vertex is not None:
            half = (n + 1) // 2
            model.Add(pos_vars[self.pivot_vertex] <= half)
            num_constraints += 1

        solver = cp_model.CpSolver()
        if self.num_workers > 1:
            solver.parameters.num_workers = self.num_workers
        if self.time_limit_seconds:
            solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.log_search_progress = self.verbose

        t0 = time.perf_counter()
        status = solver.Solve(model)
        elapsed = time.perf_counter() - t0

        is_sat = status in (cp_model.OPTIMAL, cp_model.FEASIBLE)
        labeling = None
        if is_sat:
            labeling = {v: int(solver.Value(pos_vars[v])) for v in self.graph.nodes()}

        return is_sat, labeling, elapsed, num_constraints

    def verify_solution(
        self, labeling: Optional[Dict[int, int]], expected_k: int
    ) -> Tuple[bool, int, Optional[str]]:
        """Verify that a given labeling is a valid permutation and achieves min span >= expected_k.

        Returns:
            (is_valid, actual_min_dist, error_message)
        """
        n = self.n
        if labeling is None:
            return False, 0, "No labeling provided (None)"

        positions = list(labeling.values())
        if len(positions) != n or sorted(positions) != list(range(1, n + 1)):
            return False, 0, f"Labeling is not a valid permutation of 1..{n}"

        min_dist = n
        for u, v in self.graph.edges():
            dist = abs(labeling[u] - labeling[v])
            if dist < min_dist:
                min_dist = dist
            if dist < expected_k:
                return (
                    False,
                    dist,
                    f"Edge ({u}, {v}) violated distance: |{labeling[u]} - {labeling[v]}| = {dist} < {expected_k}",
                )

        return True, min_dist, None

    def solve(self, method: str = "direct_optimize") -> Dict[str, Any]:
        """Find the optimal Antibandwidth B*(G).

        Args:
            method: 'direct_optimize' (CP-SAT objective maximization) or 'binary_search'.

        Returns:
            Dictionary containing:
            - optimal_k: Optimal antibandwidth value
            - labeling: Best vertex-to-position mapping
            - total_time: Total elapsed seconds
            - iterations: Search history
            - verified: Verification boolean
        """
        n = self.n
        m = self.m

        if n <= 1:
            return {
                "optimal_k": 0,
                "labeling": {0: 1} if n == 1 else {},
                "total_time": 0.0,
                "iterations": [],
                "verified": True,
            }

        if m == 0:
            labeling = {i: i + 1 for i in range(n)}
            return {
                "optimal_k": n - 1,
                "labeling": labeling,
                "total_time": 0.0,
                "iterations": [],
                "verified": True,
            }

        if method == "binary_search":
            return self._solve_binary_search()
        else:
            return self._solve_direct_optimize()

    def _solve_direct_optimize(self) -> Dict[str, Any]:
        """Solve ABP via direct objective maximization in CP-SAT."""
        n = self.n
        model = cp_model.CpModel()
        pos_vars = {v: model.NewIntVar(1, n, f"pos_{v}") for v in self.graph.nodes()}
        model.AddAllDifferent(list(pos_vars.values()))

        # Antibandwidth objective variable k in [1, floor(n / 2)]
        k_upper = n // 2 if n >= 2 else 1
        k_var = model.NewIntVar(1, k_upper, "k_antibandwidth")

        total_constraints = 1
        for u, v in self.graph.edges():
            diff = model.NewIntVar(-(n - 1), n - 1, f"diff_{u}_{v}")
            model.Add(diff == pos_vars[u] - pos_vars[v])
            abs_diff = model.NewIntVar(0, n - 1, f"abs_diff_{u}_{v}")
            model.AddAbsEquality(abs_diff, diff)
            model.Add(abs_diff >= k_var)
            total_constraints += 3

        if self.break_symmetry and self.pivot_vertex is not None:
            half = (n + 1) // 2
            model.Add(pos_vars[self.pivot_vertex] <= half)
            total_constraints += 1

        model.Maximize(k_var)

        solver = cp_model.CpSolver()
        if self.num_workers > 1:
            solver.parameters.num_workers = self.num_workers
        if self.time_limit_seconds:
            solver.parameters.max_time_in_seconds = self.time_limit_seconds
        solver.parameters.log_search_progress = self.verbose

        t0 = time.perf_counter()
        status = solver.Solve(model)
        elapsed = time.perf_counter() - t0

        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            best_k = int(solver.Value(k_var))
            labeling = {v: int(solver.Value(pos_vars[v])) for v in self.graph.nodes()}
            verified, min_dist, _ = self.verify_solution(labeling, best_k)
        else:
            best_k = 1
            labeling = {v: i + 1 for i, v in enumerate(self.graph.nodes())}
            verified, _, _ = self.verify_solution(labeling, 1)

        iterations = [{
            "k": best_k,
            "sat": status in (cp_model.OPTIMAL, cp_model.FEASIBLE),
            "time": elapsed,
            "clauses": total_constraints,
        }]

        return {
            "optimal_k": best_k,
            "labeling": labeling,
            "total_time": elapsed,
            "iterations": iterations,
            "verified": verified,
        }

    def _solve_binary_search(self) -> Dict[str, Any]:
        """Solve ABP via binary search over target k values."""
        n = self.n
        low = 1
        high = n // 2 if n >= 2 else 1
        best_k = 1
        best_labeling = None
        iterations = []
        total_start = time.perf_counter()

        while low <= high:
            mid = (low + high) // 2
            is_sat, labeling, solve_time, n_constraints = self.check_sat(mid)
            iterations.append({
                "k": mid,
                "sat": is_sat,
                "time": solve_time,
                "clauses": n_constraints,
            })
            if is_sat:
                best_k = mid
                best_labeling = labeling
                low = mid + 1
            else:
                high = mid - 1

        total_elapsed = time.perf_counter() - total_start
        if best_labeling is None:
            best_labeling = {v: i + 1 for i, v in enumerate(self.graph.nodes())}
            best_k = 1

        verified, _, _ = self.verify_solution(best_labeling, best_k)

        return {
            "optimal_k": best_k,
            "labeling": best_labeling,
            "total_time": total_elapsed,
            "iterations": iterations,
            "verified": verified,
        }

