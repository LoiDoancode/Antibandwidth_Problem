"""Unit and integration tests for visualizer module."""

import pytest
import tempfile
from pathlib import Path
import networkx as nx

import matplotlib
try:
    matplotlib.use("Agg")
except Exception:
    pass

from src.visualizer import (
    print_ascii_linear_layout,
    visualize_antibandwidth_labeling,
    visualize_benchmark_comparison,
    visualize_speedup_comparison,
    HAS_MATPLOTLIB,
    HAS_CNSPLOTS,
)


class TestVisualizer:
    """Tests for visualization functions."""

    def test_ascii_linear_layout_output(self, capsys):
        G = nx.path_graph(4)
        labeling = {0: 1, 1: 3, 2: 2, 3: 4}
        print_ascii_linear_layout(4, list(G.edges()), labeling, k=1)
        captured = capsys.readouterr()
        assert "LINEAR ANTIBANDWIDTH LAYOUT" in captured.out
        assert "Position :" in captured.out
        assert "Vertex   :" in captured.out

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib required for visualizer tests")
    def test_visualize_antibandwidth_labeling_file(self):
        G = nx.path_graph(4)
        labeling = {0: 1, 1: 3, 2: 2, 3: 4}
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            ok = visualize_antibandwidth_labeling(
                graph=G,
                labeling=labeling,
                k=1,
                save_path=tmp_path,
                show=False,
            )
            assert ok is True
            assert Path(tmp_path).exists()
            assert Path(tmp_path).stat().st_size > 0
        finally:
            if Path(tmp_path).exists():
                Path(tmp_path).unlink()

    @pytest.mark.skipif(not HAS_MATPLOTLIB, reason="matplotlib required for benchmark plot tests")
    def test_visualize_benchmark_comparison_and_speedup(self):
        records = [
            {"graph": "p6", "config": "DIRECT_glucose4_Sym", "encoding": "direct", "solver": "glucose4", "symmetry": True, "time": 0.01, "clauses": 100},
            {"graph": "p6", "config": "DIRECT_glucose4_NoSym", "encoding": "direct", "solver": "glucose4", "symmetry": False, "time": 0.02, "clauses": 98},
            {"graph": "p6", "config": "CPSAT_Sym", "encoding": "cpsat", "solver": "cpsat", "symmetry": True, "time": 0.008, "clauses": 15},
            {"graph": "p6", "config": "CPSAT_NoSym", "encoding": "cpsat", "solver": "cpsat", "symmetry": False, "time": 0.015, "clauses": 15},
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            p_time = Path(tmpdir) / "time.png"
            p_clauses = Path(tmpdir) / "clauses.png"
            p_speedup = Path(tmpdir) / "speedup.png"

            assert visualize_benchmark_comparison(records, metric="time", save_path=str(p_time), show=False)
            assert p_time.exists() and p_time.stat().st_size > 0

            assert visualize_benchmark_comparison(records, metric="clauses", save_path=str(p_clauses), show=False)
            assert p_clauses.exists() and p_clauses.stat().st_size > 0

            assert visualize_speedup_comparison(records, save_path=str(p_speedup), show=False)
            assert p_speedup.exists() and p_speedup.stat().st_size > 0
