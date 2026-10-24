"""Solver for Antibandwidth Problem using SAT and Binary Search.

Orchestrates the SAT encoding (Direct Encoding / Order Encoding) and binary search
to find the optimal Antibandwidth B*(G) = max_f min_{(u, v) in E} |f(u) - f(v)|.
Supports internal PySAT engines (Glucose, CaDiCaL, Minisat) and external solvers (Kissat).
"""

import os
import subprocess
import tempfile
import time
from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import networkx as nx

from .sat_encoder import AntibandwidthSATEncoder
from .order_encoder import AntibandwidthOrderEncoder

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
        encoding: str = "direct",
        break_symmetry: bool = True,
        external_solver: Optional[str] = None,
        verbose: bool = True,
    ):
        """
        Args:
            graph: Undirected graph with vertices 0..n-1.
            solver_name: Name of PySAT solver (e.g., 'glucose4', 'cadical153', 'minisat22').
            encoding: 'direct' (Direct Encoding) or 'order' (Order Encoding).
            break_symmetry: Enable symmetry breaking constraints.
            external_solver: Path / command of external SAT solver binary (e.g. 'kissat').
            verbose: Print step-by-step solver progress.
        """
        self.graph = graph
        self.n = graph.number_of_nodes()
        self.solver_name = solver_name
        self.encoding = encoding.lower()
        self.break_symmetry = break_symmetry
        self.external_solver = external_solver
        self.verbose = verbose

        # Choose encoder based on configuration
        if self.encoding == "order":
            self.encoder = AntibandwidthOrderEncoder(graph, break_symmetry=break_symmetry)
        else:
            self.encoder = AntibandwidthSATEncoder(graph, break_symmetry=break_symmetry)

    def check_sat_pysat(self, cnf) -> Tuple[bool, Optional[List[int]], float]:
        """Solve CNF using PySAT backend."""
        if not HAS_PYSAT:
            raise RuntimeError(
                "python-sat (pysat) is not installed. Please run: pip install python-sat"
            )
        start_time = time.perf_counter()
        is_sat = False
        model = None

        with PySATSolver(name=self.solver_name, bootstrap_with=cnf.clauses) as s:
            if s.solve():
                is_sat = True
                model = s.get_model()

        elapsed = time.perf_counter() - start_time
        return is_sat, model, elapsed

    def check_sat_external(self, cnf, solver_cmd: str) -> Tuple[bool, Optional[List[int]], float]:
        """Solve CNF using an external SAT solver executable (e.g. Kissat, CaDiCaL CLI).

        Exports CNF to temporary DIMACS file, calls the binary, parses DIMACS output.
        """
        start_time = time.perf_counter()

        with tempfile.NamedTemporaryFile(suffix=".cnf", delete=False, mode="w", encoding="utf-8") as tmp:
            tmp_path = tmp.name
            if hasattr(cnf, "to_dimacs"):
                tmp.write(cnf.to_dimacs())
            else:
                num_vars = getattr(cnf, "nv", self.n * self.n)
                tmp.write(f"p cnf {num_vars} {len(cnf.clauses)}\n")
                for c in cnf.clauses:
                    tmp.write(" ".join(map(str, c)) + " 0\n")

        is_sat = False
        model = []

        try:
            # Run external solver process
            proc = subprocess.run(
                [solver_cmd, tmp_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            output = proc.stdout

            for line in output.splitlines():
                line = line.strip()
                if line.startswith("s SATISFIABLE") or line == "SATISFIABLE":
                    is_sat = True
                elif line.startswith("s UNSATISFIABLE") or line == "UNSATISFIABLE":
                    is_sat = False
                elif line.startswith("v "):
                    # Extract literal values from DIMACS output
                    lits = [int(tok) for tok in line[2:].split() if tok != "0"]
                    model.extend(lits)

        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        elapsed = time.perf_counter() - start_time
        return is_sat, (model if is_sat else None), elapsed

    def check_sat(self, k: int) -> Tuple[bool, Optional[Dict[int, int]], float, int]:
        """Check if there exists a valid labeling with antibandwidth >= k.

        Returns:
            (is_sat, labeling_dict, solve_time_seconds, num_clauses)
        """
        cnf = self.encoder.encode(k)
        num_clauses = len(cnf.clauses)

        if self.external_solver:
            is_sat, model, elapsed = self.check_sat_external(cnf, self.external_solver)
        else:
            is_sat, model, elapsed = self.check_sat_pysat(cnf)

        labeling = None
        if is_sat and model:
            labeling = self.encoder.decode_model(model)

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
            labeling = {i: i + 1 for i in range(n)}
            return {
                "optimal_k": n - 1,
                "labeling": labeling,
                "total_time": 0.0,
                "iterations": [],
                "verified": True,
            }

        # Safe bounds:
        # Lower bound: 1 (any connected graph with >= 1 edge has min distance >= 1)
        # Upper bound: n - 1
        low = 1
        high = n - 1

        best_k = 1
        best_labeling = None
        iterations = []
        total_start = time.perf_counter()

        solver_display = self.external_solver or self.solver_name
        if self.verbose:
            print(f"\n[ABP Solver] Nodes: {n}, Edges: {m}")
            print(f"[ABP Solver] Encoding: {self.encoding.upper()}, Symmetry Breaking: {self.break_symmetry}")
            print(f"[ABP Solver] Search space: k in [{low}, {high}] using {method.upper()} with {solver_display}")
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
                    low = mid + 1  # Search for larger antibandwidth
                else:
                    high = mid - 1  # Target is too large, reduce upper bound

        elif method == "linear_search":
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
