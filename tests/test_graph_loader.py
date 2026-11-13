"""Unit tests for GraphLoader."""

import pytest
import tempfile
from pathlib import Path
import networkx as nx
from src.graph_loader import load_graph, GraphLoader


class TestGraphLoader:
    """Tests for loading various graph format benchmarks."""

    def test_load_coordinate_format(self):
        # Create a temporary coordinate format graph file
        content = """%%MatrixMarket matrix coordinate pattern symmetric
4 4 3
1 2
2 3
3 4
"""
        with tempfile.NamedTemporaryFile("w", suffix=".mtx", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            G, info = load_graph(tmp_path)
            assert G.number_of_nodes() == 4
            assert G.number_of_edges() == 3
            assert info["num_vertices"] == 4
            assert info["num_edges"] == 3
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_load_simple_edge_list(self):
        content = """# Sample edge list
0 1
1 2
2 3
"""
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as tmp:
            tmp.write(content)
            tmp_path = Path(tmp.name)

        try:
            G, info = load_graph(tmp_path)
            assert G.number_of_nodes() == 4
            assert G.number_of_edges() == 3
            assert set(G.nodes()) == {0, 1, 2, 3}
        finally:
            if tmp_path.exists():
                tmp_path.unlink()

    def test_file_not_found_raises_error(self):
        with pytest.raises(FileNotFoundError):
            load_graph("non_existent_graph_path_12345.mtx")

    def test_load_can_24_if_present(self):
        path = Path("data/instance/harwell-boeing_v2/can___24.txt")
        if path.exists():
            G, info = load_graph(path)
            assert G.number_of_nodes() == 24
            assert info["num_vertices"] == 24
            assert G.number_of_edges() > 0

