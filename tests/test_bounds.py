"""Unit and integration tests for Level-1 LB and UB bounds."""

import pytest
import networkx as nx

from src.bounds import (
    compute_greedy_lower_bound,
    compute_level1_bounds,
    compute_upper_bound,
)
from src.solver import AntibandwidthSolver, HAS_PYSAT
from src.cp_solver import AntibandwidthCPSolver, HAS_ORTOOLS


class TestLevel1Bounds:
    """Tests for Level-1 LB and UB functions."""

    def test_trivial_graphs(self):
        assert compute_upper_bound(nx.Graph()) == 0
        assert compute_upper_bound(nx.empty_graph(1)) == 0
        assert compute_upper_bound(nx.empty_graph(5)) == 4

        b1 = compute_level1_bounds(nx.empty_graph(1))
        assert b1["lb"] == 0 and b1["ub"] == 0

        b5 = compute_level1_bounds(nx.empty_graph(5))
        assert b5["lb"] == 4 and b5["ub"] == 4

    def test_known_graph_families(self):
        # Star graph K_{1, 5}: n=6, max_deg=5 => UB = 6 - 5 = 1, LB = 1
        star = nx.star_graph(5)
        b_star = compute_level1_bounds(star)
        assert b_star["ub"] == 1
        assert b_star["lb"] == 1

        # Complete graph K_5: n=5, max_deg=4 => UB = 1, LB = 1
        k5 = nx.complete_graph(5)
        b_k5 = compute_level1_bounds(k5)
        assert b_k5["ub"] == 1
        assert b_k5["lb"] == 1

        # Path P_6: n=6, min_deg=1, max_deg=2 => UB <= (6 + 1 - 1) // 2 = 3
        p6 = nx.path_graph(6)
        b_p6 = compute_level1_bounds(p6)
        assert 1 <= b_p6["lb"] <= 3
        assert b_p6["ub"] == 3

    def test_disconnected_with_isolated_vertices(self):
        # 1 edge (0, 1) and 4 isolated vertices => n=6, B*(G) = 5 > n//2
        G = nx.empty_graph(6)
        G.add_edge(0, 1)
        bounds = compute_level1_bounds(G)
        assert bounds["ub"] == 5
        assert bounds["lb"] <= 5

    @pytest.mark.skipif(not HAS_PYSAT, reason="python-sat is required")
    def test_bounds_soundness_and_solver_consistency(self):
        graphs = [
            nx.path_graph(6),
            nx.cycle_graph(7),
            nx.erdos_renyi_graph(8, 0.4, seed=42),
            nx.erdos_renyi_graph(9, 0.3, seed=7),
        ]
        for G in graphs:
            if G.number_of_edges() == 0:
                continue
            bounds = compute_level1_bounds(G)
            s_bounded = AntibandwidthSolver(G, encoding="scl", verbose=False)
            res_bounded = s_bounded.solve(method="binary_search", use_bounds=True)

            s_unbounded = AntibandwidthSolver(G, encoding="scl", verbose=False)
            res_unbounded = s_unbounded.solve(method="binary_search", use_bounds=False)

            assert res_bounded["optimal_k"] == res_unbounded["optimal_k"]
            assert bounds["lb"] <= res_bounded["optimal_k"] <= bounds["ub"]
            assert res_bounded["verified"] is True

            # Check greedy labeling validity
            valid, min_d, _ = s_bounded.verify_solution(bounds["lb_labeling"], bounds["lb"])
            assert valid is True
            assert min_d == bounds["lb"]

    @pytest.mark.skipif(not HAS_ORTOOLS, reason="OR-Tools is required")
    def test_cp_solver_with_bounds(self):
        G = nx.cycle_graph(6)
        s_opt = AntibandwidthCPSolver(G, verbose=False)
        res_opt = s_opt.solve(method="direct_optimize", use_bounds=True)
        res_bs = s_opt.solve(method="binary_search", use_bounds=True)
        res_raw = s_opt.solve(method="direct_optimize", use_bounds=False)

        assert res_opt["optimal_k"] == res_bs["optimal_k"] == res_raw["optimal_k"]
        assert res_opt["verified"] is True
        assert res_bs["verified"] is True
