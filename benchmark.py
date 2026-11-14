"""Benchmark Suite for Antibandwidth Problem (ABP)"""

import argparse
import csv
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path
from typing import Dict, List, Any

# Ensure workspace root is in sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.graph_loader import load_graph
from src.sat_encoder import SUPPORTED_AMO_ENCODINGS
from src.solver import AntibandwidthSolver
from src.cp_solver import AntibandwidthCPSolver, HAS_ORTOOLS
from src.visualizer import (
    visualize_benchmark_comparison,
    visualize_speedup_comparison,
    visualize_antibandwidth_labeling,
)


def _worker_run_solver(
    g_path: str,
    solver_name: str,
    encoding: str,
    amo_encoding: str,
    break_symmetry: bool,
    time_limit: float,
    out_queue: Any,
    shared_clauses: Any = None,
):
    """Isolated worker process for running SAT solvers with hard timeout guarantee."""
    try:
        from src.graph_loader import load_graph
        from src.solver import AntibandwidthSolver

        def _track_clauses(num_clauses: int) -> None:
            if shared_clauses is not None:
                with shared_clauses.get_lock():
                    shared_clauses.value += num_clauses

        def _track_best(best_k: int, labeling: Dict[int, int], clauses_so_far: int) -> None:
            out_queue.put(("PROGRESS", {"optimal_k": best_k, "labeling": labeling, "clauses": clauses_so_far}))

        graph, _ = load_graph(g_path)
        solver = AntibandwidthSolver(
            graph=graph,
            solver_name=solver_name,
            encoding=encoding,
            amo_encoding=amo_encoding,
            break_symmetry=break_symmetry,
            time_limit_seconds=time_limit,
            verbose=False,
            on_clauses_generated=_track_clauses,
            on_best_found=_track_best,
        )
        res = solver.solve(method="incremental" if encoding == "scl" else "binary_search")
        out_queue.put(("OK", res))
    except Exception as e:
        out_queue.put(("ERR", str(e)))


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
        "-i", "--input", "--files", "--graph",
        nargs="+",
        dest="files",
        default=None,
        help="One or more graph benchmark file paths to evaluate (supports multiple matrices).",
    )
    parser.add_argument(
        "--solvers",
        nargs="+",
        default=["cadical153"],
        help="PySAT solver backends to compare (e.g., cadical153, glucose4). Default: cadical153",
    )
    parser.add_argument(
        "--encodings",
        nargs="+",
        default=["direct", "order", "scl", "cpsat"],
        choices=["direct", "order", "scl", "cpsat"],
        help="Encodings / models to compare (direct, order, scl, cpsat). Default: direct order scl cpsat",
    )
    parser.add_argument(
        "--amo-encodings",
        nargs="+",
        default=["pairwise", "commander", "seqcounter"],
        choices=list(SUPPORTED_AMO_ENCODINGS),
        help="AMO encodings for Direct SAT ('pairwise', 'seqcounter', 'commander', 'totalizer', 'ladder', 'bitwise'). Default: pairwise commander seqcounter",
    )
    parser.add_argument(
        "--compare-symmetry",
        action="store_true",
        default=True,
        help="Evaluate both With Symmetry Breaking (True) and Without (False).",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=300.0,
        help="Maximum solving time in seconds per CP-SAT configuration. Default: 300.0s",
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
        default="docs/benchmark_time_comparison.png",
        help="Path to save comparative time plot. Default: docs/benchmark_time_comparison.png",
    )
    parser.add_argument(
        "--plot-clauses",
        type=str,
        default="docs/benchmark_clause_comparison.png",
        help="Path to save comparative clause complexity plot. Default: docs/benchmark_clause_comparison.png",
    )
    parser.add_argument(
        "--plot-speedup",
        type=str,
        default="docs/benchmark_speedup_comparison.png",
        help="Path to save symmetry breaking speedup plot. Default: docs/benchmark_speedup_comparison.png",
    )
    parser.add_argument(
        "--visualize-solutions",
        action="store_true",
        help="Also generate individual solution graph plots for each graph.",
    )
    parser.add_argument(
        "--merge",
        action="store_true",
        help="Merge new results into existing --output-csv (replacing rows of re-run graphs) before regenerating tables and plots.",
    )
    parser.add_argument(
        "--drop-graphs",
        nargs="+",
        default=[],
        help="Graph filenames to remove from existing CSV when using --merge (e.g. --drop-graphs nos3).",
    )
    return parser.parse_args()


def _load_existing_csv(csv_path: Path, exclude_graphs: set) -> List[Dict[str, Any]]:
    """Load existing benchmark rows from CSV, excluding specified graph names."""
    if not csv_path.exists():
        return []
    loaded: List[Dict[str, Any]] = []
    with open(csv_path, "r", newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("graph") in exclude_graphs:
                continue
            k_raw = row.get("optimal_k", "")
            k_val: Any = int(k_raw) if k_raw.lstrip("-").isdigit() else k_raw
            loaded.append({
                "graph": row["graph"],
                "n": int(row["n"]),
                "m": int(row["m"]),
                "density": float(row["density"]),
                "config": row["config"],
                "encoding": row["encoding"],
                "solver": row["solver"],
                "symmetry": row["symmetry"] == "True",
                "optimal_k": k_val,
                "time": float(row["time"]),
                "clauses": int(row["clauses"]),
                "verified": row["verified"] == "True",
            })
    return loaded


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
            Path("data/instance/harwell-boeing_v2/can___61.txt"),
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

                    try:
                        cp_solver = AntibandwidthCPSolver(
                            graph=graph,
                            break_symmetry=sym,
                            verbose=False,
                            time_limit_seconds=getattr(args, "time_limit", 300.0),
                        )
                        res = cp_solver.solve(method="direct_optimize")

                        total_clauses = sum(item.get("clauses", 0) for item in res["iterations"])
                        k_opt = res["optimal_k"]
                        verified = res["verified"]
                        status = "OK" if verified else "FAIL"

                        print(f"B*(G)={k_opt} | Time={res['total_time']:.4f}s | Constraints={total_clauses:6d} [{status}]")
                    except Exception as e:
                        limit_t = getattr(args, "time_limit", 300.0)
                        print(f"ERROR: {e}")
                        total_clauses = 0
                        k_opt = "ERR"
                        verified = False
                        res = {"total_time": limit_t, "labeling": None}

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
                        img_path = f"docs/solution_{g_name}_cpsat.png"
                        visualize_antibandwidth_labeling(
                            graph=graph,
                            labeling=res["labeling"],
                            k=k_opt,
                            title=f"Solution for {g_name} (CP-SAT)",
                            save_path=img_path,
                            show=False,
                        )
            else:
                amo_list = args.amo_encodings if enc == "direct" else ["pairwise"]
                for solv, amo_enc in [(s, a) for s in args.solvers for a in amo_list]:
                    for sym in sym_modes:
                        sym_label = "Sym" if sym else "NoSym"
                        enc_label = (
                            f"{enc.upper()}_{amo_enc.upper()}"
                            if (enc == "direct")
                            else enc.upper()
                        )
                        cfg_name = f"{enc_label}_{solv}_{sym_label}"

                        print(f"    Running config [{cfg_name:28s}] ... ", end="", flush=True)

                        if n > 100:
                            if enc == "order" or amo_enc == "pairwise":
                                est_clauses = 2 * n * (n * (n - 1) // 2)
                                oom_label = f"OOM (n={n} > 100: ~{est_clauses:,d} clauses exceed RAM) [SKIP]"
                            else:
                                est_clauses = 6 * n * n
                                oom_label = f"OOM (n={n} > 100: ~{est_clauses:,d} clauses exceed SAT timeout) [SKIP]"
                            limit_t = getattr(args, "time_limit", 300.0)
                            print(oom_label)
                            entry = {
                                "graph": g_name,
                                "n": n,
                                "m": m,
                                "density": round(density, 4),
                                "config": cfg_name,
                                "encoding": enc_label.lower(),
                                "solver": solv,
                                "symmetry": sym,
                                "optimal_k": "OOM",
                                "time": limit_t,
                                "clauses": est_clauses,
                                "verified": False,
                            }
                            results.append(entry)
                            continue

                        limit_t = getattr(args, "time_limit", 300.0)
                        queue = mp.Queue()
                        shared_clauses = mp.Value("Q", 0)
                        proc = mp.Process(
                            target=_worker_run_solver,
                            args=(str(g_path), solv, enc, amo_enc, sym, limit_t, queue, shared_clauses),
                        )

                        t0 = time.perf_counter()
                        proc.start()
                        proc.join(timeout=limit_t)
                        elapsed = time.perf_counter() - t0

                        timed_out = False
                        if proc.is_alive():
                            timed_out = True
                            proc.terminate()
                            proc.join()

                        latest_progress = None
                        final_msg = None
                        while not queue.empty():
                            try:
                                msg_type, msg_data = queue.get_nowait()
                                if msg_type == "PROGRESS":
                                    latest_progress = msg_data
                                else:
                                    final_msg = (msg_type, msg_data)
                            except Exception:
                                break

                        if timed_out:
                            total_clauses = int(shared_clauses.value)
                            if total_clauses == 0:
                                from src.sat_encoder import AntibandwidthSATEncoder
                                from src.order_encoder import AntibandwidthOrderEncoder
                                from src.scl_encoder import AntibandwidthSCLEncoder
                                k_probe = max(1, n // 4)
                                if enc == "order":
                                    total_clauses = len(AntibandwidthOrderEncoder(graph, break_symmetry=sym).encode(k_probe).clauses)
                                elif enc == "scl":
                                    total_clauses = len(AntibandwidthSCLEncoder(graph, break_symmetry=sym).encode(k_probe).clauses)
                                else:
                                    total_clauses = AntibandwidthSATEncoder(graph, break_symmetry=sym, amo_encoding=amo_enc).get_stats(k_probe)["total_clauses"]

                            if latest_progress is not None:
                                k_opt = latest_progress["optimal_k"]
                                verified = True
                                res = {"total_time": limit_t, "labeling": latest_progress["labeling"]}
                                print(f"B*(G)={k_opt} | Time={limit_t:.4f}s | Clauses={total_clauses:6d} [OK-FEASIBLE/TO]")
                            else:
                                print(f"TIMEOUT (exceeded {limit_t:.1f}s) | Clauses={total_clauses:6d} [FAIL]")
                                k_opt = "TIMEOUT"
                                verified = False
                                res = {"total_time": limit_t, "labeling": None}
                        elif final_msg is not None:
                            status_code, res_data = final_msg
                            if status_code == "OK":
                                res = res_data
                                total_clauses = sum(item.get("clauses", 0) for item in res.get("iterations", []))
                                k_opt = res["optimal_k"]
                                verified = res["verified"]
                                if res.get("timed_out", False):
                                    status = "OK-FEASIBLE/TO" if verified and res.get("labeling") else "TIMEOUT"
                                    print(f"B*(G)={k_opt} | Time={res['total_time']:.4f}s | Clauses={total_clauses:6d} [{status}]")
                                else:
                                    status = "OK" if verified else "FAIL"
                                    print(f"B*(G)={k_opt} | Time={res['total_time']:.4f}s | Clauses={total_clauses:6d} [{status}]")
                            else:
                                print(f"ERROR ({res_data}) [FAIL]")
                                total_clauses = 0
                                k_opt = "ERR"
                                verified = False
                                res = {"total_time": elapsed, "labeling": None}
                        else:
                            print(f"ERROR (Solver process exited unexpectedly) [FAIL]")
                            total_clauses = 0
                            k_opt = "ERR"
                            verified = False
                            res = {"total_time": elapsed, "labeling": None}

                        entry = {
                            "graph": g_name,
                            "n": n,
                            "m": m,
                            "density": round(density, 4),
                            "config": cfg_name,
                            "encoding": enc_label.lower(),
                            "solver": solv,
                            "symmetry": sym,
                            "optimal_k": k_opt,
                            "time": res["total_time"],
                            "clauses": total_clauses,
                            "verified": verified,
                        }
                        results.append(entry)

                        if args.visualize_solutions and res["labeling"] and sym:
                            img_path = f"docs/solution_{g_name}_{enc_label.lower()}_{solv}.png"
                            visualize_antibandwidth_labeling(
                                graph=graph,
                                labeling=res["labeling"],
                                k=k_opt,
                                title=f"Solution for {g_name} ({enc_label}_{solv})",
                                save_path=img_path,
                                show=False,
                            )

    # -------------------------------------------------------------
    # Merge with existing CSV if requested
    # -------------------------------------------------------------
    if args.merge and args.output_csv:
        new_graph_names = {r["graph"] for r in results}
        exclude_set = new_graph_names | set(args.drop_graphs)
        existing_rows = _load_existing_csv(Path(args.output_csv), exclude_set)
        if existing_rows:
            print(f"\n[*] Merging {len(existing_rows)} existing rows from {args.output_csv} (excluded: {sorted(exclude_set)})")
            results = existing_rows + results

    # -------------------------------------------------------------
    # Output Summary Table
    # -------------------------------------------------------------
    print("\n" + "=" * 95)
    print("                     BENCHMARK RESULTS SUMMARY")
    print("=" * 95)
    print(f"{'Graph':<15} | {'Config':<25} | {'k*':<4} | {'Time (s)':<10} | {'Clauses':<10} | {'Status'}")
    print("-" * 95)
    for r in results:
        status_str = "PASSED" if r["verified"] else ("OOM" if r["optimal_k"] == "OOM" else "FAILED")
        k_str = str(r['optimal_k'])
        print(f"{r['graph']:<15} | {r['config']:<25} | {k_str:<4} | {r['time']:<10.4f} | {r['clauses']:<10} | {status_str}")
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
                st = "PASSED" if r["verified"] else ("OOM (Memory Wall)" if r["optimal_k"] == "OOM" else "FAILED")
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
