"""Graph Loader for Antibandwidth Problem.

Supports:
- MatrixMarket files (.mtx)
- Harwell-Boeing / Rutherford-Boeing files (.rb, .rua, .rsa)
- Simple edge list files (.txt, .edges)
"""

from pathlib import Path
from typing import Tuple, Union, Optional
import networkx as nx


class GraphLoader:
    """Utility class to parse benchmark graph files into NetworkX Graph objects."""

    @staticmethod
    def from_matrix_market(filepath: Union[str, Path]) -> nx.Graph:
        """Parse a Matrix Market (.mtx) file into an undirected simple graph.

        Uses scipy if installed, otherwise uses a pure Python fallback.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Matrix Market file not found: {filepath}")

        # Try scipy first
        try:
            from scipy.io import mmread
            mat = mmread(str(filepath))
            # Convert to coordinate format if needed
            coo = mat.tocoo()
            G = nx.Graph()
            G.add_nodes_from(range(mat.shape[0]))
            for u, v in zip(coo.row, coo.col):
                if u != v:  # Ignore self-loops
                    G.add_edge(int(u), int(v))
            return G
        except ImportError:
            pass

        # Fallback pure-Python parser for MatrixMarket coordinate format
        G = nx.Graph()
        with open(filepath, "r", encoding="utf-8") as f:
            lines = f.readlines()

        # Parse header
        line_idx = 0
        is_symmetric = False
        while line_idx < len(lines):
            line = lines[line_idx].strip()
            if line.startswith("%%MatrixMarket"):
                parts = line.lower().split()
                if "symmetric" in parts:
                    is_symmetric = True
                line_idx += 1
                break
            line_idx += 1

        # Skip comment lines
        while line_idx < len(lines) and lines[line_idx].strip().startswith("%"):
            line_idx += 1

        if line_idx >= len(lines):
            raise ValueError(f"Invalid MatrixMarket file: {filepath} has no size line")

        # Size line: nrows ncols nnz
        size_tokens = lines[line_idx].strip().split()
        num_rows = int(size_tokens[0])
        num_cols = int(size_tokens[1])
        num_nodes = max(num_rows, num_cols)
        G.add_nodes_from(range(num_nodes))
        line_idx += 1

        # Read entries (1-based indices in MatrixMarket)
        for i in range(line_idx, len(lines)):
            line = lines[i].strip()
            if not line or line.startswith("%"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                u = int(parts[0]) - 1
                v = int(parts[1]) - 1
                if u != v and 0 <= u < num_nodes and 0 <= v < num_nodes:
                    G.add_edge(u, v)

        return G

    @staticmethod
    def from_harwell_boeing(filepath: Union[str, Path]) -> nx.Graph:
        """Parse Harwell-Boeing / Rutherford-Boeing (.rb, .rua, .rsa) files.

        Handles standard Harwell-Boeing compressed column format and coordinate dumps.
        """
        filepath = Path(filepath)
        if not filepath.exists():
            raise FileNotFoundError(f"Harwell-Boeing file not found: {filepath}")

        # Try scipy first if available
        try:
            from scipy.io import hb_read
            mat = hb_read(str(filepath))
            coo = mat.tocoo()
            G = nx.Graph()
            G.add_nodes_from(range(mat.shape[0]))
            for u, v in zip(coo.row, coo.col):
                if u != v:
                    G.add_edge(int(u), int(v))
            return G
        except (ImportError, Exception):
            pass

        # Text-based fallback reader
        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()

        if len(lines) < 4:
            raise ValueError(f"File {filepath} is too short to be a valid Harwell-Boeing file.")

        # Line 2: Totcrd, Ptrcrd, Indcrd, Valcrd, Rhscrd
        line2_tokens = lines[1].split()
        # Line 3: Matrix type (3 chars: e.g. RUA, RSA) + Nrow, Ncol, Nnz, Neltvl
        line3 = lines[2].strip()
        mat_type = line3[:3].upper()
        rest3 = line3[3:].split()
        if len(rest3) >= 3:
            num_rows = int(rest3[0])
            num_cols = int(rest3[1])
            num_entries = int(rest3[2])
        else:
            raise ValueError(f"Unable to parse dimensions from Harwell-Boeing line 3: {line3}")

        ptrcrd = int(line2_tokens[1]) if len(line2_tokens) > 1 else 0
        indcrd = int(line2_tokens[2]) if len(line2_tokens) > 2 else 0

        # Optional line 5 if Rhscrd > 0
        rhscrd = int(line2_tokens[4]) if len(line2_tokens) > 4 else 0
        curr_line = 4
        if len(lines) > 4 and lines[4].strip().startswith("("):
            curr_line = 5

        # Read column pointers
        colptr = []
        for _ in range(ptrcrd):
            if curr_line < len(lines):
                tokens = lines[curr_line].split()
                colptr.extend([int(t) for t in tokens])
                curr_line += 1

        # Read row indices
        rowind = []
        for _ in range(indcrd):
            if curr_line < len(lines):
                tokens = lines[curr_line].split()
                rowind.extend([int(t) for t in tokens])
                curr_line += 1

        num_nodes = max(num_rows, num_cols)
        G = nx.Graph()
        G.add_nodes_from(range(num_nodes))

        # Reconstruct graph from Harwell-Boeing 1-based Compressed Column pointers
        if len(colptr) >= num_cols + 1 and len(rowind) >= num_entries:
            for j in range(num_cols):
                start = colptr[j] - 1
                end = colptr[j + 1] - 1
                for idx in range(start, min(end, len(rowind))):
                    i = rowind[idx] - 1
                    if i != j and 0 <= i < num_nodes and 0 <= j < num_nodes:
                        G.add_edge(i, j)
        else:
            # If pointer parsing failed, attempt coordinate-fallback
            for idx in range(curr_line, len(lines)):
                parts = lines[idx].strip().split()
                if len(parts) >= 2:
                    try:
                        u = int(parts[0]) - 1
                        v = int(parts[1]) - 1
                        if u != v:
                            G.add_edge(u, v)
                    except ValueError:
                        continue

        return G

    @staticmethod
    def from_edge_list(filepath: Union[str, Path]) -> nx.Graph:
        """Parse simple text edge list file (space/tab/comma separated u v)."""
        filepath = Path(filepath)
        G = nx.Graph()
        raw_edges = []
        node_set = set()

        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or line.startswith("%"):
                    continue
                parts = line.replace(",", " ").split()
                if len(parts) >= 2:
                    u = int(parts[0])
                    v = int(parts[1])
                    if u != v:
                        raw_edges.append((u, v))
                        node_set.add(u)
                        node_set.add(v)

        # Map nodes to contiguous 0-indexed integers
        sorted_nodes = sorted(node_set)
        node_map = {old: new for new, old in enumerate(sorted_nodes)}
        G.add_nodes_from(range(len(sorted_nodes)))
        for u, v in raw_edges:
            G.add_edge(node_map[u], node_map[v])

        return G


def load_graph(filepath: Union[str, Path]) -> Tuple[nx.Graph, dict]:
    """Load a graph file based on extension and return graph + summary metadata."""
    path = Path(filepath)
    suffix = path.suffix.lower()

    if suffix in [".mtx", ".mm"]:
        G = GraphLoader.from_matrix_market(path)
    elif suffix in [".rb", ".rua", ".rsa", ".hb"]:
        G = GraphLoader.from_harwell_boeing(path)
    else:
        # Fallback based on content detection
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                first_line = f.readline()
                if "matrixmarket" in first_line.lower():
                    G = GraphLoader.from_matrix_market(path)
                else:
                    G = GraphLoader.from_edge_list(path)
        except Exception:
            G = GraphLoader.from_edge_list(path)

    # Relabel nodes to contiguous 0..n-1 if not already
    mapping = {node: idx for idx, node in enumerate(sorted(G.nodes()))}
    G = nx.relabel_nodes(G, mapping)

    info = {
        "filename": path.name,
        "num_vertices": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0,
        "max_degree": max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0,
        "min_degree": min(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0,
    }

    return G, info
