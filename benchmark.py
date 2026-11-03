"""Benchmark Suite for Antibandwidth Problem (ABP)"""

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
from src.cp_solver import AntibandwidthCPSolver, HAS_ORTOOLS
from src.visualizer import (
    visualize_benchmark_comparison,
    visualize_speedup_comparison,
    visualize_antibandwidth_labeling,
)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Run comprehensive comparative benchmarks on Antibandwidth Solvers."
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/instance/harwell-boeing_v2",
        help="Directory containing benchmark graph files. Default: data/instance/harwell-boeing_v2",
    )
    parser.add_argument(
        "-i", "--input", "--files",
        nargs="+",
        dest="files",
        default=None,
        help="One or more graph benchmark file paths to evaluate (supports multiple matrices).",
    )
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=["glucose4", "cadical153"],
        help="PySAT solver backends to compare (e.g., glucose4 cadical153). Default: glucose4 cadical153",
    )
    parser.add_argument(
        "--encodings",
        nargs="+",
        default=["direct", "order", "cpsat"],
        choices=["direct", "order", "cpsat"],
        help="Encodings / models to compare (direct, order, cpsat). Default: direct order cpsat",
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
        "--output-md",
        type=str,
        default="benchmark_results.md",
        help="Path to export tabular benchmark results as Markdown table.",
    )
    parser.add_argument(
        "--plot-time",
        type=str,
        default="benchmark_time_comparison.png",
        help="Path to save comparative time plot.",
    )
    parser.add_argument(
        "--plot-clauses",
        type=str,
        default="benchmark_clause_comparison.png",
        help="Path to save comparative clause complexity plot.",
    )
    parser.add_argument(
        "--plot-speedup",
        type=str,
        default="benchmark_speedup_comparison.png",
        help="Path to save symmetry breaking speedup plot.",
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
        graph_files = []
        for p_str in args.files:
            p = Path(p_str)
            if p.is_dir():
                graph_files.extend(discover_graph_files(str(p)))
            elif "*" in p_str or "?" in p_str:
                import glob
                graph_files.extend(Path(g) for g in sorted(glob.glob(p_str)))
            else:
                graph_files.append(p)
    else:
        # Default to diverse curated suite of Harwell-Boeing instances
        default_suite = [
            Path("data/instance/harwell-boeing_v2/jgl009.txt"),
            Path("data/instance/harwell-boeing_v2/jgl011.txt"),
            Path("data/instance/harwell-boeing_v2/can___24.txt"),
            Path("data/instance/harwell-boeing_v2/bcspwr01.txt"),
        ]
        existing_defaults = [p for p in default_suite if p.exists()]
        if existing_defaults:
            graph_files = existing_defaults
        else:
            graph_files = discover_graph_files(args.data_dir)

    if not graph_files:
        print(f"[!] No graph benchmark files found in '{args.data_dir}'.")
        sys.exit(1)

    print("\n" + "=" * 80)
    print("       ANTIBANDWIDTH PROBLEM - COMPREHENSIVE BENCHMARK SUITE")
    print("=" * 80)
    print(f"[*] Found {len(graph_files)} graph file(s): {[f.name for f in graph_files]}")
    print(f"[*] Encodings / Models: {args.encodings}")
    print(f"[*] SAT Solvers:        {args.solvers}")
    print(f"[*] CP-SAT Support:     {'ENABLED' if HAS_ORTOOLS else 'DISABLED (Install ortools)'}")
    print(f"[*] Symmetry Modes:     {'[ON, OFF]' if args.compare_symmetry else '[ON]'}")
    print("=" * 80 + "\n")

    results: List[Dict[str, Any]] = []
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
        density = (2.0 * m) / (n * (n - 1)) if n > 1 else 0.0
        print(f"\n>>> Benchmarking Graph: {g_name} (|V|={n}, |E|={m}, Density={density:.3f})")

        for enc in args.encodings:
            if enc == "cpsat":
                if not HAS_ORTOOLS:
                    print("    Skipping CP-SAT: Google OR-Tools is not installed.")
                    continue
                for sym in sym_modes:
                    sym_label = "Sym" if sym else "NoSym"
                    cfg_name = f"CPSAT_{sym_label}"
                    print(f"    Running config [{cfg_name:24s}] ... ", end="", flush=True)

                    cp_solver = AntibandwidthCPSolver(
                        graph=graph,
                        break_symmetry=sym,
                        verbose=False,
                    )
                    res = cp_solver.solve(method="direct_optimize")

                    total_clauses = sum(item.get("clauses", 0) for item in res["iterations"])
                    k_opt = res["optimal_k"]
                    verified = res["verified"]
                    status = "OK" if verified else "FAIL"

                    print(f"B*(G)={k_opt} | Time={res['total_time']:.4f}s | Constraints={total_clauses:6d} [{status}]")

                    entry = {
                        "graph": g_name,
                        "n": n,
                        "m": m,
                        "density": round(density, 4),
                        "config": cfg_name,
                        "encoding": "cpsat",
                        "solver": "cpsat",
                        "symmetry": sym,
                        "optimal_k": k_opt,
                        "time": res["total_time"],
                        "clauses": total_clauses,
                        "verified": verified,
                    }
                    results.append(entry)

                    if args.visualize_solutions and res["labeling"] and sym:
                        img_path = f"solution_{g_name}_cpsat.png"
                        visualize_antibandwidth_labeling(
                            graph=graph,
                            labeling=res["labeling"],
                            k=k_opt,
                            title=f"Solution for {g_name} (CP-SAT)",
                            save_path=img_path,
                            show=False,
                        )
            else:
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
                            "density": round(density, 4),
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

                        if args.visualize_solutions and res["labeling"] and sym:
                            img_path = f"solution_{g_name}_{enc}_{solv}.png"
                            visualize_antibandwidth_labeling(
                                graph=graph,
                                labeling=res["labeling"],
                                k=k_opt,
                                title=f"Solution for {g_name} ({enc.upper()}_{solv})",
                                save_path=img_path,
                                show=False,
                            )

    # -------------------------------------------------------------
    # Output Summary Table
    # -------------------------------------------------------------
    print("\n" + "=" * 95)
    print("                     BENCHMARK RESULTS SUMMARY")
    print("=" * 95)
    print(f"{'Graph':<15} | {'Config':<25} | {'k*':<4} | {'Time (s)':<10} | {'Clauses':<10} | {'Status'}")
    print("-" * 95)
    for r in results:
        status_str = "PASSED" if r["verified"] else "FAILED"
        print(f"{r['graph']:<15} | {r['config']:<25} | {r['optimal_k']:<4} | {r['time']:<10.4f} | {r['clauses']:<10} | {status_str}")
    print("=" * 95)

    # Export to CSV
    if args.output_csv and results:
        out_csv = Path(args.output_csv)
        keys = list(results[0].keys())
        with open(out_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(results)
        print(f"\n[+] Tabular benchmark CSV exported to: {out_csv.resolve()}")

    # Export to Markdown table
    if args.output_md and results:
        out_md = Path(args.output_md)
        with open(out_md, "w", encoding="utf-8") as f:
            f.write("# Antibandwidth Comprehensive Benchmark Results\n\n")
            f.write("| Graph | Vertices (n) | Edges (m) | Density | Configuration | B*(G) | Time (s) | Clauses/Constr | Status |\n")
            f.write("| :--- | :---: | :---: | :---: | :--- | :---: | :---: | :---: | :---: |\n")
            for r in results:
                st = "PASSED" if r["verified"] else "FAILED"
                f.write(
                    f"| {r['graph']} | {r['n']} | {r['m']} | {r['density']} | {r['config']} | "
                    f"{r['optimal_k']} | {r['time']:.4f} | {r['clauses']} | {st} |\n"
                )
        print(f"[+] Tabular benchmark Markdown exported to: {out_md.resolve()}")

    # Generate comparative plots
    if args.plot_time and results:
        visualize_benchmark_comparison(
            benchmark_data=results,
            metric="time",
            title="Antibandwidth Benchmark: Solving Time Comparison (SAT vs CP-SAT)",
            save_path=args.plot_time,
            show=False,
        )

    if args.plot_clauses and results:
        visualize_benchmark_comparison(
            benchmark_data=results,
            metric="clauses",
            title="Antibandwidth Benchmark: Clause / Constraint Complexity",
            save_path=args.plot_clauses,
            show=False,
        )

    if args.plot_speedup and results and args.compare_symmetry:
        visualize_speedup_comparison(
            benchmark_data=results,
            title="Symmetry Breaking Speedup Ratio (T_nosym / T_sym)",
            save_path=args.plot_speedup,
            show=False,
        )


if __name__ == "__main__":
    run_benchmark()
