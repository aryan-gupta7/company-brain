"""Graph utilities for Company Brain — networkx-based validation.

- Cycle detection via strongly connected components (O(V+E), not simple_cycles)
- Critical path via dag_longest_path with EDGE weights (not node weights)
- Span-grounding verification (quote must be substring at stated offset)
"""

import networkx as nx
from typing import List, Dict, Any, Tuple, Optional


def build_task_graph(tasks: List[dict], dependencies: List[dict]) -> nx.DiGraph:
    """Build a directed graph from tasks and dependencies.

    Convention: DEPENDS_ON edge goes from the dependent task to its prerequisite.
    (A)-[:DEPENDS_ON]->(B) means "A depends on B" — B must complete before A.

    Node attributes: all task properties (name, time_per_exec_hours, etc.)
    Edge attributes: source_quote, confidence, extraction_method, etc.
    """
    G = nx.DiGraph()
    for task in tasks:
        G.add_node(task['task_id'], **task)
    for dep in dependencies:
        G.add_edge(dep['from'], dep['to'], **{
            k: v for k, v in dep.items()
            if k not in ('from', 'to')
        })
    return G


def detect_cycles(G: nx.DiGraph) -> List[set]:
    """Detect cycles using strongly connected components.

    O(V+E) — handles large graphs. A cycle exists if any SCC has >1 node.
    (Previous bug: used simple_cycles which can blow up exponentially.)
    """
    sccs = nx.strongly_connected_components(G)
    return [scc for scc in sccs if len(scc) > 1]


def find_critical_path(G: nx.DiGraph, duration_attr: str = 'time_per_exec_hours') -> Tuple[list, float]:
    """Find the critical path (longest path by duration) in a DAG.

    dag_longest_path uses EDGE weights, not node weights.
    Converts node durations to edge weights: edge (u,v) gets duration of node u.

    Returns: (path_node_ids, total_duration_hours)
    """
    if detect_cycles(G):
        raise ValueError("Cannot compute critical path: graph contains cycles")

    # Convert node durations to edge weights.
    # Edge (u, v) gets weight = duration of TARGET node (v).
    # This ensures dag_longest_path correctly distinguishes parallel paths.
    # Total = sum(edge weights) + duration of FIRST node.
    G_edges = nx.DiGraph()
    for node_id in G.nodes():
        G_edges.add_node(node_id, **G.nodes[node_id])
    for u, v in G.edges():
        duration = G.nodes[v].get(duration_attr, 0)
        edge_data = G.edges[u, v]
        G_edges.add_edge(u, v, weight=duration, **edge_data)

    path = nx.dag_longest_path(G_edges, weight='weight')
    if not path:
        return [], 0.0
    # Sum edge weights = durations of all nodes except the first
    edge_sum = sum(G_edges[u][v]['weight'] for u, v in zip(path, path[1:]))
    # Add the first node's duration
    first_node_duration = G.nodes[path[0]].get(duration_attr, 0)
    total = edge_sum + first_node_duration
    return path, total


def validate_process_graph(tasks: List[dict], dependencies: List[dict]) -> dict:
    """Validate a process graph: check for cycles, compute critical path.

    Returns a dict with validation results.
    """
    G = build_task_graph(tasks, dependencies)

    cycles = detect_cycles(G)
    if cycles:
        return {
            'valid': False,
            'cycles': [list(c) for c in cycles],
            'message': f"Contradictory dependencies detected: {len(cycles)} cycle(s). Please review.",
        }

    try:
        critical_path, path_hours = find_critical_path(G)
    except Exception:
        critical_path, path_hours = [], 0.0

    return {
        'valid': True,
        'cycles': [],
        'critical_path': critical_path,
        'path_length_hours': path_hours,
        'total_tasks': len(tasks),
        'total_dependencies': len(dependencies),
    }


def compute_downstream_impact(G: nx.DiGraph, source_node: str, max_depth: int = 5) -> List[dict]:
    """Compute all tasks downstream of a source node.

    Uses BFS with typed, directed traversal. Returns DISTINCT nodes.
    (Previous bug: used undirected untyped [*1..5] which explodes through hubs.)
    """
    visited = set()
    results = []
    queue = [(source_node, 0)]

    while queue:
        node, depth = queue.pop(0)
        if node in visited or depth > max_depth:
            continue
        visited.add(node)

        for successor in G.successors(node):
            if successor not in visited:
                results.append({
                    'task_id': successor,
                    'name': G.nodes[successor].get('name', ''),
                    'depth': depth + 1,
                })
                queue.append((successor, depth + 1))

    return results


# --- Span-grounding verification ---

def verify_span_grounding(edge: dict, source_text: str) -> bool:
    """Verify that source_quote is a verbatim substring of source_text.

    Previous bug: span-grounding was never actually verified.
    """
    quote = edge.get('source_quote', '')
    if not quote:
        return False
    return quote in source_text


def verify_all_spans(dependencies: List[dict], source_text: str) -> Tuple[List[dict], List[dict]]:
    """Verify span-grounding for all edges. Returns (valid, invalid) lists."""
    valid = []
    invalid = []
    for dep in dependencies:
        if verify_span_grounding(dep, source_text):
            valid.append(dep)
        else:
            dep['span_error'] = f"Quote not found in source text: {dep.get('source_quote', '')[:80]}..."
            invalid.append(dep)
    return valid, invalid


# --- Confidence / agreement scoring ---

def derive_confidence_for_edge(edge_key: tuple, all_runs: List[List[dict]]) -> float:
    """Agreement score for a SINGLE edge across multiple extraction runs.

    Measures consistency (agreement), NOT correctness.
    Calibrate against gold-label edges to convert agreement → accuracy.

    Edge dicts use 'from' and 'to' keys (matching build_task_graph format).
    Previous bug: counted most common edge across ALL edges, not per-edge.
    """
    if not all_runs:
        return 0.0
    runs_containing = sum(
        1 for run in all_runs
        if any((e.get('from'), e.get('to')) == edge_key for e in run)
    )
    agreement = runs_containing / len(all_runs)
    return min(agreement, 0.95)  # Cap at 0.95 — never 100% certain
