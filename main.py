"""Main entry point for the Antibandwidth Problem (ABP) Solver Framework.

Usage:
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --solver cadical153
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --encoding order
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --encoding cpsat
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --visualize docs/solution_jgl009.png
    python main.py --input data/instance/harwell-boeing_v2/jgl009.txt --check-k 1
"""

import argparse
import json
import sys
from pathlib import Path

# Add workspace directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.graph_loader import load_graph, resolve_graph_path
from src.sat_encoder import AntibandwidthSATEncoder
from src.order_encoder import AntibandwidthOrderEncoder
from src.solver import AntibandwidthSolver
from src.cp_solver import AntibandwidthCPSolver, HAS_ORTOOLS
from src.visualizer import visualize_antibandwidth_labeling, visualize_benchmark_comparison


def print_banner():
    banner = r"""
======================================================================
       ANTIBANDWIDTH PROBLEM (ABP) - SAT & CP SOLVER FRAMEWORK
======================================================================
"""
    print(banner)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Solve Antibandwidth Problem (ABP) using SAT solvers and CP-SAT."
    )
    parser.add_argument(
        "-i", "--input",
        nargs="+",
        default=["data/instance/harwell-boeing_v2/can___24.txt"],
        help="One or more paths to graph benchmark files, directories, or glob patterns.",
    )
    parser.add_argument(
        "-k", "--check-k",
        type=int,
        default=None,
        help="Check satisfiability for a single target k instead of running full optimization.",
    )
    parser.add_argument(
        "--solver",
        type=str,
        default="glucose4",
        help="Solver backend: PySAT solvers ('glucose4', 'cadical153', 'minisat22') or 'cpsat'. Default: glucose4",
    )
    parser.add_argument(
        "--encoding",
        type=str,
        choices=["direct", "order", "cpsat"],
        default="direct",
        help="Encoding / formulation: 'direct' (Pairwise), 'order' (Order Encoding), or 'cpsat' (Google OR-Tools CP-SAT). Default: direct",
    )
    parser.add_argument(
        "--external-solver",
        type=str,
        default=None,
        help="Command / path to external SAT solver binary (e.g. 'kissat', 'cadical').",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["binary_search", "linear_search", "direct_optimize"],
        default="binary_search",
        help="Search strategy for optimal k. Default: binary_search",
    )
    parser.add_argument(
        "--no-symmetry-breaking",
        action="store_true",
        help="Disable symmetry breaking constraints.",
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default=None,
        help="Optional path to save solution labeling (JSON format).",
    )
    parser.add_argument(
        "--export-dimacs",
        type=str,
        default=None,
        help="Export CNF formula for the target k (specified by --check-k) to a DIMACS file.",
    )
    parser.add_argument(
        "--time-limit",
        type=float,
        default=100.0,
        help="Time limit in seconds for CP-SAT solver. Default: 100.0s",
    )
    parser.add_argument(
        "--visualize",
        type=str,
        nargs="?",
        const="docs/solution.png",
        default=None,
        help="Path to save graphical visualization of the solution (e.g., --visualize docs/solution.png).",
    )
    parser.add_argument(
        "--show-plot",
        action="store_true",
        help="Display the matplotlib interactive GUI plot window.",
    )
    return parser.parse_args()


def main():
    print_banner()
    args = parse_args()

    # Resolve input path(s) - supports single file, multiple files, directories, or globs
    input_list = args.input if isinstance(args.input, list) else [args.input]
    resolved_paths = []
    for item in input_list:
        p = Path(item)
        if p.is_dir():
            resolved_paths.extend(sorted(p.glob("*.txt")))
            resolved_paths.extend(sorted(p.glob("*.mtx")))
        elif "*" in item or "?" in item:
            import glob
            resolved_paths.extend(Path(m) for m in sorted(glob.glob(item)))
        else:
            resolved = resolve_graph_path(p)
            if resolved.exists():
                resolved_paths.append(resolved)
            else:
                print(f"[Warning] Graph file not found: {item}")

    unique_paths = []
    for p in resolved_paths:
        if p not in unique_paths:
            unique_paths.append(p)

    if not unique_paths:
        print(f"[Error] No valid graph benchmark files found.")
        sys.exit(1)

    break_sym = not args.no_symmetry_breaking
    is_cpsat = (args.encoding == "cpsat" or args.solver == "cpsat")

    if is_cpsat and not HAS_ORTOOLS:
        print("[Error] Google OR-Tools is not installed. Run: pip install ortools")
        sys.exit(1)

    # If multiple graphs are passed: Batch multi-graph mode
    if len(unique_paths) > 1:
        print(f"[*] Multi-Matrix Mode: processing {len(unique_paths)} matrices with encoding={args.encoding.upper()}, solver={args.solver}...")
        batch_results = []

        for p in unique_paths:
            try:
                g, inf = load_graph(p)
            except Exception as e:
                print(f"[!] Skipping {p.name}: load error ({e})")
                continue

            print(f"    --> Solving {inf['filename']:15s} (|V|={inf['num_vertices']:3d}, |E|={inf['num_edges']:4d}, D={inf['density']:.4f}) ... ", end="", flush=True)

            if is_cpsat:
                solver_inst = AntibandwidthCPSolver(
                    g,
                    break_symmetry=break_sym,
                    time_limit_seconds=getattr(args, "time_limit", 100.0),
                    verbose=False,
                )
                mth = "direct_optimize" if args.method == "direct_optimize" else "binary_search"
                res = solver_inst.solve(method=mth)
            else:
                solver_inst = AntibandwidthSolver(
                    g,
                    solver_name=args.solver,
                    encoding=args.encoding,
                    break_symmetry=break_sym,
                    external_solver=args.external_solver,
                    verbose=False,
                )
                res = solver_inst.solve(method=args.method)

            n_cls = sum(it.get("clauses", 0) for it in res.get("iterations", []))
            st = "PASSED" if res.get("verified", False) else "FAILED"
            print(f"B*(G)={res['optimal_k']:2d} | Time={res['total_time']:.4f}s | Clauses={n_cls} [{st}]")

            batch_results.append({
                "graph": inf["filename"],
                "n": inf["num_vertices"],
                "m": inf["num_edges"],
                "density": inf["density"],
                "config": f"{args.encoding.upper()}_{args.solver}",
                "optimal_k": res["optimal_k"],
                "time": res["total_time"],
                "clauses": n_cls,
                "verified": res.get("verified", False),
            })

        print("\n" + "=" * 95)
        print("                        MULTI-GRAPH COMPARATIVE RESULTS SUMMARY")
        print("=" * 95)
        print(f"{'Graph':16s} | {'|V|':4s} | {'|E|':5s} | {'Density':7s} | {'Config':18s} | {'B*(G)':5s} | {'Time (s)':10s} | {'Clauses':10s} | {'Status':6s}")
        print("-" * 95)
        for r in batch_results:
            st = "PASSED" if r["verified"] else "FAILED"
            print(f"{r['graph']:16s} | {r['n']:4d} | {r['m']:5d} | {r['density']:.4f}  | {r['config']:18s} | {r['optimal_k']:5d} | {r['time']:10.4f} | {r['clauses']:10d} | {st:6s}")
        print("=" * 95 + "\n")

        if args.visualize:
            visualize_benchmark_comparison(
                benchmark_data=batch_results,
                metric="time",
                title=f"Multi-Matrix Solving Time Comparison ({args.encoding.upper()} - {args.solver})",
                save_path=args.visualize,
                show=args.show_plot,
            )
        return

    # Single graph mode
    input_path = unique_paths[0]
    print(f"[*] Loading graph from: {input_path} ...")
    try:
        graph, info = load_graph(input_path)
    except Exception as e:
        print(f"[Error] Failed to load graph: {e}")
        sys.exit(1)

    print(f"[*] Graph Summary:")
    print(f"    - Name:         {info['filename']}")
    print(f"    - Vertices |V|: {info['num_vertices']}")
    print(f"    - Edges |E|:    {info['num_edges']}")
    print(f"    - Density:      {info['density']}")
    print(f"    - Degree range: [{info['min_degree']}, {info['max_degree']}]")
    print(f"    - Encoding:     {args.encoding.upper()}")

    # Mode 1: Check single k or export DIMACS
    if args.check_k is not None:
        target_k = args.check_k
        print(f"\n[*] Mode: Single k Check (Target k = {target_k})")

        if args.export_dimacs:
            if is_cpsat:
                print("[Error] Cannot export DIMACS CNF for CP-SAT model.")
                sys.exit(1)
            if args.encoding == "order":
                encoder = AntibandwidthOrderEncoder(graph, break_symmetry=break_sym)
            else:
                encoder = AntibandwidthSATEncoder(graph, break_symmetry=break_sym)
            encoder.export_dimacs(target_k, args.export_dimacs)
            print(f"[+] Exported DIMACS CNF to: {args.export_dimacs}")
            return

        if is_cpsat:
            cp_solver = AntibandwidthCPSolver(
                graph,
                break_symmetry=break_sym,
                time_limit_seconds=getattr(args, "time_limit", 100.0),
                verbose=False,
            )
            is_sat, labeling, elapsed, n_clauses = cp_solver.check_sat(target_k)
            verifier_fn = cp_solver.verify_solution
        else:
            solver = AntibandwidthSolver(
                graph,
                solver_name=args.solver,
                encoding=args.encoding,
                break_symmetry=break_sym,
                external_solver=args.external_solver,
                verbose=False,
            )
            is_sat, labeling, elapsed, n_clauses = solver.check_sat(target_k)
            verifier_fn = solver.verify_solution

        try:
            status = "SATISFIABLE" if is_sat else "UNSATISFIABLE"
            print(f"[*] Result: {status} in {elapsed:.4f}s ({n_clauses} clauses/constraints)")

            if is_sat and labeling:
                valid, min_d, err = verifier_fn(labeling, target_k)
                print(f"[*] Solution verification: {'VALID' if valid else f'INVALID: {err}'}")
                print(f"[*] Sample vertex labeling: {dict(list(labeling.items())[:10])} ...")

                if args.visualize or args.show_plot:
                    visualize_antibandwidth_labeling(
                        graph=graph,
                        labeling=labeling,
                        k=target_k,
                        title=f"Antibandwidth Solution: k = {target_k} ({info['filename']})",
                        save_path=args.visualize,
                        show=args.show_plot,
                    )
        except RuntimeError as e:
            print(f"[Error] {e}")
            sys.exit(1)
        return

    # Mode 2: Search for optimal Antibandwidth B*(G)
    if is_cpsat:
        cp_solver = AntibandwidthCPSolver(
            graph,
            break_symmetry=break_sym,
            time_limit_seconds=getattr(args, "time_limit", 100.0),
            verbose=True,
        )
        method = "direct_optimize" if args.method == "direct_optimize" else "binary_search"
        results = cp_solver.solve(method=method)
    else:
        solver = AntibandwidthSolver(
            graph,
            solver_name=args.solver,
            encoding=args.encoding,
            break_symmetry=break_sym,
            external_solver=args.external_solver,
            verbose=True,
        )
        try:
            results = solver.solve(method=args.method)
        except RuntimeError as e:
            print(f"[Error] {e}")
            print("\nPlease install the required dependencies with:")
            print("    pip install -r requirements.txt")
            sys.exit(1)

    opt_k = results["optimal_k"]
    labeling = results["labeling"]

    print("=" * 65)
    print(f" RESULT SUMMARY")
    print("=" * 65)
    print(f" Optimal Antibandwidth B*(G): {opt_k}")
    print(f" Total Solving Time:         {results['total_time']:.4f} seconds")
    print(f" Verification Status:        {'PASSED' if results['verified'] else 'FAILED'}")

    if labeling:
        print(f"\n Optimal Labeling (Vertex -> Position):")
        sorted_labels = sorted(labeling.items(), key=lambda x: x[0])
        preview = sorted_labels[:15]
        for v, pos in preview:
            print(f"   Vertex {v:3d} -> Position {pos:3d}")
        if len(sorted_labels) > 15:
            print(f"   ... ({len(sorted_labels) - 15} more vertices)")

        # Generate visual layout / save plot
        if args.visualize or args.show_plot:
            visualize_antibandwidth_labeling(
                graph=graph,
                labeling=labeling,
                k=opt_k,
                title=f"Optimal Antibandwidth B*(G) = {opt_k} for {info['filename']}",
                save_path=args.visualize,
                show=args.show_plot,
            )

    if args.output and labeling:
        out_path = Path(args.output)
        out_data = {
            "graph": info,
            "optimal_antibandwidth": opt_k,
            "solving_time_seconds": results["total_time"],
            "labeling": labeling,
            "encoding": args.encoding,
            "solver": args.solver,
            "symmetry_breaking": break_sym,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"\n[+] Solution saved to: {out_path}")


if __name__ == "__main__":
    main()
