"""Main entry point for the Antibandwidth Problem (ABP) SAT Solver.

Usage:
    python main.py --input data/sample_c5.mtx
    python main.py --input data/sample_p6.mtx --solver cadical153
    python main.py --input data/sample_c5.mtx --check-k 2
"""

import argparse
import json
import sys
from pathlib import Path

# Add workspace directory to python path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.graph_loader import load_graph
from src.sat_encoder import AntibandwidthSATEncoder
from src.solver import AntibandwidthSolver


def print_banner():
    banner = r"""
======================================================================
       ANTIBANDWIDTH PROBLEM (ABP) - SAT SOLVER FRAMEWORK
======================================================================
"""
    print(banner)


def parse_args():
    parser = argparse.ArgumentParser(
        description="Solve Antibandwidth Problem (ABP) using SAT solvers and Binary Search."
    )
    parser.add_argument(
        "-i", "--input",
        type=str,
        default="data/sample_c5.mtx",
        help="Path to the graph benchmark file (.mtx, .rb, .edges, .txt). Default: data/sample_c5.mtx",
    )
    parser.add_argument(
        "-k", "--check-k",
        type=int,
        default=None,
        help="Check satisfiability for a single target k instead of running binary search.",
    )
    parser.add_argument(
        "--solver",
        type=str,
        default="glucose4",
        help="PySAT solver backend (e.g., 'glucose4', 'cadical153', 'minisat22', 'lingeling'). Default: glucose4",
    )
    parser.add_argument(
        "--method",
        type=str,
        choices=["binary_search", "linear_search"],
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
    return parser.parse_args()


def main():
    print_banner()
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"[Error] File not found: {input_path}")
        print("Please check the path or use one of the files in data/ (e.g. data/sample_c5.mtx)")
        sys.exit(1)

    print(f"[*] Loading graph from: {input_path} ...")
    try:
        graph, info = load_graph(input_path)
    except Exception as e:
        print(f"[Error] Failed to load graph: {e}")
        sys.exit(1)

    print(f"[*] Graph Summary:")
    print(f"    - Name:        {info['filename']}")
    print(f"    - Vertices |V|: {info['num_vertices']}")
    print(f"    - Edges |E|:    {info['num_edges']}")
    print(f"    - Density:      {info['density']}")
    print(f"    - Degree range: [{info['min_degree']}, {info['max_degree']}]")

    break_sym = not args.no_symmetry_breaking

    # Mode 1: Check single k or export DIMACS
    if args.check_k is not None:
        target_k = args.check_k
        print(f"\n[*] Mode: Single k Check (Target k = {target_k})")

        if args.export_dimacs:
            encoder = AntibandwidthSATEncoder(graph, break_symmetry=break_sym)
            encoder.export_dimacs(target_k, args.export_dimacs)
            print(f"[+] Exported DIMACS CNF to: {args.export_dimacs}")
            return

        solver = AntibandwidthSolver(
            graph,
            solver_name=args.solver,
            break_symmetry=break_sym,
            verbose=False,
        )

        try:
            is_sat, labeling, elapsed, n_clauses = solver.check_sat(target_k)
            status = "SATISFIABLE" if is_sat else "UNSATISFIABLE"
            print(f"[*] Result: {status} in {elapsed:.4f}s ({n_clauses} clauses)")

            if is_sat and labeling:
                valid, min_d, err = solver.verify_solution(labeling, target_k)
                print(f"[*] Solution verification: {'VALID' if valid else f'INVALID: {err}'}")
                print(f"[*] Sample vertex labeling: {dict(list(labeling.items())[:10])} ...")
        except RuntimeError as e:
            print(f"[Error] {e}")
            sys.exit(1)
        return

    # Mode 2: Search for optimal Antibandwidth B*(G)
    solver = AntibandwidthSolver(
        graph,
        solver_name=args.solver,
        break_symmetry=break_sym,
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
        # Print nicely formatted vertex-to-position mapping
        sorted_labels = sorted(labeling.items(), key=lambda x: x[0])
        preview = sorted_labels[:15]
        for v, pos in preview:
            print(f"   Vertex {v:3d} -> Position {pos:3d}")
        if len(sorted_labels) > 15:
            print(f"   ... ({len(sorted_labels) - 15} more vertices)")

    if args.output and labeling:
        out_path = Path(args.output)
        out_data = {
            "graph": info,
            "optimal_antibandwidth": opt_k,
            "solving_time_seconds": results["total_time"],
            "labeling": labeling,
        }
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(out_data, f, indent=2)
        print(f"\n[+] Solution saved to: {out_path}")


if __name__ == "__main__":
    main()
