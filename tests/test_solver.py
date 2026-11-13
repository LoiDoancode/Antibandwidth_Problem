"""Unit and integration tests for AntibandwidthSolver."""

import pytest
import networkx as nx
from src.solver import AntibandwidthSolver, HAS_PYSAT


@pytest.mark.skipif(not HAS_PYSAT, reason="python-sat is required for solver tests")
class TestAntibandwidthSolver:
    """Tests for Antibandwidth SAT Solver."""

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

    def test_direct_vs_order_encoding_consistency(self):
        # Both encodings must yield the exact same optimal k for P_5
        G = nx.path_graph(5)

        s_direct = AntibandwidthSolver(G, encoding="direct", break_symmetry=True, verbose=False)
        res_direct = s_direct.solve()

        s_order = AntibandwidthSolver(G, encoding="order", break_symmetry=True, verbose=False)
        res_order = s_order.solve()

        assert res_direct["optimal_k"] == res_order["optimal_k"]
        assert res_direct["verified"] is True
        assert res_order["verified"] is True

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

