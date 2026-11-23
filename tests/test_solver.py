"""Unit and integration tests for AntibandwidthSolver."""

from pathlib import Path
import subprocess

import pytest
import networkx as nx
from src.solver import AntibandwidthSolver, HAS_PYSAT


@pytest.fixture
def external_process(monkeypatch):
    def configure(returncode=0, stdout="", stderr="", error=None):
        temp_paths = []

        def run(command, **kwargs):
            temp_paths.append(Path(command[1]))
            if error is not None:
                raise error
            return subprocess.CompletedProcess(command, returncode, stdout, stderr)

        monkeypatch.setattr("src.solver.subprocess.run", run)
        return temp_paths

    return configure


@pytest.mark.skipif(not HAS_PYSAT, reason="python-sat is required for solver tests")
class TestAntibandwidthSolver:
    """Tests for Antibandwidth SAT Solver."""

    @pytest.mark.parametrize("encoding", ["direct", "scl"])
    @pytest.mark.parametrize("method", ["direct_optimize", "unknown_method"])
    @pytest.mark.parametrize(
        "graph",
        [nx.path_graph(6), nx.empty_graph(0), nx.empty_graph(1), nx.empty_graph(4)],
        ids=["p6", "empty", "singleton", "edgeless"],
    )
    def test_unsupported_search_method_raises(self, encoding, method, graph):
        solver = AntibandwidthSolver(graph, encoding=encoding, verbose=False)

        with pytest.raises(ValueError, match="Unsupported search method"):
            solver.solve(method=method)

    def test_trivial_graphs(self):
        # Empty graph n=1
        G1 = nx.Graph()
        G1.add_node(0)
        s1 = AntibandwidthSolver(G1, verbose=False)
        res1 = s1.solve()
        assert res1["optimal_k"] == 0

        # Disconnected / no edges graph n=4
        G_no_edges = nx.empty_graph(4)
        s_no_edges = AntibandwidthSolver(G_no_edges, verbose=False)
        res_no_edges = s_no_edges.solve()
        assert res_no_edges["optimal_k"] == 3  # n - 1

    def test_complete_graph_kn(self):
        # For complete graph K_n (n >= 2), every pair is connected.
        # Any permutation will have two vertices at adjacent positions |f(u) - f(v)| = 1.
        # Therefore, B*(K_n) = 1 for all n >= 2.
        for n in [3, 4]:
            G = nx.complete_graph(n)
            solver = AntibandwidthSolver(G, encoding="direct", verbose=False)
            result = solver.solve()
            assert result["optimal_k"] == 1
            assert result["verified"] is True

    def test_path_graph_p4(self):
        # For path P_4: 0-1-2-3, optimal antibandwidth is 2.
        G = nx.path_graph(4)
        solver = AntibandwidthSolver(G, encoding="direct", verbose=False)
        result = solver.solve()
        assert result["optimal_k"] == 2
        assert result["verified"] is True

    def test_direct_vs_scl_encoding_consistency(self):
        # Both encodings must yield the exact same optimal k for P_5
        G = nx.path_graph(5)

        s_direct = AntibandwidthSolver(G, encoding="direct", break_symmetry=True, verbose=False)
        res_direct = s_direct.solve()

        s_scl = AntibandwidthSolver(G, encoding="scl", break_symmetry=True, verbose=False)
        res_scl = s_scl.solve(method="incremental")

        assert res_direct["optimal_k"] == res_scl["optimal_k"]
        assert res_direct["verified"] is True
        assert res_scl["verified"] is True

    def test_symmetry_breaking_consistency(self):
        # Symmetry breaking should prune search space without changing optimal k
        G = nx.cycle_graph(5)

        s_sym = AntibandwidthSolver(G, encoding="direct", break_symmetry=True, verbose=False)
        res_sym = s_sym.solve()

        s_no_sym = AntibandwidthSolver(G, encoding="direct", break_symmetry=False, verbose=False)
        res_no_sym = s_no_sym.solve()

        assert res_sym["optimal_k"] == res_no_sym["optimal_k"]

    def test_verify_solution_method(self):
        G = nx.path_graph(4)
        solver = AntibandwidthSolver(G, verbose=False)

        # Valid labeling for P_4 achieving k=2:
        # 0 -> 3, 1 -> 1, 2 -> 4, 3 -> 2
        # Edges: (0,1): |3-1|=2, (1,2): |1-4|=3, (2,3): |4-2|=2. All >= 2.
        valid_labeling = {0: 3, 1: 1, 2: 4, 3: 2}
        is_valid, min_dist, err = solver.verify_solution(valid_labeling, expected_k=2)
        assert is_valid is True
        assert min_dist == 2
        assert err is None

        # Invalid labeling: not a permutation (duplicate values)
        invalid_perm = {0: 1, 1: 1, 2: 4, 3: 2}
        is_valid, _, err = solver.verify_solution(invalid_perm, expected_k=2)
        assert is_valid is False
        assert "permutation" in err.lower()

        # Invalid labeling: violates target k=2
        # 0 -> 1, 1 -> 2, 2 -> 3, 3 -> 4 gives min_dist = 1
        violating_labeling = {0: 1, 1: 2, 2: 3, 3: 4}
        is_valid, min_dist, err = solver.verify_solution(violating_labeling, expected_k=2)
        assert is_valid is False
        assert min_dist == 1

    @pytest.mark.parametrize("amo_encoding", ["seqcounter", "commander", "totalizer", "ladder", "bitwise"])
    def test_advanced_amo_encodings_solve_equivalently(self, amo_encoding):
        # Path P_6 has optimal B*(P_6) = 3; Cycle C_5 has optimal B*(C_5) = 2
        for graph, expected_k in [(nx.path_graph(6), 3), (nx.cycle_graph(5), 2)]:
            solver = AntibandwidthSolver(
                graph,
                solver_name="cadical153",
                encoding="direct",
                amo_encoding=amo_encoding,
                break_symmetry=True,
                verbose=False,
            )
            res = solver.solve()
            assert res["optimal_k"] == expected_k
            assert res["verified"] is True


class TestExternalSolverResults:
    @pytest.mark.parametrize(
        "returncode,output,expected_sat",
        [
            (10, "s SATISFIABLE\nv 1 -2 -3\nv -4 5 -6 0\nv -7 -8 9 0\n", True),
            (0, "SATISFIABLE\nv 1 -2 -3 -4 5 -6 -7 -8 9 0\n", True),
            (20, "s UNSATISFIABLE\n", False),
            (0, "UNSATISFIABLE\n", False),
        ],
    )
    def test_conclusive_results_preserve_status_and_model(self, external_process, returncode, output, expected_sat):
        temp_paths = external_process(returncode, output)
        solver = AntibandwidthSolver(nx.path_graph(3), verbose=False)
        cnf = solver.encoder.encode(1 if expected_sat else 4)

        is_sat, model, elapsed = solver.check_sat_external(cnf, "external-solver")

        assert is_sat is expected_sat
        assert model == ([1, -2, -3, -4, 5, -6, -7, -8, 9] if expected_sat else None)
        assert elapsed >= 0
        assert temp_paths and all(not path.exists() for path in temp_paths)

    @pytest.mark.parametrize(
        "returncode,output,stderr,error_message",
        [
            (1, "", "invalid option", "exit code 1.*invalid option"),
            (1, "s UNSATISFIABLE\n", "solver crashed", "exit code 1.*solver crashed"),
            (-9, "", "", "exit code -9"),
            (0, "s UNKNOWN\n", "", "UNKNOWN"),
            (0, "UNKNOWN\n", "", "UNKNOWN"),
            (0, "c s UNSATISFIABLE\n", "", "status"),
            (20, "", "", "status"),
            (10, "s UNSATISFIABLE\n", "", "exit code"),
            (20, "s SATISFIABLE\nv 1 5 9 0\n", "", "exit code"),
            (0, "s SATISFIABLE\ns UNSATISFIABLE\n", "", "conflicting"),
            (0, "s UNSATISFIABLE\ns SATISFIABLE\n", "", "conflicting"),
            (10, "s SATISFIABLE\nv not-a-literal 0\n", "", "model"),
            (10, "s SATISFIABLE\n", "", "model"),
            (0, "s SATISFIABLEsuffix\nv 1 5 9 0\n", "", "status"),
        ],
    )
    def test_failed_or_inconclusive_results_raise(self, external_process, returncode, output, stderr, error_message):
        temp_paths = external_process(returncode, output, stderr)
        solver = AntibandwidthSolver(nx.path_graph(3), verbose=False)

        with pytest.raises(RuntimeError, match=error_message):
            solver.check_sat_external(solver.encoder.encode(1), "external-solver")

        assert temp_paths and all(not path.exists() for path in temp_paths)

    @pytest.mark.parametrize("error", [FileNotFoundError("binary missing"), PermissionError("access denied")])
    def test_launch_errors_raise_solver_error(self, external_process, error):
        temp_paths = external_process(error=error)
        solver = AntibandwidthSolver(nx.path_graph(3), verbose=False)

        with pytest.raises(RuntimeError, match="start"):
            solver.check_sat_external(solver.encoder.encode(1), "external-solver")

        assert temp_paths and all(not path.exists() for path in temp_paths)

    def test_timeout_preserves_exception_and_cleans_cnf(self, external_process):
        temp_paths = external_process(error=subprocess.TimeoutExpired("external-solver", 0.1))
        solver = AntibandwidthSolver(nx.path_graph(3), verbose=False)

        with pytest.raises(TimeoutError, match="time limit"):
            solver.check_sat_external(solver.encoder.encode(1), "external-solver", time_limit=0.1)

        assert temp_paths and all(not path.exists() for path in temp_paths)

    @pytest.mark.parametrize("method", ["binary_search", "linear_search", "incremental"])
    def test_search_does_not_treat_external_failure_as_unsat(self, external_process, method):
        external_process(1, stderr="solver failed")
        solver = AntibandwidthSolver(nx.path_graph(6), external_solver="external-solver", verbose=False)

        with pytest.raises(RuntimeError, match="solver failed"):
            solver.solve(method=method)

