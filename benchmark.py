"""Benchmark Suite for Antibandwidth Problem (ABP).

Executes experimental evaluations across multiple graphs and configurations:
1. Direct Encoding vs. Order Encoding
2. With Symmetry Breaking vs. Without Symmetry Breaking
3. Solver engine comparison (e.g., glucose4 vs. cadical153)

Outputs tabular statistics (CSV/Markdown) and generates comparative visualization plots.

Usage:
    python benchmark.py
    python benchmark.py --data-dir data --output-csv results.csv --plot benchmark_chart.png
    python benchmark.py --compare-encodings --compare-symmetry
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.graph_loader import load_graph
from src.solver import AntibandwidthSolver
from src.visualizer import visualize_benchmark_comparison, visualize_antibandwidth_labeling


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run comparative benchmarks on Antibandwidth SAT Solvers."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/instance/harwell-boeing_v2",
        help="Directory containing benchmark graph files. Default: data/instance/harwell-boeing_v2",
    )
    parser.add_argument(
        "--files",
        nargs="+",
        default=None,
        help="Explicit list of graph file paths to evaluate.",
    )
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=["glucose4"],
        help="PySAT solver backends to compare (e.g., glucose4 cadical153).",
    )
    parser.add_argument(
        "--encodings",
        nargs="+",
        default=["direct", "order"],
        choices=["direct", "order"],
        help="Encodings to compare (direct, order). Default: direct order",
    )
    parser.add_argument(
        "--compare-symmetry",
        action="store_true",
        default=True,
        help="Evaluate both With Symmetry Breaking (True) and Without (False).",
    )
    parser.add_argument(
        "--output-csv",
        type=str,
        default="benchmark_results.csv",
        help="Path to export tabular benchmark results as CSV.",
    )
    parser.add_argument(
        "--plot",
        type=str,
        default="benchmark_comparison.png",
        help="Path to save comparative visualization plot of the benchmarks.",
    )
    parser.add_argument(
        "--visualize-solutions",
        action="store_true",
        help="Also generate individual solution graph plots for each graph.",
    )
    return parser.parse_args()


def discover_graph_files(data_dir: str, recursive: bool = True) -> List[Path]:
    """Find all supported graph files in the directory (recursively if requested)."""
    dir_path = Path(data_dir)
    if not dir_path.exists():
        return []

    supported_exts = {".mtx", ".rb", ".edges", ".txt", ""}
    ignored_names = {"readme.md", "license", ".gitignore", "readme.txt"}

    files = []
    iterator = dir_path.rglob("*") if recursive else dir_path.iterdir()
    for f in sorted(iterator):
        if f.is_file():
            if f.name.lower() in ignored_names:
                continue
            if f.suffix.lower() in supported_exts or f.suffix == "":
                files.append(f)
    return files


def run_benchmark():
    args = parse_args()

    # Determine files to run
    if args.files:
        graph_files = [Path(p) for p in args.files]
    else:
        graph_files = discover_graph_files(args.data_dir)

    if not graph_files:
        print(f"[!] No graph benchmark files found in '{args.data_dir}'.")
        sys.exit(1)

    print("\n" + "=" * 75)
    print("       ANTIBANDWIDTH PROBLEM - BENCHMARK SUITE")
    print("=" * 75)
    print(f"[*] Found {len(graph_files)} graph file(s): {[f.name for f in graph_files]}")
    print(f"[*] Encodings: {args.encodings}")
    print(f"[*] Solvers:   {args.solvers}")
    print(f"[*] Symmetry:  {'[ON, OFF]' if args.compare_symmetry else '[ON]'}")
    print("=" * 75 + "\n")

    results: List[Dict[str, Any]] = []

    # Symmetry configurations to test
    sym_modes = [True, False] if args.compare_symmetry else [True]

    for g_path in graph_files:
        try:
            graph, info = load_graph(g_path)
        except Exception as e:
            print(f"[!] Skipping {g_path.name}: failed to load ({e})")
            continue

        g_name = info["filename"]
        n = info["num_vertices"]
        m = info["num_edges"]
        print(f"\n>>> Benchmarking Graph: {g_name} (|V|={n}, |E|={m})")

        for enc in args.encodings:
            for solv in args.solvers:
                for sym in sym_modes:
                    sym_label = "Sym" if sym else "NoSym"
                    cfg_name = f"{enc.upper()}_{solv}_{sym_label}"

                    print(f"    Running config [{cfg_name:24s}] ... ", end="", flush=True)

                    solver = AntibandwidthSolver(
                        graph=graph,
                        solver_name=solv,
                        encoding=enc,
                        break_symmetry=sym,
                        verbose=False,
                    )

                    t0 = time.perf_counter()
                    res = solver.solve(method="binary_search")
                    elapsed = time.perf_counter() - t0

                    total_clauses = sum(item["clauses"] for item in res["iterations"])
                    k_opt = res["optimal_k"]
                    verified = res["verified"]

                    status = "OK" if verified else "FAIL"
                    print(f"B*(G)={k_opt} | Time={res['total_time']:.4f}s | Clauses={total_clauses:6d} [{status}]")

                    entry = {
                        "graph": g_name,
                        "n": n,
                        "m": m,
                        "config": cfg_name,
                        "encoding": enc,
                        "solver": solv,
                        "symmetry": sym,
                        "optimal_k": k_opt,
                        "time": res["total_time"],
                        "clauses": total_clauses,
                        "verified": verified,
                    }
                    results.append(entry)

                    # Optional: visualize solution graph
                    if args.visualize_solutions and res["labeling"] and sym:
                        img_path = f"solution_{g_name}_{enc}.png"
                        visualize_antibandwidth_labeling(
                            graph=graph,
                            labeling=res["labeling"],
                            k=k_opt,
                            title=f"Solution for {g_name} ({enc.upper()})",
                            save_path=img_path,
                            show=False,
                        )

    # -------------------------------------------------------------
    # Output Summary Table
    # -------------------------------------------------------------
    print("\n" + "=" * 90)
    print("                     BENCHMARK RESULTS SUMMARY")
    print("=" * 90)
    print(f"{'Graph':<15} | {'Config':<25} | {'k*':<4} | {'Time (s)':<10} | {'Clauses':<10} | {'Status'}")
    print("-" * 90)
    for r in results:
        status_str = "PASSED" if r["verified"] else "FAILED"
        print(f"{r['graph']:<15} | {r['config']:<25} | {r['optimal_k']:<4} | {r['time']:<10.4f} | {r['clauses']:<10} | {status_str}")
    print("=" * 90)

    # Export to CSV
    if args.output_csv and results:
        out_csv = Path(args.output_csv)
        keys = list(results[0].keys())
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[+] Tabular benchmark exported to: {out_csv.resolve()}")

    # Generate comparative plot
    if args.plot and results:
        visualize_benchmark_comparison(
            benchmark_data=results,
            metric="time",
            title="Antibandwidth Benchmark: Solving Time Comparison",
            save_path=args.plot,
            show=False,
        )


if __name__ == "__main__":
    run_benchmark()
