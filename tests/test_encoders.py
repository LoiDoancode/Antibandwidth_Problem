"""Unit tests for Direct, Order, and Staircase SCL SAT Encoders."""

from pathlib import Path
import pytest
import networkx as nx
from src.sat_encoder import AntibandwidthSATEncoder
from src.order_encoder import AntibandwidthOrderEncoder
from src.scl_encoder import AntibandwidthSCLEncoder
from src.solver import AntibandwidthSolver
from src.graph_loader import load_graph


class TestDirectEncoder:
    """Tests for AntibandwidthSATEncoder (Direct Encoding)."""

    def test_var_mapping_and_decoding(self):
        G = nx.path_graph(4)
        encoder = AntibandwidthSATEncoder(G)
        n = 4

        # Test index mapping formula: v * n + p
        for v in range(n):
            for p in range(1, n + 1):
                lit = encoder.var(v, p)
                assert lit == v * n + p
                dec_v, dec_p = encoder.decode_var(lit)
                assert dec_v == v
                assert dec_p == p

    def test_encode_generates_clauses(self):
        G = nx.path_graph(4)
        encoder = AntibandwidthSATEncoder(G, break_symmetry=False)
        cnf = encoder.encode(k=2)

        # Must have clauses for ALO, AMO, and edge distances
        assert len(cnf.clauses) > 0
        # Check ALO: each vertex has at least one position
        # For n=4, ALO clauses have length 4
        alo_clauses = [c for c in cnf.clauses if len(c) == 4 and all(x > 0 for x in c)]
        assert len(alo_clauses) == 4

    def test_symmetry_breaking_adds_clauses(self):
        G = nx.path_graph(4)
        enc_no_sym = AntibandwidthSATEncoder(G, break_symmetry=False)
        cnf_no_sym = enc_no_sym.encode(k=2)

        enc_sym = AntibandwidthSATEncoder(G, break_symmetry=True)
        cnf_sym = enc_sym.encode(k=2)

        # Symmetry breaking eliminates assignments where pivot > ceil(n/2)
        assert len(cnf_sym.clauses) > len(cnf_no_sym.clauses)

    def test_decode_model(self):
        G = nx.path_graph(3)
        encoder = AntibandwidthSATEncoder(G)
        # Model representing: v0 -> 1, v1 -> 3, v2 -> 2
        # v0, pos1: 0*3 + 1 = 1
        # v1, pos3: 1*3 + 3 = 6
        # v2, pos2: 2*3 + 2 = 8
        model = [1, 6, 8]
        labeling = encoder.decode_model(model)
        assert labeling == {0: 1, 3: 2, 1: 3} or labeling == {0: 1, 1: 3, 2: 2}

    def test_arbitrary_node_labels(self):
        G = nx.Graph()
        G.add_edge("A", "B")
        G.add_edge("B", "C")
        encoder = AntibandwidthSATEncoder(G)
        cnf = encoder.encode(k=1)
        assert len(cnf.clauses) > 0
        assert "A" in encoder.node_to_idx
        assert "B" in encoder.node_to_idx

    def test_get_stats(self):
        G = nx.path_graph(4)
        encoder = AntibandwidthSATEncoder(G, break_symmetry=True)
        stats = encoder.get_stats(k=2)
        assert stats["num_nodes"] == 4
        assert stats["num_variables"] == 16
        assert stats["alo_vertex_clauses"] == 4
        assert stats["total_clauses"] > 0

    def test_export_dimacs_file(self, tmp_path):
        G = nx.path_graph(3)
        encoder = AntibandwidthSATEncoder(G)
        file_path = tmp_path / "test_p3.cnf"
        encoder.export_dimacs(k=1, filepath=str(file_path))
        assert file_path.exists()
        assert file_path.stat().st_size > 0

    def test_invalid_amo_encoding_raises(self):
        G = nx.path_graph(4)
        with pytest.raises(ValueError):
            AntibandwidthSATEncoder(G, amo_encoding="unknown_amo")

    @pytest.mark.parametrize("amo_encoding", ["seqcounter", "commander", "totalizer", "ladder", "bitwise"])
    def test_advanced_amo_encodings_clauses_and_vars(self, amo_encoding, tmp_path):
        # For n = 10, pairwise AMO needs 2 * 10 * 45 = 900 clauses
        G = nx.path_graph(10)
        enc_pw = AntibandwidthSATEncoder(G, break_symmetry=True, amo_encoding="pairwise")
        enc_adv = AntibandwidthSATEncoder(G, break_symmetry=True, amo_encoding=amo_encoding)

        cnf_adv = enc_adv.encode(k=3)
        stats_pw = enc_pw.get_stats(k=3)
        stats_adv = enc_adv.get_stats(k=3)

        assert cnf_adv.nv == stats_adv["num_variables"]
        assert stats_adv["aux_variables"] > 0
        assert stats_adv["total_clauses"] == len(cnf_adv.clauses)
        # Sequential Counter and Commander strictly reduce AMO clause count vs Pairwise at n=10
        if amo_encoding in ("seqcounter", "commander"):
            assert (
                stats_adv["amo_vertex_clauses"] + stats_adv["amo_position_clauses"]
                < stats_pw["amo_vertex_clauses"] + stats_pw["amo_position_clauses"]
            )

        dimacs_path = tmp_path / f"test_{amo_encoding}.cnf"
        enc_adv.export_dimacs(k=3, filepath=str(dimacs_path))
        header = dimacs_path.read_text(encoding="utf-8").splitlines()[0]
        assert header.startswith(f"p cnf {cnf_adv.nv} {len(cnf_adv.clauses)}")



class TestOrderEncoder:
    """Tests for AntibandwidthOrderEncoder (Order Encoding)."""

    def test_var_mapping_and_decoding(self):
        G = nx.path_graph(4)
        encoder = AntibandwidthOrderEncoder(G)
        n = 4

        # Test index mapping formula: v * (n - 1) + p
        for v in range(n):
            for p in range(1, n):
                lit = encoder.var(v, p)
                assert lit == v * (n - 1) + p
                dec_v, dec_p = encoder.decode_var(lit)
                assert dec_v == v
                assert dec_p == p

    def test_encode_generates_monotonicity(self):
        G = nx.path_graph(3)
        encoder = AntibandwidthOrderEncoder(G, break_symmetry=False)
        cnf = encoder.encode(k=1)
        assert len(cnf.clauses) > 0

    def test_order_symmetry_breaking_unit_clause(self):
        G = nx.path_graph(4)
        enc_no_sym = AntibandwidthOrderEncoder(G, break_symmetry=False)
        cnf_no_sym = enc_no_sym.encode(k=2)

        enc_sym = AntibandwidthOrderEncoder(G, break_symmetry=True)
        cnf_sym = enc_sym.encode(k=2)

        # Symmetry breaking in order encoding adds 1 unit clause: y_{pivot, ceil(n/2)}
        assert len(cnf_sym.clauses) == len(cnf_no_sym.clauses) + 1


class TestSCLEncoder:
    """Tests for AntibandwidthSCLEncoder (Staircase Sequential Counter) and incremental search."""

    def test_path_graph_p4(self):
        g = nx.path_graph(4)
        solver = AntibandwidthSolver(g, encoding="scl", solver_name="cadical153", verbose=False)
        res = solver.solve(method="incremental")
        direct_res = AntibandwidthSolver(g, encoding="direct", solver_name="cadical153", verbose=False).solve()
        assert res["optimal_k"] == direct_res["optimal_k"]
        assert res["verified"] is True

    def test_cycle_graph_c5(self):
        g = nx.cycle_graph(5)
        scl_res = AntibandwidthSolver(g, encoding="scl", solver_name="cadical153", verbose=False).solve(method="incremental")
        direct_res = AntibandwidthSolver(g, encoding="direct", solver_name="cadical153", verbose=False).solve()
        assert scl_res["optimal_k"] == direct_res["optimal_k"] == 2
        assert scl_res["verified"] is True

    def test_complete_graph_k4(self):
        g = nx.complete_graph(4)
        scl_res = AntibandwidthSolver(g, encoding="scl", solver_name="cadical153", verbose=False).solve(method="binary_search")
        assert scl_res["optimal_k"] == 1
        assert scl_res["verified"] is True

    def test_symmetry_breaking_consistency(self):
        g = nx.wheel_graph(6)
        res_sym = AntibandwidthSolver(g, encoding="scl", break_symmetry=True, verbose=False).solve(method="incremental")
        res_nosym = AntibandwidthSolver(g, encoding="scl", break_symmetry=False, verbose=False).solve(method="incremental")
        assert res_sym["optimal_k"] == res_nosym["optimal_k"]
        assert res_sym["verified"] is True
        assert res_nosym["verified"] is True

    def test_can_24_equivalence_and_clause_reduction(self):
        path = Path("data/instance/harwell-boeing_v2/can___24.txt")
        if not path.exists():
            pytest.skip("can___24.txt not present")

        g, _ = load_graph(path)
        scl_res = AntibandwidthSolver(g, encoding="scl", solver_name="cadical153", verbose=False).solve(method="incremental")
        assert scl_res["optimal_k"] == 5
        assert scl_res["verified"] is True

        # Verify SCL produces significantly fewer clauses than Direct Pairwise at k=5
        scl_clauses = len(AntibandwidthSCLEncoder(g).encode(5).clauses)
        direct_clauses = len(AntibandwidthSATEncoder(g, amo_encoding="pairwise").encode(5).clauses)
        assert scl_clauses < direct_clauses


