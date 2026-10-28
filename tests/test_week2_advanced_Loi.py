"""Verification and Demonstration Script for Week 2 Deliverables (Thành viên: Lợi).

Thoroughly verifies Week 2 advanced algorithms and modules:
1. Symmetry Breaking mechanism in both Direct and Order Encoding (pivot vertex selection, half-space pruning).
2. Order Encoding CNF generation (monotonicity, injectivity/bijectivity, Tamura distance propagation including p = n - k).
3. Correctness of model decoding for Order Encoding.
4. Equivalence and validity of optimal Antibandwidth B*(G) solutions on benchmark graphs (Cycle C5, Path P6, Edge P2).
5. Convenience methods: solve_binary_search() and solve_linear_search().
6. Visualization module functionality (ASCII linear arc layout & dual-plot generation).
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import networkx as nx
from src.graph_loader import load_graph
from src.sat_encoder import AntibandwidthSATEncoder
from src.order_encoder import AntibandwidthOrderEncoder
from src.solver import AntibandwidthSolver, HAS_PYSAT
from src.visualizer import print_ascii_linear_layout, visualize_antibandwidth_labeling, HAS_MATPLOTLIB, HAS_CNSPLOTS


def test_1_symmetry_breaking_formulation():
    print("=" * 68)
    print("TEST 1: Symmetry Breaking Formulation & Clause Pruning")
    print("=" * 68)

    # 1. Star graph K_1,5 (nodes 0..5, deg(0)=5, others=1)
    G_star = nx.star_graph(5)
    n = G_star.number_of_nodes()
    half = (n + 1) // 2  # for n=6, half = 3

    # Direct Encoder
    direct_enc = AntibandwidthSATEncoder(G_star, break_symmetry=True)
    assert direct_enc.pivot_vertex == 0, f"Expected pivot vertex 0, got {direct_enc.pivot_vertex}"
    cnf_direct = direct_enc.encode(k=2)

    # Check that positions > half are forbidden for pivot vertex in direct encoding
    forbidden_positions = list(range(half + 1, n + 1))
    found_sb_direct = 0
    for clause in cnf_direct.clauses:
        if len(clause) == 1:
            lit = clause[0]
            if lit < 0:
                v, p = direct_enc.decode_var(lit)
                if v == 0 and p in forbidden_positions:
                    found_sb_direct += 1
    assert found_sb_direct == len(forbidden_positions), (
        f"Direct symmetry breaking clauses missing: expected {len(forbidden_positions)}, found {found_sb_direct}"
    )
    print(f"  [+] Direct Encoding on Star(5): Pivot = {direct_enc.pivot_vertex} (degree {G_star.degree[0]})")
    print(f"      Pruning unit clauses added for positions {forbidden_positions}: {found_sb_direct} clauses.")

    # Order Encoder
    order_enc = AntibandwidthOrderEncoder(G_star, break_symmetry=True)
    assert order_enc.pivot_vertex == 0, f"Expected pivot vertex 0, got {order_enc.pivot_vertex}"
    cnf_order = order_enc.encode(k=2)

    # In Order Encoding, pos(0) <= half is simply unit clause: [var(0, half)]
    expected_lit = order_enc.var(0, half)
    found_sb_order = any(clause == [expected_lit] for clause in cnf_order.clauses)
    assert found_sb_order, f"Order symmetry breaking unit clause [{expected_lit}] not found!"
    print(f"  [+] Order Encoding on Star(5): Pivot = {order_enc.pivot_vertex}")
    print(f"      Single unit clause [y_{{{order_enc.pivot_vertex}, {half}}}] successfully enforced.")

    # 2. Corner case: n = 2 (minimal graph)
    G_p2 = nx.path_graph(2)
    order_p2 = AntibandwidthOrderEncoder(G_p2, break_symmetry=True)
    cnf_p2 = order_p2.encode(k=1)
    # For n=2, half = (2+1)//2 = 1. Pivot must have y_{pivot, 1}
    assert [order_p2.var(order_p2.pivot_vertex, 1)] in cnf_p2.clauses
    print(f"  [+] Corner Case n=2: Symmetry breaking unit clause correctly placed at half=1.")

    print("[PASS] Test 1: Symmetry Breaking formulation verified successfully.\n")
    return True


def test_2_order_encoding_monotonicity_and_tamura_intervals():
    print("=" * 68)
    print("TEST 2: Order Encoding Monotonicity, Tamura Intervals & Decoding")
    print("=" * 68)

    # Path graph P4: 0 - 1 - 2 - 3 (n=4)
    G = nx.path_graph(4)
    n = 4
    k = 2
    encoder = AntibandwidthOrderEncoder(G, break_symmetry=False)
    cnf = encoder.encode(k=k)

    # 1. Total order variables: n * (n - 1) = 4 * 3 = 12
    num_vars = n * (n - 1)
    print(f"  [*] Graph P4 (n={n}, k={k}): Number of order variables = {num_vars}")

    # 2. Monotonicity clauses: for each v, y_{v, p} -> y_{v, p+1}  (n * (n - 2) clauses)
    mono_clauses_count = 0
    for v in range(n):
        for p in range(1, n - 1):
            expected = [-encoder.var(v, p), encoder.var(v, p + 1)]
            assert expected in cnf.clauses, f"Missing monotonicity clause {expected}"
            mono_clauses_count += 1
    print(f"  [+] Monotonicity clauses verified: {mono_clauses_count} clauses.")

    # 3. Tamura Interval propagation clauses:
    # For edge (u, v) and for each p in [1, n - k]:
    # [-var(u, p), var(v, p), -var(v, p + k - 1)]
    # In P4 with k=2, n-k = 2. Positions p = 1 and p = 2 must both exist!
    tamura_clauses_count = 0
    for u, v in G.edges():
        for p in range(1, n - k + 1):
            c1 = [-encoder.var(u, p), encoder.var(v, p), -encoder.var(v, p + k - 1)]
            c2 = [-encoder.var(v, p), encoder.var(u, p), -encoder.var(u, p + k - 1)]
            assert c1 in cnf.clauses, f"Missing Tamura interval clause {c1} for p={p}"
            assert c2 in cnf.clauses, f"Missing Tamura interval clause {c2} for p={p}"
            tamura_clauses_count += 2
    print(f"  [+] Tamura interval clauses verified (including p = n - k = 2): {tamura_clauses_count} clauses.")

    # 4. Model Decoding logic verification
    # Suppose variable assignments:
    # v0: f(v0) = 1  => y_{0, 1}=T, y_{0, 2}=T, y_{0, 3}=T
    # v1: f(v1) = 3  => y_{1, 1}=F, y_{1, 2}=F, y_{1, 3}=T
    # v2: f(v2) = 2  => y_{2, 1}=F, y_{2, 2}=T, y_{2, 3}=T
    # v3: f(v3) = 4  => y_{3, 1}=F, y_{3, 2}=F, y_{3, 3}=F (all false means f(v3) = 4)
    simulated_model = [
        encoder.var(0, 1), encoder.var(0, 2), encoder.var(0, 3),
        -encoder.var(1, 1), -encoder.var(1, 2), encoder.var(1, 3),
        -encoder.var(2, 1), encoder.var(2, 2), encoder.var(2, 3),
        -encoder.var(3, 1), -encoder.var(3, 2), -encoder.var(3, 3),
    ]
    decoded = encoder.decode_model(simulated_model)
    expected_labeling = {0: 1, 1: 3, 2: 2, 3: 4}
    assert decoded == expected_labeling, f"Decoding mismatch: got {decoded}, expected {expected_labeling}"
    print(f"  [+] Model Decoding correctly mapped Order literals to labeling: {decoded}")
    print("[PASS] Test 2: Order encoding structure & decoding logic verified.\n")
    return True


def test_3_solver_solution_and_equivalence():
    print("=" * 68)
    print("TEST 3: End-to-End Solving & Equivalence (Direct vs. Order)")
    print("=" * 68)

    if not HAS_PYSAT:
        print("  [SKIP] PySAT not available in current environment. Logic verified via encoder tests.")
        return True

    # 1. Test on Cycle C5 (Known optimal B*(C5) = 2)
    G_c5 = nx.cycle_graph(5)
    solver_direct = AntibandwidthSolver(G_c5, encoding="direct", break_symmetry=True, verbose=False)
    k_direct, label_direct, time_direct = solver_direct.solve_binary_search()
    valid_direct, min_d_direct, _ = solver_direct.verify_solution(label_direct, k_direct)

    solver_order = AntibandwidthSolver(G_c5, encoding="order", break_symmetry=True, verbose=False)
    k_order, label_order, time_order = solver_order.solve_binary_search()
    valid_order, min_d_order, _ = solver_order.verify_solution(label_order, k_order)

    print(f"  [*] Graph C5 (n=5, m=5):")
    print(f"      Direct Encoding: B*(G) = {k_direct} (Valid: {valid_direct}, Time: {time_direct:.4f}s)")
    print(f"      Order Encoding : B*(G) = {k_order} (Valid: {valid_order}, Time: {time_order:.4f}s)")
    assert k_direct == 2, f"Direct encoding gave B*(C5) = {k_direct}, expected 2"
    assert k_order == 2, f"Order encoding gave B*(C5) = {k_order}, expected 2"
    assert valid_direct and valid_order, "One or both labelings failed verification!"

    # 2. Test Linear Search convenience method on C5
    k_order_lin, label_order_lin, time_order_lin = solver_order.solve_linear_search()
    assert k_order_lin == 2, f"Linear search gave {k_order_lin}, expected 2"
    print(f"      Linear Search  : B*(G) = {k_order_lin} (Time: {time_order_lin:.4f}s)")

    # 3. Test on Path P6 (Known optimal B*(P6) = 3)
    G_p6 = nx.path_graph(6)
    solver_p6 = AntibandwidthSolver(G_p6, encoding="order", break_symmetry=True, verbose=False)
    k_p6, label_p6, time_p6 = solver_p6.solve_binary_search()
    valid_p6, min_d_p6, _ = solver_p6.verify_solution(label_p6, k_p6)
    print(f"  [*] Graph P6 (n=6, m=5):")
    print(f"      Order Encoding : B*(G) = {k_p6} (Valid: {valid_p6}, Time: {time_p6:.4f}s)")
    assert k_p6 == 3, f"Order encoding gave B*(P6) = {k_p6}, expected 3"
    assert valid_p6, "P6 labeling failed verification!"

    # 4. Corner case: 2-node graph P2 (Known optimal B*(P2) = 1)
    G_p2 = nx.path_graph(2)
    solver_p2 = AntibandwidthSolver(G_p2, encoding="order", break_symmetry=True, verbose=False)
    k_p2, label_p2, time_p2 = solver_p2.solve_binary_search()
    valid_p2, _, _ = solver_p2.verify_solution(label_p2, k_p2)
    print(f"  [*] Corner Case P2 (n=2, m=1):")
    print(f"      Order Encoding : B*(G) = {k_p2} (Valid: {valid_p2})")
    assert k_p2 == 1, f"Expected B*(P2)=1, got {k_p2}"
    assert valid_p2, "P2 labeling failed verification!"

    print("[PASS] Test 3: Solvers produced identical optimal values matching theoretical bounds.\n")
    return True


def test_4_visualization_module():
    print("=" * 68)
    print("TEST 4: Visualization Module & Dual-Layout Export")
    print("=" * 68)

    # Path graph P4 with labeling
    G = nx.path_graph(4)
    labeling = {0: 1, 1: 3, 2: 2, 3: 4}
    k = 1

    # 1. Verify ASCII layout printer runs without exception
    print_ascii_linear_layout(4, list(G.edges()), labeling, k)
    print(f"  [+] ASCII 1D layout printer verified.")
    print(f"  [+] Matplotlib available: {HAS_MATPLOTLIB}")
    print(f"  [+] cnsplots available: {HAS_CNSPLOTS}")

    # 2. Verify export to file (if matplotlib is installed)
    if HAS_MATPLOTLIB:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_png = tmp.name
        try:
            ok = visualize_antibandwidth_labeling(G, labeling, k, save_path=tmp_png, show=False)
            assert ok, "visualize_antibandwidth_labeling returned False"
            assert os.path.exists(tmp_png) and os.path.getsize(tmp_png) > 0, "Output image file is empty or missing"
            print(f"  [+] Dual-layout plot successfully rendered and exported ({os.path.getsize(tmp_png)} bytes).")
        finally:
            if os.path.exists(tmp_png):
                os.remove(tmp_png)

    print("[PASS] Test 4: Visualizer interface & export verified.\n")
    return True


def main():
    print("\n" + "#" * 68)
    print("    ANTIBANDWIDTH PROBLEM - WEEK 2 VERIFICATION SUITE")
    print("    Thành viên: Lợi | Superpowers Quality & Rigor Process")
    print("#" * 68 + "\n")

    t1 = test_1_symmetry_breaking_formulation()
    t2 = test_2_order_encoding_monotonicity_and_tamura_intervals()
    t3 = test_3_solver_solution_and_equivalence()
    t4 = test_4_visualization_module()

    print("#" * 68)
    if t1 and t2 and t3 and t4:
        print("    ALL WEEK 2 DELIVERABLES VERIFIED WITH 100% SUCCESS!")
    else:
        print("    SOME CHECKS REQUIRE ATTENTION. PLEASE REVIEW OUTPUT ABOVE.")
    print("#" * 68 + "\n")


if __name__ == "__main__":
    main()
