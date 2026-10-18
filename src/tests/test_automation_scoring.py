"""Tests for automation_scoring.py — feasibility × impact framework."""

import sys; sys.path.insert(0, 'src')

import pytest
from core.automation_scoring import (
    compute_feasibility, compute_impact, compute_automation_fraction,
    compute_annual_savings, classify_quadrant, assess, rank_tasks,
    TaskAttributes, AutomationScore,
    STRUCTURENESS_GATE, DECISION_COMPLEXITY_GATE, EXCEPTION_RATE_GATE,
    ERROR_COST_GATE, COMPLIANCE_RISK_GATE, MAX_AUTOMATION_FRACTION,
)


class TestFeasibility:
    """Feasibility = min() of gates, not weighted sum."""

    def test_perfect_task(self):
        """A perfect task should have feasibility 1.0."""
        task = TaskAttributes(
            name='Perfect', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.0,
            error_cost_dollars=0, compliance_risk=0.0,
        )
        assert compute_feasibility(task) == 1.0

    def test_weakest_link(self):
        """Feasibility is limited by the weakest dimension."""
        task = TaskAttributes(
            name='WeakLink', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.8,  # 1-0.8 = 0.2
            error_cost_dollars=0, compliance_risk=0.0,
        )
        assert compute_feasibility(task) == pytest.approx(0.2)

    def test_structuredness_gate(self):
        """If structuredness < 0.3, feasibility capped at 0.3."""
        task = TaskAttributes(
            name='LowStruct', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=0.2, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.0,
            error_cost_dollars=0, compliance_risk=0.0,
        )
        feas = compute_feasibility(task)
        assert feas <= 0.3

    def test_decision_complexity_gate(self):
        """If decision_complexity > 0.7, feasibility capped at 0.4."""
        task = TaskAttributes(
            name='HighJudgment', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.9, exception_rate=0.0,
            error_cost_dollars=0, compliance_risk=0.0,
        )
        feas = compute_feasibility(task)
        assert feas <= 0.4

    def test_exception_rate_gate(self):
        """If exception_rate > 0.5, feasibility capped at 0.4."""
        task = TaskAttributes(
            name='HighExceptions', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.7,
            error_cost_dollars=0, compliance_risk=0.0,
        )
        feas = compute_feasibility(task)
        assert feas <= 0.4


class TestImpact:
    """Impact = frequency × time × labor_rate."""

    def test_basic_impact(self):
        task = TaskAttributes(
            name='Test', frequency_per_year=52, time_per_exec_hours=3.85,
            labor_rate_dollars=42, structuredness=0.5, data_accessibility=0.5,
            decision_complexity=0.5, exception_rate=0.1,
            error_cost_dollars=100, compliance_risk=0.1,
        )
        impact_dollars, impact_norm = compute_impact(task)
        assert impact_dollars == pytest.approx(52 * 3.85 * 42, rel=0.01)

    def test_normalization(self):
        """Impact normalized to reference_max."""
        task = TaskAttributes(
            name='Test', frequency_per_year=1000, time_per_exec_hours=10,
            labor_rate_dollars=200, structuredness=0.5, data_accessibility=0.5,
            decision_complexity=0.5, exception_rate=0.1,
            error_cost_dollars=100, compliance_risk=0.1,
        )
        _, impact_norm = compute_impact(task, reference_max=100_000)
        assert impact_norm == pytest.approx(min(1000 * 10 * 200 / 100_000, 1.0))


class TestAutomationFraction:
    """automation_fraction = feasibility × coverage_rate."""

    def test_full_automation(self):
        # Even perfect tasks are capped at MAX_AUTOMATION_FRACTION (0.85)
        assert compute_automation_fraction(1.0, 0.0) == MAX_AUTOMATION_FRACTION

    def test_with_exceptions(self):
        # feasibility=0.8, coverage=0.9 → 0.72
        assert compute_automation_fraction(0.8, 0.1) == pytest.approx(0.72)

    def test_cap(self):
        """Automation fraction capped at MAX_AUTOMATION_FRACTION (0.85)."""
        assert compute_automation_fraction(1.0, 0.0) <= MAX_AUTOMATION_FRACTION


class TestQuadrant:
    """Feasibility × impact quadrant classification."""

    def test_automate_now(self):
        assert classify_quadrant(0.8, 0.7) == 'AUTOMATE_NOW'

    def test_automate_if_easy(self):
        assert classify_quadrant(0.8, 0.3) == 'AUTOMATE_IF_EASY'

    def test_redesign_first(self):
        assert classify_quadrant(0.4, 0.7) == 'REDESIGN_FIRST'

    def test_dont_automate(self):
        assert classify_quadrant(0.3, 0.2) == 'DONT_AUTOMATE'


class TestAnnualSavings:
    """Savings = hours × automation_fraction × labor_rate + error_reduction - cost."""

    def test_basic_savings(self):
        task = TaskAttributes(
            name='Test', frequency_per_year=52, time_per_exec_hours=3.85,
            labor_rate_dollars=42, structuredness=0.9, data_accessibility=0.95,
            decision_complexity=0.2, exception_rate=0.1,
            error_cost_dollars=500, compliance_risk=0.1,
            implementation_cost_annual=1200,
        )
        frac = compute_automation_fraction(0.8, 0.1)
        savings = compute_annual_savings(task, frac)
        # labor: 200 × 0.72 × 42 = 6048
        # error: 0.72 × 0.8 × 500 × 52 = 14976
        # total: 6048 + 14976 - 1200 = 19824
        assert savings > 0

    def test_error_reduction_scaled_by_fraction(self):
        """Error reduction is scaled by automation_fraction.
        A task with 2% automation should only get 2% of error reduction."""
        task = TaskAttributes(
            name='LowAuto', frequency_per_year=4, time_per_exec_hours=8,
            labor_rate_dollars=150, structuredness=0.2, data_accessibility=0.3,
            decision_complexity=0.9, exception_rate=0.8,
            error_cost_dollars=50000, compliance_risk=0.1,
        )
        frac = compute_automation_fraction(0.1, 0.8)  # 0.1 × 0.2 = 0.02
        savings = compute_annual_savings(task, frac)
        # With 2% automation, error reduction should be tiny
        # error_reduction = 0.02 × 0.8 × 50000 × 4 = 3200
        # NOT 0.8 × 50000 × 4 = 160000 (the old bug)
        assert savings < 10000, f"Savings {savings} too high for 2% automation"


class TestRiskGates:
    """Error cost and compliance risk are gates, not benefits."""

    def test_high_compliance_risk(self):
        task = TaskAttributes(
            name='Compliance', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.0,
            error_cost_dollars=0, compliance_risk=0.9,  # Above gate
        )
        score = assess(task)
        assert score.risk_gate_triggered
        assert score.quadrant == 'PARTIAL_HUMAN_IN_LOOP'

    def test_high_error_cost(self):
        task = TaskAttributes(
            name='HighError', frequency_per_year=100, time_per_exec_hours=1,
            labor_rate_dollars=50, structuredness=1.0, data_accessibility=1.0,
            decision_complexity=0.0, exception_rate=0.0,
            error_cost_dollars=100_000,  # Above gate
            compliance_risk=0.1,
        )
        score = assess(task)
        assert score.risk_gate_triggered
        assert score.quadrant == 'PARTIAL_HUMAN_IN_LOOP'


class TestInvoiceReconciliation:
    """The canonical demo example — must produce consistent numbers."""

    def test_demo_example(self):
        task = TaskAttributes(
            name='Invoice Reconciliation',
            frequency_per_year=52, time_per_exec_hours=3.85,
            labor_rate_dollars=42, structuredness=0.9, data_accessibility=0.95,
            decision_complexity=0.2, exception_rate=0.1,
            error_cost_dollars=500, compliance_risk=0.1,
            implementation_cost_annual=1200,
        )
        score = assess(task)
        assert score.feasibility == 0.8
        assert score.automation_fraction == pytest.approx(0.72)
        assert score.annual_savings > 0
        assert score.risk_gate_triggered is False


class TestRankTasks:
    """Rank tasks by annual savings."""

    def test_ranking(self):
        tasks = [
            TaskAttributes(
                name='Low', frequency_per_year=10, time_per_exec_hours=0.5,
                labor_rate_dollars=25, structuredness=0.5, data_accessibility=0.5,
                decision_complexity=0.5, exception_rate=0.3,
                error_cost_dollars=100, compliance_risk=0.1,
            ),
            TaskAttributes(
                name='High', frequency_per_year=260, time_per_exec_hours=0.5,
                labor_rate_dollars=25, structuredness=0.95, data_accessibility=0.9,
                decision_complexity=0.1, exception_rate=0.05,
                error_cost_dollars=100, compliance_risk=0.1,
            ),
        ]
        ranked = rank_tasks(tasks)
        assert ranked[0].task_name == 'High'
        assert ranked[1].task_name == 'Low'


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
