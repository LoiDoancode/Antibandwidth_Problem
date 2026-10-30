"""Unit tests for Direct and Order SAT Encoders."""

import pytest
import networkx as nx
from src.sat_encoder import AntibandwidthSATEncoder
from src.order_encoder import AntibandwidthOrderEncoder


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
        assert labeling == {0: 1, 1: 3, 2: 2}


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

