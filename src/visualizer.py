"""Visualization module for Antibandwidth Problem (ABP)"""

from typing import Dict, List, Optional, Tuple, Any
from pathlib import Path
import networkx as nx

try:
    import matplotlib
    try:
        matplotlib.use("Agg")
    except Exception:
        pass
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

try:
    import cnsplots as cns
    HAS_CNSPLOTS = True
except ImportError:
    HAS_CNSPLOTS = False


def print_ascii_linear_layout(n: int, edges: List[Tuple[int, int]], labeling: Dict[int, int], k: int) -> None:
    """Prints a clean ASCII representation of the 1D linear layout in the terminal."""
    pos_to_vertex = {p: v for v, p in labeling.items()}
    print("\n" + "=" * 65)
    print(f" LINEAR ANTIBANDWIDTH LAYOUT (Target k = {k})")
    print("=" * 65)

    header = "Position : " + "  ".join(f"{p:3d}" for p in range(1, n + 1))
    nodes_line = "Vertex   : " + "  ".join(f"[{pos_to_vertex.get(p, '?'):1d}]" if pos_to_vertex.get(p, -1) < 10 
                                          else f"[{pos_to_vertex.get(p, '?'):2d}]" for p in range(1, n + 1))
    print(header)
    print("-" * len(header))
    print(nodes_line)
    print("-" * len(header))

    # Print edge distances
    print("\nEdge Distances (|f(u) - f(v)| >= k):")
    critical_edges = []
    for u, v in sorted(edges):
        dist = abs(labeling[u] - labeling[v])
        is_bottleneck = (dist == k)
        mark = " <-- [CRITICAL / BOTTLENECK]" if is_bottleneck else ""
        print(f"  Edge ({u:2d}, {v:2d}): |{labeling[u]:2d} - {labeling[v]:2d}| = {dist:2d} {mark}")
        if is_bottleneck:
            critical_edges.append((u, v, dist))

    if critical_edges:
        print(f"\n[*] Found {len(critical_edges)} critical edge(s) achieving exact minimum distance k = {k}.")
    print("=" * 65 + "\n")


def visualize_antibandwidth_labeling(
    graph: nx.Graph,
    labeling: Dict[int, int],
    k: int,
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    show: bool = False,
) -> bool:
    n = graph.number_of_nodes()
    edges = list(graph.edges())

    # Always print ASCII layout to console
    print_ascii_linear_layout(n, edges, labeling, k)

    if not HAS_MATPLOTLIB:
        print("[Warning] matplotlib is not installed. To generate graphical plots, run: pip install matplotlib")
        return False

    if HAS_CNSPLOTS:
        try:
            cns.setup_matplotlib()
        except Exception:
            pass

    # Create figure with 2 subplots
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 7))
    if title is None:
        title = f"Antibandwidth Problem Solution: B*(G) = {k} (n = {n}, m = {len(edges)})"
    fig.suptitle(title, fontsize=14, fontweight="bold", y=0.98)

    # -------------------------------------------------------------
    # Subplot 1: Network graph layout
    # -------------------------------------------------------------
    pos_layout = nx.circular_layout(graph) if n <= 15 else nx.spring_layout(graph, seed=42)

    # Node colors based on position
    node_positions = [labeling.get(node, 1) for node in graph.nodes()]
    node_labels = {node: f"v{node}\n[{labeling.get(node, '?')}]" for node in graph.nodes()}

    # Separate normal edges and bottleneck (critical) edges
    critical_edges = []
    normal_edges = []
    edge_labels = {}

    for u, v in graph.edges():
        d = abs(labeling[u] - labeling[v])
        edge_labels[(u, v)] = f"d={d}"
        if d == k:
            critical_edges.append((u, v))
        else:
            normal_edges.append((u, v))

    # Draw nodes
    nodes_collection = nx.draw_networkx_nodes(
        graph,
        pos_layout,
        ax=ax1,
        node_size=800,
        node_color=node_positions,
        cmap=plt.cm.coolwarm,
        edgecolors="black",
        linewidths=1.5,
    )
    nx.draw_networkx_labels(graph, pos_layout, labels=node_labels, ax=ax1, font_size=9, font_weight="bold")

    # Draw normal edges
    nx.draw_networkx_edges(
        graph,
        pos_layout,
        edgelist=normal_edges,
        ax=ax1,
        edge_color="gray",
        width=1.5,
        alpha=0.7,
    )
    # Draw critical edges (bottleneck distance == k)
    if critical_edges:
        nx.draw_networkx_edges(
            graph,
            pos_layout,
            edgelist=critical_edges,
            ax=ax1,
            edge_color="red",
            width=2.5,
            style="solid",
            label=f"Critical Edge (dist = {k})",
        )

    # Edge distance labels
    nx.draw_networkx_edge_labels(graph, pos_layout, edge_labels=edge_labels, ax=ax1, font_size=8, font_color="darkblue")

    cbar = plt.colorbar(nodes_collection, ax=ax1, fraction=0.046, pad=0.04)
    cbar.set_label("Assigned Position f(v) in {1 .. n}", fontsize=9)
    ax1.set_title("Graph Representation (Red = Bottleneck Edges)", fontsize=11, fontweight="semibold")
    ax1.axis("off")

    # -------------------------------------------------------------
    # Subplot 2: 1D Linear Permutation Layout with Arcs
    # -------------------------------------------------------------
    ax2.set_xlim(0, n + 1)
    # Determine vertical height needed for largest arc
    max_dist = max([abs(labeling[u] - labeling[v]) for u, v in edges], default=1)
    ax2.set_ylim(-1.5, max(4.0, (max_dist / 2) * 0.75 + 1.0))

    # Draw baseline axis
    ax2.axhline(0, color="black", linewidth=1.2, zorder=1)
    ax2.set_xticks(range(1, n + 1))
    ax2.set_xlabel("Linear Position p in {1, ..., n}", fontsize=10, fontweight="bold")
    ax2.set_yticks([])

    # Place vertices on line
    for v in graph.nodes():
        p = labeling[v]
        ax2.scatter(p, 0, s=350, zorder=5, color=plt.cm.coolwarm((p - 1) / max(1, n - 1)), edgecolors="black", linewidth=1.5)
        ax2.text(p, -0.6, f"v{v}", ha="center", va="top", fontsize=9, fontweight="bold")

    # Draw curved arcs for edges
    for u, v in edges:
        p_u = labeling[u]
        p_v = labeling[v]
        d = abs(p_u - p_v)
        center_x = (p_u + p_v) / 2.0
        width = d
        height = d * 0.6  # Height proportional to distance

        is_crit = (d == k)
        edge_color = "red" if is_crit else "navy"
        lw = 2.0 if is_crit else 1.2
        alpha = 0.9 if is_crit else 0.55

        arc = patches.Arc(
            (center_x, 0),
            width=width,
            height=height,
            theta1=0,
            theta2=180,
            color=edge_color,
            linewidth=lw,
            alpha=alpha,
            zorder=3,
        )
        ax2.add_patch(arc)
        # Label distance at top of arc
        ax2.text(center_x, height / 2 + 0.1, f"d={d}", ha="center", va="bottom", fontsize=7.5, color=edge_color, alpha=0.85)

    ax2.set_title(f"1D Embedding: All Edge Spans >= {k}", fontsize=11, fontweight="semibold")
    ax2.grid(True, axis="x", linestyle="--", alpha=0.5)

    plt.tight_layout()

    if save_path:
        out_file = Path(save_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"[+] Saved visualization plot to: {out_file.resolve()}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return True


def visualize_benchmark_comparison(
    benchmark_data: List[Dict[str, Any]],
    metric: str = "time",
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    show: bool = False,
) -> bool:
    """Plot comparative benchmark metrics across different algorithms / configurations.

    Args:
        benchmark_data: List of dicts, each with keys:
            ['graph', 'config', 'time', 'clauses', 'optimal_k', ...]
        metric: 'time' (Execution seconds) or 'clauses' (Number of CNF clauses).
        title: Optional custom plot title.
        save_path: Path to save the image (e.g., 'benchmark_results.png').
        show: If True, opens GUI window.

    Returns:
        True if plot saved/shown successfully.
    """
    if not HAS_MATPLOTLIB:
        print("[Warning] matplotlib is required for benchmark plots. Run: pip install matplotlib")
        return False

    if not benchmark_data:
        print("[Warning] No benchmark data provided.")
        return False

    if HAS_CNSPLOTS:
        try:
            cns.setup_matplotlib()
        except Exception:
            pass

    import numpy as np

    # Group by graph and configuration
    graphs = sorted(list(set(d["graph"] for d in benchmark_data)))
    configs = sorted(list(set(d["config"] for d in benchmark_data)))

    data_matrix = {cfg: [0.0] * len(graphs) for cfg in configs}
    for d in benchmark_data:
        g_idx = graphs.index(d["graph"])
        cfg = d["config"]
        raw_val = d["time"] if metric == "time" else d.get("clauses", 0)
        data_matrix[cfg][g_idx] = float(raw_val)

    x = np.arange(len(graphs))
    bar_width = 0.8 / max(1, len(configs))

    fig, ax = plt.subplots(figsize=(max(10, len(graphs) * 2), 6))

    colors = [
        "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728",
        "#9467bd", "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
    ]
    all_bars_info = []
    for i, cfg in enumerate(configs):
        offset = (i - len(configs) / 2 + 0.5) * bar_width
        vals = data_matrix[cfg]
        bars = ax.bar(
            x + offset,
            vals,
            width=bar_width,
            label=cfg,
            color=colors[i % len(colors)],
            edgecolor="black",
            alpha=0.9,
        )
        all_bars_info.append((i, cfg, bars))

    # Expand y-limit headroom for staggered labels & leader lines
    max_val = max(max(float(val) for val in v) for v in data_matrix.values()) if data_matrix else 1.0
    ax.set_ylim(0, max_val * 1.35)

    # Stagger offsets when configurations are clustered (prevents label collision on equal heights)
    stagger_offsets = [8, 28, 48, 68] if len(configs) > 4 else [8, 24]

    for i, cfg, bars in all_bars_info:
        stagger_level = i % len(stagger_offsets)
        y_offset = stagger_offsets[stagger_level] if len(configs) > 3 else 5

        for bar in bars:
            height = bar.get_height()
            if height > 0:
                fmt = f"{height:.3f}s" if metric == "time" else f"{int(height):,}"
                bar_x = bar.get_x() + bar.get_width() / 2

                # Leader line connecting text to top of bar when raised
                arrow_props = dict(
                    arrowstyle="-",
                    color="#555555",
                    lw=0.8,
                    linestyle=":",
                    shrinkA=2,
                    shrinkB=2,
                ) if y_offset > 12 else None

                ax.annotate(
                    fmt,
                    xy=(bar_x, height),
                    xytext=(0, y_offset),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=6.8,
                    fontweight="bold",
                    rotation=90,
                    arrowprops=arrow_props,
                )

    ax.set_xticks(x)
    ax.set_xticklabels(graphs, fontsize=10, fontweight="bold")
    ax.set_xlabel("Benchmark Graphs", fontsize=11, fontweight="bold")

    if metric == "time":
        ax.set_ylabel("Solving Time (seconds)", fontsize=11, fontweight="bold")
        default_title = "Execution Time Comparison Across Configurations"
    else:
        ax.set_ylabel("Number of CNF Clauses / Constraints", fontsize=11, fontweight="bold")
        default_title = "Clause Complexity Comparison Across Configurations"

    ax.set_title(title or default_title, fontsize=13, fontweight="bold", pad=15)
    ax.legend(frameon=True, shadow=True, bbox_to_anchor=(1.02, 1), loc="upper left")
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)

    plt.tight_layout()

    if save_path:
        out_file = Path(save_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"[+] Saved benchmark chart to: {out_file.resolve()}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return True


def visualize_speedup_comparison(
    benchmark_data: List[Dict[str, Any]],
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    show: bool = False,
) -> bool:
    """Plot speedup ratio (Time_NoSym / Time_Sym) achieved by Symmetry Breaking.

    Args:
        benchmark_data: List of benchmark dicts containing 'graph', 'encoding', 'solver', 'symmetry', 'time'.
        title: Plot title.
        save_path: Destination path for saved image.
        show: If True, opens GUI window.
    """
    if not HAS_MATPLOTLIB:
        return False

    if HAS_CNSPLOTS:
        try:
            cns.setup_matplotlib()
        except Exception:
            pass

    import numpy as np

    # Group times by (graph, encoding, solver) -> {True: time_sym, False: time_nosym}
    grouped: Dict[Tuple[str, str, str], Dict[bool, float]] = {}
    for d in benchmark_data:
        g = d["graph"]
        enc = d.get("encoding", "direct")
        solv = d.get("solver", "glucose4")
        sym_raw = d.get("symmetry", True)
        if isinstance(sym_raw, str):
            sym = sym_raw.strip().lower() in ("true", "1", "yes")
        else:
            sym = bool(sym_raw)
        key = (g, enc, solv)
        if key not in grouped:
            grouped[key] = {}
        grouped[key][sym] = float(d["time"])

    # Compute speedup ratio
    speedup_records = []
    for (g, enc, solv), times in grouped.items():
        if True in times and False in times and times[True] > 0:
            ratio = times[False] / times[True]
            speedup_records.append({
                "graph": g,
                "label": f"{enc.upper()}_{solv}",
                "speedup": ratio,
            })

    if not speedup_records:
        print("[!] Not enough symmetric pairs found to compute speedup.")
        return False

    graphs = sorted(list(set(r["graph"] for r in speedup_records)))
    labels = sorted(list(set(r["label"] for r in speedup_records)))

    matrix = {lbl: [0.0] * len(graphs) for lbl in labels}
    for r in speedup_records:
        g_idx = graphs.index(r["graph"])
        lbl = r["label"]
        matrix[lbl][g_idx] = r["speedup"]

    x = np.arange(len(graphs))
    bar_width = 0.8 / max(1, len(labels))

    fig, ax = plt.subplots(figsize=(max(9, len(graphs) * 2), 5.5))
    # Custom color palette: ORDER_glucose4 is explicitly gold/yellow (#f1c40f)
    speedup_color_map = {
        "order_glucose4": "#f1c40f",      # Vang tuoi / Gold Yellow theo yeu cau
        "order_cadical153": "#1b9e77",    # Xanh luc / Teal
        "direct_glucose4": "#2b5c8f",     # Xanh duong dam / Navy Blue
        "direct_cadical153": "#d95f02",   # Cam do / Orange
        "cpsat_cpsat": "#7570b3",         # Tim / Purple
    }
    fallback_colors = ["#2b5c8f", "#d95f02", "#1b9e77", "#7570b3", "#e7298a", "#66a61e"]

    for i, lbl in enumerate(labels):
        offset = (i - len(labels) / 2 + 0.5) * bar_width
        vals = matrix[lbl]
        bar_color = speedup_color_map.get(lbl.lower(), fallback_colors[i % len(fallback_colors)])
        bars = ax.bar(
            x + offset,
            vals,
            width=bar_width,
            label=f"{lbl} Speedup",
            color=bar_color,
            edgecolor="black",
        )
        for bar in bars:
            h = bar.get_height()
            if h > 0:
                ax.annotate(
                    f"{h:.2f}x",
                    xy=(bar.get_x() + bar.get_width() / 2, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )

    ax.axhline(1.0, color="red", linestyle="--", linewidth=1.5, label="Baseline (1.0x - No Gain)")
    ax.set_xticks(x)
    ax.set_xticklabels(graphs, fontsize=10, fontweight="bold")
    ax.set_xlabel("Benchmark Graphs", fontsize=11, fontweight="bold")
    ax.set_ylabel("Speedup Ratio (T_nosym / T_sym)", fontsize=11, fontweight="bold")
    ax.set_title(
        title or "Symmetry Breaking Acceleration Ratio (Speedup >= 1.0x)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.legend(frameon=True, shadow=True)
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)

    plt.tight_layout()

    if save_path:
        out_file = Path(save_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(out_file, dpi=200, bbox_inches="tight")
        print(f"[+] Saved speedup chart to: {out_file.resolve()}")

    if show:
        plt.show()
    else:
        plt.close(fig)

    return True
