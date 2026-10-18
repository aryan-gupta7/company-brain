"""Automation Assessment Engine — Company Brain.

Feasibility × Impact framework with honest math.

Feasibility: gated (noisy-AND), not weighted sum.
  - A chain is only as strong as its weakest link.
  - min(structuredness, data_access, (1-decision_complexity), (1-exception_rate))
  - Additional gates: if structuredness < 0.3 or decision_complexity > 0.7, cap.

Impact: hours/year × labor rate (dimensional analysis, not ordinal sums).
  - hours_per_year = frequency_per_year × time_per_exec_hours
  - impact_dollars = hours_per_year × labor_rate

Risk gates: error cost and compliance risk are gates, NOT benefits.
  - High compliance risk → force human-in-loop regardless of feasibility.
"""

from dataclasses import dataclass
from typing import Tuple

# Thresholds for gates (configurable defaults, not research-derived constants)
STRUCTURENESS_GATE = 0.3      # Below this, cap feasibility
DECISION_COMPLEXITY_GATE = 0.7  # Above this, cap feasibility
EXCEPTION_RATE_GATE = 0.5     # Above this, cap feasibility
ERROR_COST_GATE = 50_000       # Above this, force human-in-loop
COMPLIANCE_RISK_GATE = 0.7    # Above this, force human-in-loop
MAX_AUTOMATION_FRACTION = 0.85  # Even perfect tasks keep 15% human oversight


@dataclass
class TaskAttributes:
    """All inputs for automation scoring. Every field is source-labeled."""
    name: str
    frequency_per_year: float   # Source: user-provided or estimated from SOP
    time_per_exec_hours: float  # Source: user-provided or estimated from SOP
    labor_rate_dollars: float   # Source: user-provided fully-loaded rate
    structuredness: float       # Source: extraction or user-provided (0-1)
    data_accessibility: float   # Source: extraction or user-provided (0-1)
    decision_complexity: float  # Source: extraction or user-provided (0-1)
    exception_rate: float       # Source: user-provided or historical (0-1)
    error_cost_dollars: float   # Source: user-provided
    compliance_risk: float      # Source: user-provided or regulation-mapped (0-1)
    implementation_cost_annual: float = 0.0  # Source: user-provided


@dataclass
class AutomationScore:
    """Result of automation assessment."""
    task_name: str
    feasibility: float          # 0-1
    impact_dollars: float       # annual dollar impact
    impact_normalized: float    # 0-1 (relative to reference)
    quadrant: str               # 'AUTOMATE_NOW' | 'AUTOMATE_IF_EASY' | 'REDESIGN_FIRST' | 'DONT_AUTOMATE' | 'PARTIAL_HUMAN_IN_LOOP'
    automation_fraction: float  # 0-1 (fraction of runs fully automated)
    annual_savings: float       # dollars/year
    risk_gate_triggered: bool   # True if human-in-loop required
    derivation: dict            # full derivation for transparency


def compute_feasibility(task: TaskAttributes) -> float:
    """Compute feasibility using gated approach (noisy-AND).

    NOT a weighted sum — strengths cannot compensate for fatal weaknesses.
    """
    # Base feasibility = minimum of all dimensions (weakest link)
    feasibility = min(
        task.structuredness,
        task.data_accessibility,
        1.0 - task.decision_complexity,
        1.0 - task.exception_rate,
    )

    # Additional gates: cap feasibility if critical dimensions are too low
    if task.structuredness < STRUCTURENESS_GATE:
        feasibility = min(feasibility, 0.3)
    if task.decision_complexity > DECISION_COMPLEXITY_GATE:
        feasibility = min(feasibility, 0.4)
    if task.exception_rate > EXCEPTION_RATE_GATE:
        feasibility = min(feasibility, 0.4)

    return max(0.0, min(1.0, feasibility))


def compute_impact(task: TaskAttributes, reference_max: float = 100_000.0) -> Tuple[float, float]:
    """Compute impact in dollars and normalized 0-1.

    Impact = frequency × time_per_exec × labor_rate (hours/year × $/hour)
    Normalized = impact / reference_max, capped at 1.0
    """
    hours_per_year = task.frequency_per_year * task.time_per_exec_hours
    impact_dollars = hours_per_year * task.labor_rate_dollars
    impact_normalized = min(impact_dollars / reference_max, 1.0)
    return impact_dollars, impact_normalized


def compute_automation_fraction(feasibility: float, exception_rate: float) -> float:
    """Compute what fraction of runs can be fully automated.

    coverage_rate = 1 - exception_rate (fraction of runs with no exceptions)
    automation_fraction = feasibility × coverage_rate, capped at MAX_AUTOMATION_FRACTION

    NOTE: exception_rate appears in BOTH feasibility (as a gate via min) and
    coverage_rate. This is intentional:
    - feasibility gates whether automation is possible at all
    - coverage_rate reduces how often automation actually applies
    - A task with 50% exception rate: feasibility capped at 0.5, coverage = 0.5
    - automation_fraction = 0.5 × 0.5 = 0.25 (only 25% of runs fully automated)
    """
    coverage_rate = 1.0 - exception_rate
    return min(feasibility * coverage_rate, MAX_AUTOMATION_FRACTION)


def compute_annual_savings(task: TaskAttributes, automation_fraction: float) -> float:
    """Compute annual savings with full derivation.

    annual_savings = (hours_per_year × automation_fraction × labor_rate)
                   + error_reduction_value
                   - implementation_cost

    Demo example (consistent with formula):
      Invoice reconciliation: 200 hours/year, $42/hr, feasibility=0.8, coverage=0.9
      automation_fraction = 0.8 × 0.9 = 0.72
      annual_savings = (200 × 0.72 × $42) - $1,200 = $6,048 - $1,200 = $4,848
    """
    hours_per_year = task.frequency_per_year * task.time_per_exec_hours
    labor_savings = hours_per_year * automation_fraction * task.labor_rate_dollars

    # Error reduction: scaled by automation_fraction (only automated runs benefit)
    # If only 2% of runs are automated, only 2% get error reduction
    error_reduction_rate = 0.8
    error_reduction_value = (
        automation_fraction
        * error_reduction_rate
        * task.error_cost_dollars
        * task.frequency_per_year
    )

    total = labor_savings + error_reduction_value - task.implementation_cost_annual
    return total


def classify_quadrant(feasibility: float, impact_normalized: float) -> str:
    """Classify into feasibility × impact quadrant."""
    high_feas = feasibility >= 0.6
    high_impact = impact_normalized >= 0.5

    if high_feas and high_impact:
        return 'AUTOMATE_NOW'
    elif high_feas and not high_impact:
        return 'AUTOMATE_IF_EASY'
    elif not high_feas and high_impact:
        return 'REDESIGN_FIRST'
    else:
        return 'DONT_AUTOMATE'


def assess(task: TaskAttributes) -> AutomationScore:
    """Full automation assessment for a task."""
    feasibility = compute_feasibility(task)
    impact_dollars, impact_normalized = compute_impact(task)

    # Risk gates
    risk_gate_triggered = (
        task.error_cost_dollars > ERROR_COST_GATE or
        task.compliance_risk > COMPLIANCE_RISK_GATE
    )

    automation_fraction = compute_automation_fraction(feasibility, task.exception_rate)

    # If risk gate triggered, cap automation and recompute savings
    if risk_gate_triggered:
        automation_fraction = min(automation_fraction, 0.7)
        quadrant = 'PARTIAL_HUMAN_IN_LOOP'
    else:
        quadrant = classify_quadrant(feasibility, impact_normalized)

    annual_savings = compute_annual_savings(task, automation_fraction)

    return AutomationScore(
        task_name=task.name,
        feasibility=round(feasibility, 3),
        impact_dollars=round(impact_dollars, 2),
        impact_normalized=round(impact_normalized, 3),
        quadrant=quadrant,
        automation_fraction=round(automation_fraction, 3),
        annual_savings=round(annual_savings, 2),
        risk_gate_triggered=risk_gate_triggered,
        derivation={
            'hours_per_year': task.frequency_per_year * task.time_per_exec_hours,
            'feasibility_calc': f"min({task.structuredness}, {task.data_accessibility}, {1-task.decision_complexity:.2f}, {1-task.exception_rate:.2f}) = {feasibility:.3f}",
            'impact_calc': f"{task.frequency_per_year} × {task.time_per_exec_hours} × ${task.labor_rate_dollars} = ${impact_dollars:.2f}",
            'automation_fraction_calc': f"{feasibility:.3f} × {1-task.exception_rate:.2f} = {automation_fraction:.3f}",
            'savings_calc': f"({task.frequency_per_year * task.time_per_exec_hours:.0f} × {automation_fraction:.3f} × ${task.labor_rate_dollars}) + error_reduction - ${task.implementation_cost_annual} = ${annual_savings:.2f}",
            'risk_gate': f"error_cost=${task.error_cost_dollars} (gate={ERROR_COST_GATE}), compliance_risk={task.compliance_risk} (gate={COMPLIANCE_RISK_GATE})",
            'source_labels': {
                'frequency_per_year': 'user-provided or estimated',
                'time_per_exec_hours': 'user-provided or estimated',
                'labor_rate_dollars': 'user-provided',
                'structuredness': 'extraction or user-provided',
                'data_accessibility': 'extraction or user-provided',
                'decision_complexity': 'extraction or user-provided',
                'exception_rate': 'user-provided or historical',
                'error_cost_dollars': 'user-provided',
                'compliance_risk': 'user-provided or regulation-mapped',
            }
        }
    )


def rank_tasks(tasks: list) -> list:
    """Rank tasks by annual savings (descending)."""
    scores = [assess(t) for t in tasks]
    return sorted(scores, key=lambda s: s.annual_savings, reverse=True)
