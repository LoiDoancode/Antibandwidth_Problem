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


def _is_record_oom(d: Dict[str, Any]) -> bool:
    """Helper to detect whether a benchmark entry encountered Out-Of-Memory (OOM)."""
    opt_k = str(d.get("optimal_k", "")).strip().upper()
    status = str(d.get("status", "")).strip().upper()
    if "OOM" in opt_k or "OOM" in status:
        return True
    if d.get("verified") is False and (opt_k in ("ERR", "NONE", "") or "MEMORY" in status):
        return True
    return False


def visualize_benchmark_comparison(
    benchmark_data: List[Dict[str, Any]],
    metric: str = "time",
    title: Optional[str] = None,
    save_path: Optional[str] = None,
    show: bool = False,
    log_scale: bool = True,
) -> bool:
    """Plot comparative benchmark metrics across different algorithms / configurations.

    Args:
        benchmark_data: List of dicts, each with keys:
            ['graph', 'config', 'time', 'clauses', 'optimal_k', ...]
        metric: 'time' (Execution seconds) or 'clauses' (Number of CNF clauses).
        title: Optional custom plot title.
        save_path: Path to save the image (e.g., 'benchmark_results.png').
        show: If True, opens GUI window.
        log_scale: If True (default), uses logarithmic scale on the y-axis to
            prevent huge instances (like nos3) from squishing smaller test instances.

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
    import matplotlib.patches as mpatches
    import matplotlib.ticker as ticker

    # Group by graph and configuration (ordered by vertex count n descending: largest to smallest)
    graph_to_n = {d["graph"]: int(d.get("n", 0)) for d in benchmark_data}
    graphs = sorted(list(set(d["graph"] for d in benchmark_data)), key=lambda g: (-graph_to_n.get(g, 0), g))
    configs = sorted(list(set(d["config"] for d in benchmark_data)))

    data_matrix = {cfg: [0.0] * len(graphs) for cfg in configs}
    oom_matrix = {cfg: [False] * len(graphs) for cfg in configs}

    for d in benchmark_data:
        g_idx = graphs.index(d["graph"])
        cfg = d["config"]
        oom = _is_record_oom(d)
        oom_matrix[cfg][g_idx] = oom
        if oom:
            data_matrix[cfg][g_idx] = 0.0
        else:
            raw_val = d["time"] if metric == "time" else d.get("clauses", 0)
            data_matrix[cfg][g_idx] = float(raw_val)

    x = np.arange(len(graphs))
    bar_width = 0.8 / max(1, len(configs))

    fig, ax = plt.subplots(figsize=(max(11, len(graphs) * 2.2), 6.5))

    colors = [
        "#1f77b4", "#aec7e8", "#ff7f0e", "#ffbb78",
        "#2ca02c", "#98df8a", "#d62728", "#ff9896",
        "#9467bd", "#c5b0d5", "#8c564b", "#c49c94",
        "#e377c2", "#f7b6d2", "#7f7f7f", "#c7c7c7",
        "#bcbd22", "#dbdb8d", "#17becf", "#9edae5"
    ]

    # Configure Y-axis scaling (Logarithmic vs Linear)
    all_positive = [
        val for cfg in configs for val, oom in zip(data_matrix[cfg], oom_matrix[cfg])
        if not oom and val > 0
    ]

    ax.set_axisbelow(True)
    use_log = log_scale and len(all_positive) > 0
    if use_log:
        min_pos = min(all_positive)
        max_pos = max(all_positive)
        ax.set_yscale("log")
        if metric == "time":
            bottom_val = min(0.001, 10.0 ** float(np.floor(np.log10(min_pos))))
            top_val = max(1.0, 10.0 ** float(np.ceil(np.log10(max_pos)))) * 3.0
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{y:g}s"))
        else:
            bottom_val = min(10.0, 10.0 ** float(np.floor(np.log10(max(1.0, min_pos)))))
            top_val = max(100.0, 10.0 ** float(np.ceil(np.log10(max_pos)))) * 3.0
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda y, _: f"{int(y):,}"))

        ax.set_ylim(bottom_val, top_val)
    else:
        bottom_val = 0.0
        max_val = max(all_positive) if all_positive else 1.0
        ax.set_ylim(0, max_val * 1.35)

    all_bars_info = []
    legend_handles = []

    for i, cfg in enumerate(configs):
        offset = (i - len(configs) / 2 + 0.5) * bar_width
        vals = data_matrix[cfg]
        ooms = oom_matrix[cfg]
        bar_color = colors[i % len(colors)]
        legend_handles.append(mpatches.Patch(facecolor=bar_color, edgecolor="black", label=cfg))

        if use_log:
            heights = [(v - bottom_val) if (not oom and v > bottom_val) else 0.0 for v, oom in zip(vals, ooms)]
            bars = ax.bar(
                x + offset,
                heights,
                bottom=bottom_val,
                width=bar_width,
                color=bar_color,
                edgecolor="black",
                linewidth=0.5,
                alpha=1.0,
            )
        else:
            heights = [0.0 if oom else v for v, oom in zip(vals, ooms)]
            bars = ax.bar(
                x + offset,
                heights,
                width=bar_width,
                color=bar_color,
                edgecolor="black",
                linewidth=0.5,
                alpha=1.0,
            )

        for bar, oom in zip(bars, ooms):
            if oom:
                bar.set_visible(False)

        all_bars_info.append((i, cfg, bars, vals, ooms, x + offset))

    stagger_offsets_log = [1.15, 1.35, 1.6, 1.9]
    stagger_offsets_linear = [8, 28, 48, 68] if len(configs) > 4 else [8, 24]

    for i, cfg, bars, vals, ooms, x_coords in all_bars_info:
        for bar, val, is_oom, bx in zip(bars, vals, ooms, x_coords):
            if is_oom:
                oom_y = bottom_val * 1.5 if (use_log and metric == "time") else (bottom_val * 1.8 if use_log else 0.02 * ax.get_ylim()[1])
                ax.text(
                    bx,
                    oom_y,
                    "OOM",
                    ha="center",
                    va="bottom",
                    fontsize=7,
                    fontweight="bold",
                    color="#d62728",
                    rotation=90,
                )
            elif val > 0:
                fmt = f"{val:.3f}s" if metric == "time" else f"{int(val):,}"
                if use_log:
                    stag_factor = stagger_offsets_log[i % len(stagger_offsets_log)]
                    label_y = val * stag_factor
                    ax.plot([bx, bx], [val, label_y], color="#666666", linestyle=":", linewidth=0.7)
                    ax.text(
                        bx,
                        label_y,
                        fmt,
                        ha="center",
                        va="bottom",
                        fontsize=6.5,
                        fontweight="bold",
                        rotation=90,
                    )
                else:
                    stagger_level = i % len(stagger_offsets_linear)
                    y_offset = stagger_offsets_linear[stagger_level] if len(configs) > 3 else 5
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
                        xy=(bx, val),
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
    ax.set_xlabel("Benchmark Graphs (sorted by size |V|: largest to smallest)", fontsize=11, fontweight="bold")

    scale_suffix = " (Logarithmic Scale)" if use_log else ""
    if metric == "time":
        ax.set_ylabel(f"Solving Time in seconds{scale_suffix}", fontsize=11, fontweight="bold")
        default_title = "Antibandwidth Benchmark: Solving Time Comparison (SAT vs CP-SAT)"
    else:
        ax.set_ylabel(f"Number of CNF Clauses / Constraints{scale_suffix}", fontsize=11, fontweight="bold")
        default_title = "Antibandwidth Benchmark: Clause / Constraint Complexity"

    ax.set_title(title or default_title, fontsize=13, fontweight="bold", pad=15)
    ax.legend(handles=legend_handles, frameon=True, shadow=True, bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8)
    ax.grid(True, which="major", axis="y", linestyle="--", alpha=0.5)

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
    import matplotlib.patches as mpatches

    # Group times and OOM flags by (graph, encoding, solver) -> {True: (time, oom), False: (time, oom)}
    grouped: Dict[Tuple[str, str, str], Dict[bool, Tuple[float, bool]]] = {}
    for d in benchmark_data:
        g = d["graph"]
        enc = d.get("encoding", "direct")
        solv = d.get("solver", "glucose4")
        sym_raw = d.get("symmetry", True)
        if isinstance(sym_raw, str):
            sym = sym_raw.strip().lower() in ("true", "1", "yes")
        else:
            sym = bool(sym_raw)
        oom = _is_record_oom(d)
        key = (g, enc, solv)
        if key not in grouped:
            grouped[key] = {}
        grouped[key][sym] = (float(d["time"]), oom)

    # Compute speedup ratio
    speedup_records = []
    for (g, enc, solv), times in grouped.items():
        if True in times and False in times:
            t_sym, oom_sym = times[True]
            t_nosym, oom_nosym = times[False]
            has_oom = oom_sym or oom_nosym
            ratio = (t_nosym / t_sym) if (not has_oom and t_sym > 0) else 0.0
            speedup_records.append({
                "graph": g,
                "label": f"{enc.upper()}_{solv}",
                "speedup": ratio,
                "is_oom": has_oom,
            })

    if not speedup_records:
        print("[!] Not enough symmetric pairs found to compute speedup.")
        return False

    graph_to_n = {d["graph"]: int(d.get("n", 0)) for d in benchmark_data}
    graphs = sorted(list(set(r["graph"] for r in speedup_records)), key=lambda g: (-graph_to_n.get(g, 0), g))
    labels = sorted(list(set(r["label"] for r in speedup_records)))

    matrix_val = {lbl: [0.0] * len(graphs) for lbl in labels}
    matrix_oom = {lbl: [False] * len(graphs) for lbl in labels}
    for r in speedup_records:
        g_idx = graphs.index(r["graph"])
        lbl = r["label"]
        matrix_val[lbl][g_idx] = r["speedup"]
        matrix_oom[lbl][g_idx] = r["is_oom"]

    x = np.arange(len(graphs))
    bar_width = 0.8 / max(1, len(labels))

    fig, ax = plt.subplots(figsize=(max(9, len(graphs) * 2), 5.5))
    # Custom color palette: ORDER_glucose4 is explicitly gold/yellow (#f1c40f)
    speedup_color_map = {
        "direct_pairwise_glucose4": "#2b5c8f",
        "direct_pairwise_cadical153": "#d95f02",
        "direct_commander_glucose4": "#27ae60",
        "direct_commander_cadical153": "#2ecc71",
        "direct_seqcounter_glucose4": "#e67e22",
        "direct_seqcounter_cadical153": "#f39c12",
        "order_glucose4": "#f1c40f",      # Vang tuoi / Gold Yellow
        "order_cadical153": "#1b9e77",    # Xanh luc / Teal
        "direct_glucose4": "#2b5c8f",     # Xanh duong dam / Navy Blue
        "direct_cadical153": "#d95f02",   # Cam do / Orange
        "cpsat_cpsat": "#7570b3",         # Tim / Purple
    }
    fallback_colors = ["#2b5c8f", "#d95f02", "#1b9e77", "#7570b3", "#e7298a", "#66a61e"]

    legend_handles = [
        plt.Line2D([0], [0], color="red", linestyle="--", linewidth=1.5, label="Baseline (1.0x - No Gain)")
    ]

    for i, lbl in enumerate(labels):
        offset = (i - len(labels) / 2 + 0.5) * bar_width
        vals = matrix_val[lbl]
        ooms = matrix_oom[lbl]
        bar_color = speedup_color_map.get(lbl.lower(), fallback_colors[i % len(fallback_colors)])
        legend_handles.append(mpatches.Patch(facecolor=bar_color, edgecolor="black", label=f"{lbl} Speedup"))

        heights = [0.0 if oom else v for v, oom in zip(vals, ooms)]
        bars = ax.bar(
            x + offset,
            heights,
            width=bar_width,
            color=bar_color,
            edgecolor="black",
        )
        for bar, h, oom, bx in zip(bars, vals, ooms, x + offset):
            if oom:
                bar.set_visible(False)
                ax.text(
                    bx,
                    0.05,
                    "OOM",
                    ha="center",
                    va="bottom",
                    fontsize=7.5,
                    fontweight="bold",
                    color="#d62728",
                    rotation=90,
                )
            elif h > 0:
                ax.annotate(
                    f"{h:.2f}x",
                    xy=(bx, h),
                    xytext=(0, 3),
                    textcoords="offset points",
                    ha="center",
                    va="bottom",
                    fontsize=8,
                    fontweight="bold",
                )

    ax.axhline(1.0, color="red", linestyle="--", linewidth=1.5)
    ax.set_xticks(x)
    ax.set_xticklabels(graphs, fontsize=10, fontweight="bold")
    ax.set_xlabel("Benchmark Graphs (sorted by size |V|: largest to smallest)", fontsize=11, fontweight="bold")
    ax.set_ylabel("Speedup Ratio (T_nosym / T_sym)", fontsize=11, fontweight="bold")
    ax.set_title(
        title or "Symmetry Breaking Acceleration Ratio (Speedup >= 1.0x)",
        fontsize=13,
        fontweight="bold",
        pad=15,
    )
    ax.legend(handles=legend_handles, frameon=True, shadow=True, bbox_to_anchor=(1.02, 1), loc="upper left", fontsize=8.5)
    ax.grid(True, axis="y", linestyle="--", alpha=0.6)

    max_val = max(max(v) for v in matrix_val.values()) if matrix_val else 1.0
    ax.set_ylim(0, max_val * 1.18)

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
