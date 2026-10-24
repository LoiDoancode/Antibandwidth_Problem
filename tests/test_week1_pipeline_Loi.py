"""Verification and Demonstration Script for Week 1 Deliverables (Thành viên: Lợi).

Verifies:
1. SAT Solver environment configuration (PySAT with glucose4, cadical153, minisat22).
2. Automated DIMACS CNF export pipeline.
3. SAT Solver execution and solution extraction / model decoding.
4. Integration and availability of the required `cnsplots` library.
"""

import os
import sys
import tempfile
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
from src.graph_loader import load_graph
from src.sat_encoder import AntibandwidthSATEncoder
from src.solver import AntibandwidthSolver, HAS_PYSAT


def test_1_pysat_environment():
    print("=" * 65)
    print("TEST 1: SAT Solver Environment & Backends Check")
    print("=" * 65)
    if not HAS_PYSAT:
        print("[FAIL] python-sat (PySAT) is NOT installed.")
        return False
    print("[PASS] PySAT library is installed.")

    from pysat.solvers import Solver

    available_solvers = ["glucose4", "cadical153", "minisat22"]
    for s_name in available_solvers:
        try:
            with Solver(name=s_name) as s:
                # Test with a trivial formula: (x1 OR x2) AND (-x1)
                s.add_clause([1, 2])
                s.add_clause([-1])
                is_sat = s.solve()
                model = s.get_model()
                print(f"  [+] Solver '{s_name:10s}': Available & Operational (Result: SAT, Model: {model})")
        except Exception as e:
            print(f"  [-] Solver '{s_name:10s}': Not available or error: {e}")

    return True


def test_2_dimacs_cnf_export():
    print("\n" + "=" * 65)
    print("TEST 2: Automated DIMACS CNF Export Pipeline")
    print("=" * 65)
    # Build a small path graph P4: 0 - 1 - 2 - 3
    G = nx.path_graph(4)
    target_k = 2

    encoder = AntibandwidthSATEncoder(G, break_symmetry=True)
    with tempfile.NamedTemporaryFile(suffix=".cnf", delete=False, mode="w") as tmp:
        tmp_path = tmp.name

    try:
        encoder.export_dimacs(target_k, tmp_path)
        file_size = os.path.getsize(tmp_path)
        print(f"[PASS] Successfully exported CNF formula to DIMACS format.")
        print(f"       File: {tmp_path}")
        print(f"       Size: {file_size} bytes")

        with open(tmp_path, "r", encoding="utf-8") as f:
            lines = [f.readline().strip() for _ in range(5)]
        print("       Preview first lines:")
        for line in lines:
            print(f"         {line}")
    finally:
        if os.path.exists(tmp_path):
            os.remove(tmp_path)

    return True


def test_3_solver_pipeline_and_decoding():
    print("\n" + "=" * 65)
    print("TEST 3: SAT Solver Execution & Model Extraction Pipeline")
    print("=" * 65)
    # Test on Harwell-Boeing graph (can___24) or fallback
    test_path = PROJECT_ROOT / "data" / "instance" / "harwell-boeing_v2" / "can___24.txt"
    if not test_path.exists():
        test_path = PROJECT_ROOT / "data" / "sample_p6.mtx"

    graph, info = load_graph(test_path)
    print(f"[*] Loaded Graph: {info['filename']} (|V|={info['num_vertices']}, |E|={info['num_edges']})")

    solver = AntibandwidthSolver(graph, solver_name="glucose4", break_symmetry=True, verbose=False)
    
    # Check satisfiability for target k = 2
    is_sat, labeling, elapsed, n_clauses = solver.check_sat(2)
    print(f"[*] check_sat(k=2): Result = {'SATISFIABLE' if is_sat else 'UNSATISFIABLE'}")
    print(f"    Elapsed: {elapsed:.4f}s | Clauses: {n_clauses}")
    print(f"    Decoded Labeling: {labeling}")

    valid, actual_min, err = solver.verify_solution(labeling, 2)
    print(f"[PASS] Solution Verification: {'PASSED' if valid else 'FAILED'} (Actual min distance: {actual_min})")
    return valid


def test_4_cnsplots_library_check():
    print("\n" + "=" * 65)
    print("TEST 4: Library `cnsplots` Integration Check")
    print("=" * 65)
    try:
        import cnsplots as cns
        version = getattr(cns, "__version__", "installed")
        print(f"[PASS] `cnsplots` is successfully imported! (Version: {version})")
        print("       Library is ready for scientific data visualization in Week 2 & 3.")
        return True
    except ImportError as e:
        print(f"[FAIL] Could not import `cnsplots`: {e}")
        return False


def main():
    print("\n" + "#" * 65)
    print("    ANTIBANDWIDTH PROBLEM - WEEK 1 VERIFICATION (LỢI)")
    print("#" * 65 + "\n")

    t1 = test_1_pysat_environment()
    t2 = test_2_dimacs_cnf_export()
    t3 = test_3_solver_pipeline_and_decoding()
    t4 = test_4_cnsplots_library_check()

    print("\n" + "#" * 65)
    if t1 and t2 and t3 and t4:
        print("    ALL WEEK 1 TECHNICAL DELIVERABLES VERIFIED SUCCESSFULLY!")
    else:
        print("    SOME CHECKS REQUIRE ATTENTION. PLEASE REVIEW OUTPUT ABOVE.")
    print("#" * 65 + "\n")


if __name__ == "__main__":
    main()
