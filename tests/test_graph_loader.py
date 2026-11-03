"""Test script for GraphLoader and data/acoust.data."""

import sys
from pathlib import Path

# Configure UTF-8 output for Windows console
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from src.graph_loader import GraphLoader, load_graph, resolve_graph_path


def test_resolve_and_load_acoust_data():
    print("=" * 65)
    print("TEST 1: Resolve path & load_graph('acoust.data')")
    print("=" * 65)

    # 1. Test resolve_graph_path
    resolved = resolve_graph_path("acoust.data")
    print(f"[*] Resolved path: {resolved}")
    assert resolved.exists(), f"File not found at {resolved}"

    # 2. Test automatic load_graph()
    G_auto, info = load_graph("acoust.data")
    print("[*] Result from load_graph('acoust.data'):")
    for k, v in info.items():
        print(f"    - {k:14s}: {v}")

    # 3. Test direct Harwell-Boeing parser GraphLoader.from_harwell_boeing()
    print("\n" + "=" * 65)
    print("TEST 2: Direct GraphLoader.from_harwell_boeing('data/acoust.data')")
    print("=" * 65)
    G_hb = GraphLoader.from_harwell_boeing(resolved)
    print(f"[*] Nodes (from_harwell_boeing): {G_hb.number_of_nodes()}")
    print(f"[*] Edges (from_harwell_boeing): {G_hb.number_of_edges()}")

    # 4. Inspect header of acoust.data to verify expected dimensions
    print("\n" + "=" * 65)
    print("TEST 3: Inspect acoust.data Header vs Loaded Graph")
    print("=" * 65)
    with open(resolved, "r", encoding="utf-8", errors="ignore") as f:
        header_lines = [f.readline().rstrip("\n") for _ in range(5)]

    print("[*] First 5 lines of acoust.data:")
    for i, line in enumerate(header_lines, 1):
        print(f"    Line {i}: {line}")

    # Expected from line 3: CSA 841 841 4089 0 -> 841 vertices
    expected_nodes = int(header_lines[2][3:].split()[0])
    print(f"\n[*] Expected vertices from Harwell-Boeing header: {expected_nodes}")
    print(f"    - load_graph() vertices           : {G_auto.number_of_nodes()}")
    print(f"    - from_harwell_boeing() vertices  : {G_hb.number_of_nodes()}")

    if G_auto.number_of_nodes() == expected_nodes and G_auto.number_of_edges() == G_hb.number_of_edges():
        print("\n[PASS] load_graph('acoust.data') đọc đúng định dạng Harwell-Boeing!")
    else:
        print("\n[WARNING] Phát hiện sự sai lệch khi dùng load_graph('acoust.data')!")
        print("  -> Nguyên nhân 1: Đuôi file '.data' chưa có trong danh sách ['.rb', '.rua', '.rsa', '.hb']")
        print("     của hàm load_graph(), và phần nhận diện nội dung (content-based detection) thấy dòng 2")
        print("     ('1672 53 256 1363 0') có >= 3 số nguyên nên tưởng nhầm là Coordinate Format (nrows=1672)!")
        print("  -> Nguyên nhân 2: File acoust.data thực chất là một file gộp chứa NHIỀU ma trận Harwell-Boeing")
        print("     nối tiếp nhau (ví dụ: YOUNG1C, YOUNG2C, ...).")


if __name__ == "__main__":
    test_resolve_and_load_acoust_data()
