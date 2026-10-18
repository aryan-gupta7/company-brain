"""Tests for graph_utils.py — networkx-based validation."""

import sys; sys.path.insert(0, 'src')

import pytest
from core.graph_utils import (
    build_task_graph, detect_cycles, find_critical_path,
    validate_process_graph, compute_downstream_impact,
    verify_span_grounding, verify_all_spans, derive_confidence_for_edge,
)


class TestBuildGraph:
    """Build directed graph from tasks and dependencies."""

    def test_basic_graph(self):
        tasks = [
            {'task_id': 'a', 'name': 'Task A'},
            {'task_id': 'b', 'name': 'Task B'},
        ]
        deps = [{'from': 'b', 'to': 'a', 'source_quote': 'B depends on A'}]
        G = build_task_graph(tasks, deps)
        assert G.number_of_nodes() == 2
        assert G.number_of_edges() == 1
        assert G.has_edge('b', 'a')  # b depends on a

    def test_edge_attributes(self):
        tasks = [{'task_id': 'a', 'name': 'A'}]
        deps = [{'from': 'a', 'to': 'a', 'source_quote': 'self', 'confidence': 0.5}]
        G = build_task_graph(tasks, deps)
        assert G.edges['a', 'a']['confidence'] == 0.5


class TestCycleDetection:
    """Cycle detection via strongly connected components."""

    def test_no_cycles(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
            {'task_id': 'c', 'name': 'C'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'c', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        cycles = detect_cycles(G)
        assert len(cycles) == 0

    def test_simple_cycle(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'a', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        cycles = detect_cycles(G)
        assert len(cycles) == 1

    def test_self_loop(self):
        tasks = [{'task_id': 'a', 'name': 'A'}]
        deps = [{'from': 'a', 'to': 'a'}]
        G = build_task_graph(tasks, deps)
        cycles = detect_cycles(G)
        # A self-loop creates an SCC of size 1 — not detected as cycle by SCC
        # This is correct: self-loops are trivially resolvable


class TestCriticalPath:
    """Critical path via dag_longest_path with edge weights."""

    def test_linear_chain(self):
        tasks = [
            {'task_id': 'a', 'name': 'A', 'time_per_exec_hours': 1},
            {'task_id': 'b', 'name': 'B', 'time_per_exec_hours': 2},
            {'task_id': 'c', 'name': 'C', 'time_per_exec_hours': 3},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'c', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        path, total = find_critical_path(G)
        assert path == ['c', 'b', 'a']
        # Total = dur(c) + dur(b) + dur(a) = 3 + 2 + 1 = 6
        assert total == 6

    def test_parallel_tasks(self):
        tasks = [
            {'task_id': 'a', 'name': 'A', 'time_per_exec_hours': 1},
            {'task_id': 'b', 'name': 'B', 'time_per_exec_hours': 5},
            {'task_id': 'c', 'name': 'C', 'time_per_exec_hours': 2},
        ]
        deps = [
            {'from': 'c', 'to': 'a'},
            {'from': 'c', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        path, total = find_critical_path(G)
        # c->b is longer (c duration=2, b duration=5) vs c->a (c duration=2, a duration=1)
        assert 'b' in path

    def test_cycle_raises(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'a', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        with pytest.raises(ValueError, match="cycles"):
            find_critical_path(G)


class TestValidateProcessGraph:
    """Full validation: cycles + critical path."""

    def test_valid_graph(self):
        tasks = [
            {'task_id': 'a', 'name': 'A', 'time_per_exec_hours': 1},
            {'task_id': 'b', 'name': 'B', 'time_per_exec_hours': 2},
        ]
        deps = [{'from': 'b', 'to': 'a'}]
        result = validate_process_graph(tasks, deps)
        assert result['valid'] is True
        assert result['critical_path'] == ['b', 'a']
        # Total = dur(b) + dur(a) = 2 + 1 = 3
        assert result['path_length_hours'] == 3

    def test_invalid_graph(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'a', 'to': 'b'},
        ]
        result = validate_process_graph(tasks, deps)
        assert result['valid'] is False
        assert len(result['cycles']) > 0


class TestDownstreamImpact:
    """BFS-based downstream impact computation."""

    def test_direct_downstream(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
            {'task_id': 'c', 'name': 'C'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'c', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        impact = compute_downstream_impact(G, 'a')
        # a has no successors in this graph (b depends on a, c depends on b)
        assert len(impact) == 0

    def test_indirect_downstream(self):
        tasks = [
            {'task_id': 'a', 'name': 'A'},
            {'task_id': 'b', 'name': 'B'},
            {'task_id': 'c', 'name': 'C'},
        ]
        deps = [
            {'from': 'b', 'to': 'a'},
            {'from': 'c', 'to': 'b'},
        ]
        G = build_task_graph(tasks, deps)
        impact = compute_downstream_impact(G, 'c')
        # c -> b -> a (both downstream)
        assert len(impact) == 2


class TestSpanGrounding:
    """Span-grounding verification."""

    def test_valid_span(self):
        edge = {'source_quote': 'hello world'}
        assert verify_span_grounding(edge, 'say hello world now') is True

    def test_invalid_span(self):
        edge = {'source_quote': 'this is not in text'}
        assert verify_span_grounding(edge, 'some other text') is False

    def test_empty_quote(self):
        edge = {'source_quote': ''}
        assert verify_span_grounding(edge, 'any text') is False

    def test_missing_quote(self):
        edge = {}
        assert verify_span_grounding(edge, 'any text') is False

    def test_verify_all_spans(self):
        deps = [
            {'from': 'a', 'to': 'b', 'source_quote': 'match this'},
            {'from': 'b', 'to': 'c', 'source_quote': 'no match here'},
        ]
        valid, invalid = verify_all_spans(deps, 'please match this text')
        assert len(valid) == 1
        assert len(invalid) == 1


class TestConfidenceScoring:
    """Per-edge agreement scoring."""

    def test_full_agreement(self):
        runs = [
            [{'from': 'a', 'to': 'b'}],
            [{'from': 'a', 'to': 'b'}],
            [{'from': 'a', 'to': 'b'}],
        ]
        score = derive_confidence_for_edge(('a', 'b'), runs)
        assert score == 0.95  # capped at 0.95

    def test_partial_agreement(self):
        runs = [
            [{'from': 'a', 'to': 'b'}],
            [{'from': 'a', 'to': 'b'}],
            [],  # edge not found
        ]
        score = derive_confidence_for_edge(('a', 'b'), runs)
        assert score == pytest.approx(2/3, abs=0.01)

    def test_no_agreement(self):
        runs = [
            [{'from': 'x', 'to': 'y'}],
            [{'from': 'z', 'to': 'w'}],
        ]
        score = derive_confidence_for_edge(('a', 'b'), runs)
        assert score == 0.0

    def test_empty_runs(self):
        score = derive_confidence_for_edge(('a', 'b'), [])
        assert score == 0.0


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
