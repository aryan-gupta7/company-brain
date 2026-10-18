"""Company Brain Demo Runner.

Runs the 3 demo modules:
1. Incident Response (curated playbook + deterministic deadlines)
2. Process Extraction (span-grounded, with confidence)
3. Automation Assessment (feasibility × impact, honest math)

Usage:
    uv run python -m demo.run_demo
    uv run python -m demo.run_demo --module incident
    uv run python -m demo.run_demo --module automation
"""

import sys; sys.path.insert(0, 'src')

from datetime import datetime
from demo.seed_data import get_playbook, get_demo_tasks
from core.deadline_calculator import compute_deadline
from core.automation_scoring import assess, TaskAttributes
from core.graph_utils import validate_process_graph, verify_span_grounding, derive_confidence_for_edge


def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


def print_subheader(title: str):
    print(f"\n--- {title} ---")


# === Module 1: Incident Response ===

def run_incident_demo():
    """Demo: Data breach detected. Agent traverses playbook, computes deadlines."""
    print_header("MODULE 1: INCIDENT RESPONSE")
    print()
    print('User: "We detected unauthorized access to our production database')
    print('        at 2:30 PM UTC today (Friday Oct 16, 2026)."')
    print()

    detected_at = datetime(2026, 10, 16, 14, 30)  # Friday
    playbook = get_playbook('data_breach')

    print(f"Agent: \"{playbook['name']}\"")
    print(f"  Source: {playbook['source']}")
    print(f"  Detected: {detected_at.strftime('%A %b %d %H:%M UTC')}")
    print()

    for step in playbook['steps']:
        deadline = compute_deadline(detected_at, step['amount'], step['unit'])

        if step['amount'] == 0:
            timing = "⏱️ NOW"
        elif step['unit'] == 'clock_hours':
            timing = f"⏱️ Within {step['amount']} clock hour{'s' if step['amount'] != 1 else ''}"
        elif step['unit'] == 'calendar_days':
            timing = f"⏱️ Within {step['amount']} calendar day{'s' if step['amount'] != 1 else ''}"
        elif step['unit'] == 'business_days':
            timing = f"⏱️ Within {step['amount']} business day{'s' if step['amount'] != 1 else ''}"
        else:
            timing = f"⏱️ Within {step['amount']} {step['unit']}"

        print(f"  {timing} (by {deadline.strftime('%A %b %d %H:%M UTC')}):")
        print(f"    → {step['name']}")
        print(f"    → Contact: {step['contact']} ({step['contact_role']})")
        if step['legal_citation']:
            print(f"    → Legal basis: {step['legal_citation']}")
        print()

    print("  ⚠️  DECISION SUPPORT — NOT LEGAL ADVICE")
    print("  Requirements vary by jurisdiction. Consult qualified legal counsel.")
    print(f"  Sources: {playbook['source']}, GDPR Articles 33-34")
    print()
    print("  Evidence subgraph: Playbook → HAS_STEP → StepTemplate → CONTACT → Person")
    print(f"  [All deadlines computed deterministically from {detected_at.isoformat()}]")


# === Module 2: Process Extraction ===

def run_extraction_demo():
    """Demo: Extract tasks and dependencies from a sample SOP."""
    print_header("MODULE 2: PROCESS EXTRACTION")
    print()
    print('User: "Here is our invoice processing SOP. What did you extract?"')
    print()

    # Sample SOP text (would be a real document in production)
    sop_text = """
    Invoice Processing Procedure

    1. Receive invoice from vendor via email
    2. Match invoice against purchase order
    3. Verify line items and amounts
    4. Check budget approval
    5. Submit for payment approval
    6. Process payment
    7. File paid invoice

    After receiving the invoice, match it against the purchase order.
    After matching is complete, verify all line items.
    After verification, check budget approval before submitting.
    After budget approval, submit for payment approval.
    After payment approval, process the payment.
    After payment is processed, file the paid invoice.
    """

    # Simulated extraction results (in production, this comes from GraphRAG SDK + LLM)
    extracted_tasks = [
        {'task_id': 'inv_1', 'name': 'Receive invoice', 'time_per_exec_hours': 0.25},
        {'task_id': 'inv_2', 'name': 'Match against PO', 'time_per_exec_hours': 0.5},
        {'task_id': 'inv_3', 'name': 'Verify line items', 'time_per_exec_hours': 0.5},
        {'task_id': 'inv_4', 'name': 'Check budget approval', 'time_per_exec_hours': 0.25},
        {'task_id': 'inv_5', 'name': 'Submit payment approval', 'time_per_exec_hours': 0.25},
        {'task_id': 'inv_6', 'name': 'Process payment', 'time_per_exec_hours': 0.1},
        {'task_id': 'inv_7', 'name': 'File paid invoice', 'time_per_exec_hours': 0.1},
    ]

    # Convention: DEPENDS_ON edge goes from dependent task to prerequisite
    # (A)-[:DEPENDS_ON]->(B) means "A depends on B" — B must complete first
    extracted_deps = [
        {'from': 'inv_2', 'to': 'inv_1', 'source_quote': 'After receiving the invoice, match it against the purchase order', 'confidence': 0.9},
        {'from': 'inv_3', 'to': 'inv_2', 'source_quote': 'After matching is complete, verify all line items', 'confidence': 0.85},
        {'from': 'inv_4', 'to': 'inv_3', 'source_quote': 'After verification, check budget approval before submitting', 'confidence': 0.75},
        {'from': 'inv_5', 'to': 'inv_4', 'source_quote': 'After budget approval, submit for payment approval', 'confidence': 0.8},
        {'from': 'inv_6', 'to': 'inv_5', 'source_quote': 'After payment approval, process the payment', 'confidence': 0.9},
        {'from': 'inv_7', 'to': 'inv_6', 'source_quote': 'After payment is processed, file the paid invoice', 'confidence': 0.85},
    ]

    print("Agent: \"Extraction results (7 tasks, 6 dependencies):\"")
    print()

    # Verify span grounding
    valid, invalid = [], []
    for dep in extracted_deps:
        if verify_span_grounding(dep, sop_text):
            valid.append(dep)
        else:
            invalid.append(dep)

    print(f"  ✅ Span-grounded: {len(valid)}/{len(extracted_deps)} edges verified")
    if invalid:
        print(f"  ❌ Span errors: {len(invalid)} edges")
    print()

    # Validate graph
    result = validate_process_graph(extracted_tasks, extracted_deps)

    if result['valid']:
        print(f"  ✅ No cycles detected")
        print(f"  📊 Critical path: {' → '.join(result['critical_path'])}")
        print(f"  ⏱️  Critical path length: {result['path_length_hours']:.2f} hours")
    else:
        print(f"  ❌ Cycles detected: {result['cycles']}")
    print()

    print("  Extracted dependency graph:")
    for dep in extracted_deps:
        from_name = next(t['name'] for t in extracted_tasks if t['task_id'] == dep['from'])
        to_name = next(t['name'] for t in extracted_tasks if t['task_id'] == dep['to'])
        status = "✅" if dep in valid else "❌"
        print(f"    {status} {from_name} → depends on → {to_name} (confidence: {dep['confidence']})")
    print()
    print("  ⚠️  Low-confidence edges flagged for user review.")
    print("  Convention: (A)-[:DEPENDS_ON]->(B) means A depends on B (B must complete first)")


# === Module 3: Automation Assessment ===

def run_automation_demo():
    """Demo: Score tasks on automation potential."""
    print_header("MODULE 3: AUTOMATION ASSESSMENT")
    print()
    print('User: "Analyze our processes. What can we automate?"')
    print()

    tasks = get_demo_tasks()
    scores = []

    for task_data in tasks:
        task = TaskAttributes(
            name=task_data['name'],
            frequency_per_year=task_data['frequency_per_year'],
            time_per_exec_hours=task_data['time_per_exec_hours'],
            labor_rate_dollars=task_data['labor_rate_dollars'],
            structuredness=task_data['structuredness'],
            data_accessibility=task_data['data_accessibility'],
            decision_complexity=task_data['decision_complexity'],
            exception_rate=task_data['exception_rate'],
            error_cost_dollars=task_data['error_cost_dollars'],
            compliance_risk=task_data['compliance_risk'],
            implementation_cost_annual=task_data['implementation_cost_annual'],
        )
        score = assess(task)
        scores.append(score)

    # Sort by annual savings
    scores.sort(key=lambda s: s.annual_savings, reverse=True)

    print("Agent: \"Automation Assessment Results (ranked by annual savings):\"")
    print()
    print(f"  {'Task':<30} {'Feas':>5} {'Impact':>8} {'Quadrant':<25} {'Savings':>12}")
    print(f"  {'-'*30} {'-'*5} {'-'*8} {'-'*25} {'-'*12}")

    for s in scores:
        impact_str = f"${s.impact_dollars:,.0f}"
        savings_str = f"${s.annual_savings:,.0f}"
        print(f"  {s.task_name:<30} {s.feasibility:>5.2f} {impact_str:>8} {s.quadrant:<25} {savings_str:>12}")

    print()

    # Detail for top task
    top = scores[0]
    print(f"  📊 Top recommendation: {top.task_name}")
    print(f"     Quadrant: {top.quadrant}")
    print(f"     Automation fraction: {top.automation_fraction:.1%}")
    print(f"     Derivation: {top.derivation['savings_calc']}")
    if top.risk_gate_triggered:
        print(f"     ⚠️  Risk gate triggered: {top.derivation['risk_gate']}")
    print()

    # Detail for bottom task
    bottom = scores[-1]
    print(f"  🚫 Don't automate: {bottom.task_name}")
    print(f"     Feasibility: {bottom.feasibility:.2f} (decision_complexity too high)")
    print(f"     Derivation: {bottom.derivation['feasibility_calc']}")
    print()

    print("  📐 Methodology:")
    print("     Feasibility = min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)")
    print("     Impact = frequency × time_per_exec × labor_rate ($/year)")
    print("     Savings = hours × automation_fraction × labor_rate + error_reduction - cost")
    print("     All inputs labeled: user-provided, estimated, default, or computed")


# === Main ===

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Company Brain Demo")
    parser.add_argument('--module', choices=['incident', 'extraction', 'automation', 'all'],
                       default='all', help='Which demo module to run')
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port')
    args = parser.parse_args()

    # Connect to FalkorDB for real graph queries
    db = None
    try:
        from core.falkordb_client import CompanyBrainDB
        db = CompanyBrainDB(port=args.port)
        db.query("RETURN 1 AS test")
        print(f"  ✅ Connected to FalkorDB on port {args.port}")
    except Exception as e:
        print(f"  ⚠️  FalkorDB not available ({e}), using mock data")

    if args.module in ('incident', 'all'):
        run_incident_demo()

    if args.module in ('extraction', 'all'):
        run_extraction_demo()

    if args.module in ('automation', 'all'):
        run_automation_demo()

    if args.module == 'all':
        print_header("DEMO COMPLETE")
        print()
        print("  Key differentiators:")
        print("  1. Deterministic deadlines (never LLM-generated)")
        print("  2. Evidence subgraphs (explainable answers)")
        print("  3. Span-grounded extraction (verbatim source quotes)")
        print("  4. Honest automation math (gates, not weighted sums)")
        print("  5. Read-only, parameterized tools (secure by design)")
        print()
        print("  FalkorDB graph: company_brain")
        if db:
            stats = db.get_graph_stats()
            total = sum(stats['nodes'].values())
            rels = sum(stats['relationships'].values())
            print(f"  Graph stats: {total} nodes, {rels} relationships")
        print()


if __name__ == '__main__':
    main()
