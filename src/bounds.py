"""Level-1 Lower Bound (LB) and Upper Bound (UB) utilities for the Antibandwidth Problem.

Provides fast, mathematically sound O(V^2) / O(V + E) bounds:
- Upper Bound (UB):
  1. Max-degree bound: k <= n - Delta(G)
  2. Min-degree bound (when delta(G) >= 1): k <= floor((n + 1 - delta(G)) / 2)
- Lower Bound (LB):
  Fast greedy construction heuristic that produces a valid bijective labeling
  and evaluates its exact minimum edge distance.
"""

from typing import Any, Dict, List, Optional
import networkx as nx


def compute_upper_bound(graph: nx.Graph) -> int:
    """Compute a mathematically sound Level-1 upper bound on B*(G).

    Args:
        graph: Undirected NetworkX graph.

    Returns:
        Upper bound integer UB >= B*(G).
    """
    n = graph.number_of_nodes()
    if n <= 1:
        return 0

    # Ignore any self-loops when counting distinct neighbors
    degrees = [sum(1 for u in graph.neighbors(v) if u != v) for v in graph.nodes()]
    max_deg = max(degrees, default=0)
    min_deg = min(degrees, default=0)

    if max_deg == 0:
        return n - 1

    ub = n - max_deg
    if min_deg >= 1:
        ub = min(ub, (n + 1 - min_deg) // 2)

    return max(1, min(ub, n - 1))


def compute_greedy_lower_bound(graph: nx.Graph) -> Dict[str, Any]:
    """Compute a valid Level-1 lower bound and feasible labeling using a greedy heuristic.

    Places vertices one by one in descending order of degree. The highest-degree
    pivot vertex is placed at position 1 (satisfying reflection symmetry breaking),
    and each remaining vertex is placed at the available position that maximizes
    the minimum distance to its already-placed neighbors.

    Args:
        graph: Undirected NetworkX graph.

    Returns:
        Dict with keys:
        - lb: Valid lower bound (min edge distance of the greedy labeling)
        - labeling: Valid bijective mapping {node: position in 1..n}
    """
    n = graph.number_of_nodes()
    nodes = list(graph.nodes())
    if n == 0:
        return {"lb": 0, "labeling": {}}
    if n == 1:
        return {"lb": 0, "labeling": {nodes[0]: 1}}

    # Simple edges without self-loops
    edges = [(u, v) for u, v in graph.edges() if u != v]
    if not edges:
        return {"lb": n - 1, "labeling": {v: i + 1 for i, v in enumerate(nodes)}}

    # Order vertices by degree descending
    deg_map = {v: sum(1 for u in graph.neighbors(v) if u != v) for v in nodes}
    ordered_nodes = sorted(nodes, key=lambda v: deg_map[v], reverse=True)

    available: List[int] = list(range(1, n + 1))
    labeling: Dict[Any, int] = {}

    # Place pivot at position 1 (also satisfies pos[pivot] <= ceil(n/2))
    pivot = ordered_nodes[0]
    labeling[pivot] = available.pop(0)

    pick_left = False  # Alternate ends when a vertex has no placed neighbors
    for u in ordered_nodes[1:]:
        placed_neighbors = [labeling[v] for v in graph.neighbors(u) if v != u and v in labeling]
        if not placed_neighbors:
            chosen_idx = 0 if pick_left else len(available) - 1
            pick_left = not pick_left
            labeling[u] = available.pop(chosen_idx)
            continue

        best_idx = 0
        best_score = (-1, -1)
        for idx, pos in enumerate(available):
            min_d = min(abs(pos - pv) for pv in placed_neighbors)
            total_d = sum(abs(pos - pv) for pv in placed_neighbors)
            score = (min_d, total_d)
            if score > best_score:
                best_score = score
                best_idx = idx

        labeling[u] = available.pop(best_idx)

    lb = min(abs(labeling[u] - labeling[v]) for u, v in edges)
    return {"lb": lb, "labeling": labeling}


def compute_level1_bounds(graph: nx.Graph) -> Dict[str, Any]:
    """Compute both Level-1 LB (with feasible labeling) and UB for graph G.

    Returns:
        Dict with keys: 'lb', 'ub', 'lb_labeling'.
    """
    ub = compute_upper_bound(graph)
    greedy = compute_greedy_lower_bound(graph)
    lb = min(greedy["lb"], ub)
    return {
        "lb": lb,
        "ub": ub,
        "lb_labeling": greedy["labeling"],
    }
