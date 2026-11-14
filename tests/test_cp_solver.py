"""Unit and integration tests for AntibandwidthCPSolver (Google OR-Tools CP-SAT)."""

import pytest
import networkx as nx
from src.cp_solver import AntibandwidthCPSolver, HAS_ORTOOLS
from src.solver import AntibandwidthSolver, HAS_PYSAT


@pytest.mark.skipif(not HAS_ORTOOLS, reason="Google OR-Tools is required for CP-SAT tests")
class TestAntibandwidthCPSolver:
    """Tests for CP-SAT Antibandwidth Solver."""

    def test_trivial_and_empty_graphs(self):
        # Empty graph n=1
        G1 = nx.Graph()
        G1.add_node(0)
        s1 = AntibandwidthCPSolver(G1, verbose=False)
        res1 = s1.solve()
        assert res1["optimal_k"] == 0
        assert res1["verified"] is True

        # Disconnected graph without edges n=4
        G_no_edges = nx.empty_graph(4)
        s_no_edges = AntibandwidthCPSolver(G_no_edges, verbose=False)
        res_no_edges = s_no_edges.solve()
        assert res_no_edges["optimal_k"] == 3
        assert res_no_edges["verified"] is True

    def test_path_graph_p4(self):
        # Path P4: optimal B*(P4) = 2
        G = nx.path_graph(4)
        solver = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)
        res_opt = solver.solve(method="direct_optimize")
        assert res_opt["optimal_k"] == 2
        assert res_opt["verified"] is True

        # Binary search method
        res_bs = solver.solve(method="binary_search")
        assert res_bs["optimal_k"] == 2
        assert res_bs["verified"] is True

    def test_cycle_graph_c5(self):
        # Cycle C5: optimal B*(C5) = 2 (e.g. 0->1, 1->3, 2->5, 3->2, 4->4)
        G = nx.cycle_graph(5)
        solver = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)
        res = solver.solve(method="direct_optimize")
        assert res["optimal_k"] == 2
        assert res["verified"] is True

    def test_complete_graph_k4(self):
        # Complete graph K4: optimal B*(K4) = 1
        G = nx.complete_graph(4)
        solver = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)
        res = solver.solve(method="direct_optimize")
        assert res["optimal_k"] == 1
        assert res["verified"] is True

    def test_check_sat_decision(self):
        G = nx.path_graph(4)
        solver = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)

        # k = 2 is feasible for P4
        is_sat_2, labeling_2, _, _ = solver.check_sat(2)
        assert is_sat_2 is True
        assert labeling_2 is not None
        valid_2, min_d_2, _ = solver.verify_solution(labeling_2, 2)
        assert valid_2 is True
        assert min_d_2 >= 2

        # k = 3 is infeasible for P4 (B*(P4) = 2)
        is_sat_3, _, _, _ = solver.check_sat(3)
        assert is_sat_3 is False

    def test_symmetry_breaking_consistency(self):
        G = nx.path_graph(5)
        s_sym = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)
        res_sym = s_sym.solve()

        s_nosym = AntibandwidthCPSolver(G, break_symmetry=False, verbose=False)
        res_nosym = s_nosym.solve()

        assert res_sym["optimal_k"] == res_nosym["optimal_k"]
        assert res_sym["verified"] is True
        assert res_nosym["verified"] is True

    @pytest.mark.skipif(not HAS_PYSAT, reason="PySAT required for equivalence test")
    def test_equivalence_with_sat_solver(self):
        # Equivalence check on P6: both SAT and CP-SAT must yield B*(P6) = 3
        G = nx.path_graph(6)
        sat_solver = AntibandwidthSolver(G, solver_name="cadical153", encoding="direct", verbose=False)
        res_sat = sat_solver.solve()

        cp_solver = AntibandwidthCPSolver(G, break_symmetry=True, verbose=False)
        res_cp = cp_solver.solve()

        assert res_sat["optimal_k"] == res_cp["optimal_k"]
        assert res_sat["optimal_k"] == 3
        assert res_sat["verified"] is True
        assert res_cp["verified"] is True

