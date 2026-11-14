"""Solver for Antibandwidth Problem using SAT and Binary / Incremental Search.

Orchestrates the SAT encoding (Direct Encoding / Staircase SCL Encoding) and search
to find the optimal Antibandwidth B*(G) = max_f min_{(u, v) in E} |f(u) - f(v)|.
Supports internal PySAT engine (CaDiCaL 1.5.3) and external solvers (Kissat).
"""

import os
import subprocess
import tempfile
import threading
import time
from typing import Callable, Dict, List, Optional, Tuple, Any
from pathlib import Path
import networkx as nx

from .sat_encoder import AntibandwidthSATEncoder
from .scl_encoder import AntibandwidthSCLEncoder

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
        solver_name: str = "cadical153",
        encoding: str = "direct",
        amo_encoding: str = "pairwise",
        break_symmetry: bool = True,
        external_solver: Optional[str] = None,
        verbose: bool = True,
        time_limit_seconds: Optional[float] = None,
        on_clauses_generated: Optional[Callable[[int], None]] = None,
        on_best_found: Optional[Callable[[int, Dict[int, int], int], None]] = None,
    ):
        """
        Args:
            graph: Undirected graph with vertices 0..n-1.
            solver_name: Name of PySAT solver (default: 'cadical153').
            encoding: 'direct' (Direct Encoding) or 'scl' (Staircase SCL Encoding).
            amo_encoding: AMO encoding for Direct Encoding ('pairwise', 'seqcounter',
                          'commander', 'totalizer', 'ladder', 'bitwise').
            break_symmetry: Enable symmetry breaking constraints.
            external_solver: Path / command of external SAT solver binary (e.g. 'kissat').
            verbose: Print step-by-step solver progress.
            time_limit_seconds: Maximum total execution time in seconds.
        """
        self.graph = graph
        self.n = graph.number_of_nodes()
        self.solver_name = solver_name
        self.encoding = encoding.lower()
        self.amo_encoding = amo_encoding.lower()
        self.break_symmetry = break_symmetry
        self.external_solver = external_solver
        self.verbose = verbose
        self.time_limit_seconds = time_limit_seconds
        self.on_clauses_generated = on_clauses_generated
        self.on_best_found = on_best_found

        # Choose encoder based on configuration
        if self.encoding in ("scl", "staircase"):
            self.encoder = AntibandwidthSCLEncoder(graph, break_symmetry=break_symmetry)
        else:
            self.encoder = AntibandwidthSATEncoder(
                graph,
                break_symmetry=break_symmetry,
                amo_encoding=self.amo_encoding,
            )

    def check_sat_pysat(self, cnf, time_limit: Optional[float] = None) -> Tuple[bool, Optional[List[int]], float]:
        """Solve CNF using PySAT backend with optional timeout support."""
        if not HAS_PYSAT:
            raise RuntimeError(
                "python-sat (pysat) is not installed. Please run: pip install python-sat"
            )
        start_time = time.perf_counter()
        is_sat = False
        model = None

        with PySATSolver(name=self.solver_name, bootstrap_with=cnf.clauses) as s:
            if time_limit is not None and time_limit > 0:
                timer = threading.Timer(time_limit, s.interrupt)
                timer.start()
                try:
                    res = s.solve_limited(expect_interrupt=True)
                except NotImplementedError:
                    timer.cancel()
                    res = s.solve()
                finally:
                    timer.cancel()
                    try:
                        s.clear_interrupt()
                    except NotImplementedError:
                        pass

                if res is None:
                    raise TimeoutError(
                        f"PySAT solver '{self.solver_name}' exceeded time limit ({time_limit:.2f}s)"
                    )
                if res:
                    is_sat = True
                    model = s.get_model()
            else:
                if s.solve():
                    is_sat = True
                    model = s.get_model()

        elapsed = time.perf_counter() - start_time
        return is_sat, model, elapsed

    def check_sat_external(self, cnf, solver_cmd: str, time_limit: Optional[float] = None) -> Tuple[bool, Optional[List[int]], float]:
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
                timeout=time_limit,
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

        except subprocess.TimeoutExpired:
            raise TimeoutError(f"External solver '{solver_cmd}' exceeded time limit ({time_limit:.2f}s)")
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

        elapsed = time.perf_counter() - start_time
        return is_sat, (model if is_sat else None), elapsed

    def check_sat(self, k: int, time_limit: Optional[float] = None) -> Tuple[bool, Optional[Dict[int, int]], float, int]:
        """Check if there exists a valid labeling with antibandwidth >= k.

        Returns:
            (is_sat, labeling_dict, solve_time_seconds, num_clauses)
        """
        cnf = self.encoder.encode(k)
        num_clauses = len(cnf.clauses)
        if self.on_clauses_generated is not None:
            self.on_clauses_generated(num_clauses)

        if self.external_solver:
            is_sat, model, elapsed = self.check_sat_external(cnf, self.external_solver, time_limit=time_limit)
        else:
            is_sat, model, elapsed = self.check_sat_pysat(cnf, time_limit=time_limit)

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
            print(f"\n[ABP Solver] Nodes: {n}, Edges: {m}", flush=True)
            print(f"[ABP Solver] Encoding: {self.encoding.upper()}, Symmetry Breaking: {self.break_symmetry}", flush=True)
            print(f"[ABP Solver] Search space: k in [{low}, {high}] using {method.upper()} with {solver_display}", flush=True)
            print("-" * 65, flush=True)
            print(f"{'Target k':>10} | {'Status':>8} | {'Clauses':>10} | {'Time (s)':>10}", flush=True)
            print("-" * 65, flush=True)

        timed_out = False
        if method == "binary_search":
            while low <= high:
                mid = (low + high) // 2

                remaining_time = None
                if self.time_limit_seconds is not None:
                    elapsed_so_far = time.perf_counter() - total_start
                    remaining_time = self.time_limit_seconds - elapsed_so_far
                    if remaining_time <= 0:
                        timed_out = True
                        if self.verbose:
                            print(f"[ABP Solver] Timeout reached ({self.time_limit_seconds:.1f}s)! Stopping search.", flush=True)
                        break

                try:
                    is_sat, labeling, solve_time, num_clauses = self.check_sat(mid, time_limit=remaining_time)
                except TimeoutError:
                    timed_out = True
                    if self.verbose:
                        print(f"{mid:>10} | {'TIMEOUT':>8} | {'-':>10} | {remaining_time:>10.4f}", flush=True)
                    break

                status_str = "SAT" if is_sat else "UNSAT"
                iterations.append({
                    "k": mid,
                    "sat": is_sat,
                    "time": solve_time,
                    "clauses": num_clauses,
                })

                if self.verbose:
                    print(f"{mid:>10} | {status_str:>8} | {num_clauses:>10} | {solve_time:>10.4f}", flush=True)

                if is_sat:
                    best_k = mid
                    best_labeling = labeling
                    if self.on_best_found and best_labeling is not None:
                        self.on_best_found(best_k, best_labeling, sum(it["clauses"] for it in iterations))
                    low = mid + 1  # Search for larger antibandwidth
                else:
                    high = mid - 1  # Target is too large, reduce upper bound

        elif method == "linear_search":
            for k in range(high, low - 1, -1):
                remaining_time = None
                if self.time_limit_seconds is not None:
                    elapsed_so_far = time.perf_counter() - total_start
                    remaining_time = self.time_limit_seconds - elapsed_so_far
                    if remaining_time <= 0:
                        timed_out = True
                        if self.verbose:
                            print(f"[ABP Solver] Timeout reached ({self.time_limit_seconds:.1f}s)! Stopping search.", flush=True)
                        break

                try:
                    is_sat, labeling, solve_time, num_clauses = self.check_sat(k, time_limit=remaining_time)
                except TimeoutError:
                    timed_out = True
                    if self.verbose:
                        print(f"{k:>10} | {'TIMEOUT':>8} | {'-':>10} | {remaining_time:>10.4f}", flush=True)
                    break

                status_str = "SAT" if is_sat else "UNSAT"
                iterations.append({
                    "k": k,
                    "sat": is_sat,
                    "time": solve_time,
                    "clauses": num_clauses,
                })

                if self.verbose:
                    print(f"{k:>10} | {status_str:>8} | {num_clauses:>10} | {solve_time:>10.4f}", flush=True)

                if is_sat:
                    best_k = k
                    best_labeling = labeling
                    break

        elif method == "incremental":
            for k in range(low, high + 1):
                remaining_time = None
                if self.time_limit_seconds is not None:
                    elapsed_so_far = time.perf_counter() - total_start
                    remaining_time = self.time_limit_seconds - elapsed_so_far
                    if remaining_time <= 0:
                        timed_out = True
                        if self.verbose:
                            print(f"[ABP Solver] Timeout reached ({self.time_limit_seconds:.1f}s)! Stopping search.", flush=True)
                        break

                try:
                    is_sat, labeling, solve_time, num_clauses = self.check_sat(k, time_limit=remaining_time)
                except TimeoutError:
                    timed_out = True
                    if self.verbose:
                        print(f"{k:>10} | {'TIMEOUT':>8} | {'-':>10} | {remaining_time:>10.4f}", flush=True)
                    break

                status_str = "SAT" if is_sat else "UNSAT"
                iterations.append({
                    "k": k,
                    "sat": is_sat,
                    "time": solve_time,
                    "clauses": num_clauses,
                })

                if self.verbose:
                    print(f"{k:>10} | {status_str:>8} | {num_clauses:>10} | {solve_time:>10.4f}", flush=True)

                if is_sat:
                    best_k = k
                    best_labeling = labeling
                    if self.on_best_found and best_labeling is not None:
                        self.on_best_found(best_k, best_labeling, sum(it["clauses"] for it in iterations))
                else:
                    # As soon as k is UNSAT, best_k = k - 1 is guaranteed optimal
                    break

        total_time = time.perf_counter() - total_start

        # Verification step
        is_valid, actual_min, err = (True, best_k, None)
        if best_labeling:
            is_valid, actual_min, err = self.verify_solution(best_labeling, best_k)

        if self.verbose:
            print("-" * 65)
            print(f"[ABP Solver] Optimal Antibandwidth B*(G) = {best_k}{' (TIMED OUT)' if timed_out else ''}")
            print(f"[ABP Solver] Total time: {total_time:.4f}s (Verified: {'PASSED' if is_valid else f'FAILED: {err}'})\n")

        return {
            "optimal_k": best_k,
            "labeling": best_labeling,
            "total_time": total_time,
            "iterations": iterations,
            "verified": is_valid,
            "actual_min_dist": actual_min,
            "error": err,
            "timed_out": timed_out,
        }

    def solve_binary_search(self) -> Tuple[int, Optional[Dict[int, int]], float]:
        """Convenience method: run binary search and return (optimal_k, best_labeling, total_time)."""
        res = self.solve(method="binary_search")
        return res["optimal_k"], res["labeling"], res["total_time"]

    def solve_linear_search(self) -> Tuple[int, Optional[Dict[int, int]], float]:
        """Convenience method: run linear search and return (optimal_k, best_labeling, total_time)."""
        res = self.solve(method="linear_search")
        return res["optimal_k"], res["labeling"], res["total_time"]
