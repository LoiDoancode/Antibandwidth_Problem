"""Graph Loader for Antibandwidth Problem.

Supports:
- MatrixMarket files (.mtx, .mm, .txt with %%MatrixMarket header)
- Coordinate format without header (nrows ncols nnz followed by 1-based u v)
  (e.g., Harwell-Boeing benchmark instances in data/instance/harwell-boeing/small/)
- Grid / Mesh benchmark files with problem comment lines (e.g., data/instance/grids/)
- Harwell-Boeing / Rutherford-Boeing compressed column files (.rb, .rua, .rsa, .hb)
- Simple edge list files (.txt, .edges)
"""

from pathlib import Path
from typing import Tuple, Union, Optional, List
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
            coo = mat.tocoo()
            G = nx.Graph()
            G.add_nodes_from(range(mat.shape[0]))
            for u, v in zip(coo.row, coo.col):
                if u != v:  # Ignore self-loops
                    G.add_edge(int(u), int(v))
            return G
        except (ImportError, Exception):
            pass

        # Fallback pure-Python parser for MatrixMarket coordinate format
        return GraphLoader.from_coordinate_format(filepath)

    @staticmethod
    def from_coordinate_format(filepath: Union[str, Path]) -> nx.Graph:
        """Parse coordinate format: optional comments, then 'nrows ncols nnz', then lines 'u v' (1-based).

        Matches Harwell-Boeing instance dumps (e.g. bcsstk01, can___62, mesh files).
        """
        filepath = Path(filepath)
        G = nx.Graph()

        with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
            lines = [line.strip() for line in f if line.strip()]

        if not lines:
            raise ValueError(f"File {filepath} is empty.")

        # Find the size line: first line with 3 integers (nrows, ncols, nnz)
        line_idx = 0
        num_rows = num_cols = nnz = None
        while line_idx < len(lines):
            line = lines[line_idx]
            # Skip comments
            if line.startswith("%") or line.startswith("#") or line.lower().startswith("problem"):
                line_idx += 1
                continue

            parts = line.split()
            if len(parts) >= 3:
                try:
                    num_rows = int(parts[0])
                    num_cols = int(parts[1])
                    nnz = int(parts[2])
                    line_idx += 1
                    break
                except ValueError:
                    line_idx += 1
                    continue
            line_idx += 1

        if num_rows is None:
            # If no size line found, fallback to edge list
            return GraphLoader.from_edge_list(filepath)

        num_nodes = max(num_rows, num_cols)
        G.add_nodes_from(range(num_nodes))

        # Read coordinate pairs
        for idx in range(line_idx, len(lines)):
            line = lines[idx]
            if line.startswith("%") or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) >= 2:
                try:
                    u = int(parts[0]) - 1
                    v = int(parts[1]) - 1
                    if u != v and 0 <= u < num_nodes and 0 <= v < num_nodes:
                        G.add_edge(u, v)
                except ValueError:
                    continue

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
            # If too short, try coordinate reader
            return GraphLoader.from_coordinate_format(filepath)

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
            return GraphLoader.from_coordinate_format(filepath)

        ptrcrd = int(line2_tokens[1]) if len(line2_tokens) > 1 else 0
        indcrd = int(line2_tokens[2]) if len(line2_tokens) > 2 else 0

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
            return GraphLoader.from_coordinate_format(filepath)

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
                if not line or line.startswith("#") or line.startswith("%") or line.lower().startswith("problem"):
                    continue
                parts = line.replace(",", " ").split()
                if len(parts) >= 2:
                    try:
                        u = int(parts[0])
                        v = int(parts[1])
                        if u != v:
                            raw_edges.append((u, v))
                            node_set.add(u)
                            node_set.add(v)
                    except ValueError:
                        continue

        if not node_set:
            return G

        # Map nodes to contiguous 0-indexed integers
        sorted_nodes = sorted(node_set)
        node_map = {old: new for new, old in enumerate(sorted_nodes)}
        G.add_nodes_from(range(len(sorted_nodes)))
        for u, v in raw_edges:
            G.add_edge(node_map[u], node_map[v])

        return G


def resolve_graph_path(input_str: Union[str, Path], base_dirs: Optional[List[str]] = None) -> Path:
    """Resolve a graph file path, automatically searching inside data/ and data/instance/."""
    p = Path(input_str)
    if p.exists() and p.is_file():
        return p

    if base_dirs is None:
        base_dirs = [
            "data/instance/harwell-boeing_v2",
            "data/instance/harwell-boeing/small",
            "data/instance/harwell-boeing",
            "data/instance",
            "data",
            ".",
        ]

    for b in base_dirs:
        base = Path(b)
        if not base.exists():
            continue

        # Direct child
        direct = base / input_str
        if direct.exists() and direct.is_file():
            return direct

        # Search recursively for exact name or name with common extensions
        for match in base.rglob(f"*{p.name}*"):
            if match.is_file() and (match.name == p.name or match.stem == p.stem):
                return match

    return p


def load_graph(filepath: Union[str, Path]) -> Tuple[nx.Graph, dict]:
    """Load a graph file based on extension/content and return graph + summary metadata."""
    path = resolve_graph_path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Graph file not found: {filepath}")

    suffix = path.suffix.lower()

    if suffix in [".mtx", ".mm"]:
        G = GraphLoader.from_matrix_market(path)
    elif suffix in [".rb", ".rua", ".rsa", ".hb"]:
        G = GraphLoader.from_harwell_boeing(path)
    else:
        # Content-based detection
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                header_sample = [f.readline().strip() for _ in range(5)]

            has_mm = any("matrixmarket" in l.lower() for l in header_sample)
            if has_mm:
                G = GraphLoader.from_matrix_market(path)
            else:
                # Check if it has a 3-token size line (coordinate format)
                has_size_line = False
                for line in header_sample:
                    if line.startswith("%") or line.startswith("#") or line.lower().startswith("problem"):
                        continue
                    tokens = line.split()
                    if len(tokens) >= 3 and all(t.isdigit() for t in tokens[:3]):
                        has_size_line = True
                        break
                if has_size_line:
                    G = GraphLoader.from_coordinate_format(path)
                else:
                    G = GraphLoader.from_edge_list(path)
        except Exception:
            G = GraphLoader.from_coordinate_format(path)

    # Relabel nodes to contiguous 0..n-1 if not already
    mapping = {node: idx for idx, node in enumerate(sorted(G.nodes()))}
    G = nx.relabel_nodes(G, mapping)

    info = {
        "filename": path.name,
        "filepath": str(path.resolve()),
        "num_vertices": G.number_of_nodes(),
        "num_edges": G.number_of_edges(),
        "density": round(nx.density(G), 4) if G.number_of_nodes() > 1 else 0.0,
        "max_degree": max(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0,
        "min_degree": min(dict(G.degree()).values()) if G.number_of_nodes() > 0 else 0,
    }

    return G, info
