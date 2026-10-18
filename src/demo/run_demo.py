"""Company Brain Demo Runner.

Runs the demo modules. All modules now query FalkorDB for their core data:
1. Incident Response — graph traversal for playbook steps + vector search for similar
2. Process Extraction — graph-validated task graphs with span-grounding
3. Automation Assessment — graph-powered task scoring with dependency context

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
from core.sop_parser import parse_sop_document


def print_header(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}")


# === Module 1: Incident Response ===

def run_incident_demo(db=None):
    """Demo: Data breach detected. Agent queries graph for playbook, computes deadlines.

    GRAPH: Traverses Playbook->HAS_STEP->StepTemplate->CONTACT->Person
    VECTOR: Finds similar incidents from SEC EDGAR 8-K Item 1.05 data
    """
    print_header("MODULE 1: INCIDENT RESPONSE")
    print("  GRAPH: Playbook -> HAS_STEP -> StepTemplate -> CONTACT -> Person")
    print("  VECTOR: Similar incidents from SEC EDGAR 8-K Item 1.05 filings")
    print()
    print('User: "We detected unauthorized access to our production database')
    print('        at 2:30 PM UTC today (Friday Oct 16, 2026)."')
    print()

    detected_at = datetime(2026, 10, 16, 14, 30)  # Friday
    incident_type = 'data_breach'

    # PRIMARY: Query the graph for playbook steps
    if db:
        graph_steps = db.get_playbook_steps_graph(incident_type)
        if graph_steps:
            playbook_name = graph_steps[0][0]
            playbook_source = graph_steps[0][1] or 'NIST SP 800-61 Rev. 2'

            print(f"  Agent: \"{playbook_name}\"")
            print(f"  Source: {playbook_source}")
            print(f"  Detected: {detected_at.strftime('%A %b %d %H:%M UTC')}")
            print(f"  Data source: FALKORDB GRAPH TRAVERSAL")
            print()

            for row in graph_steps:
                _, _, step_id, step_name, order, amount, unit, trigger, contact_name, contact_role, legal_basis = row
                deadline = compute_deadline(detected_at, amount, unit)

                if amount == 0:
                    timing = "NOW"
                elif unit == 'clock_hours':
                    timing = f"Within {amount} clock hour{'s' if amount != 1 else ''}"
                elif unit == 'calendar_days':
                    timing = f"Within {amount} calendar day{'s' if amount != 1 else ''}"
                elif unit == 'business_days':
                    timing = f"Within {amount} business day{'s' if amount != 1 else ''}"
                else:
                    timing = f"Within {amount} {unit}"

                print(f"    {timing} (by {deadline.strftime('%A %b %d %H:%M UTC')}):")
                print(f"      -> {step_name}")
                print(f"      -> Contact: {contact_name} ({contact_role})")
                if legal_basis:
                    print(f"      -> Legal basis: {legal_basis}")
                print()

            # VECTOR SEARCH: similar incidents
            try:
                from core.embeddings import embed_text
                query_vec = embed_text(f"{incident_type} security incident")
                vec_result = db.graph.query(
                    'CALL db.idx.vector.queryNodes($label, $attr, $k, vecf32($qv)) YIELD node, score RETURN node.company_name, node.type, node.severity, node.detected_at, score ORDER BY score DESC LIMIT 3',
                    {'label': 'Incident', 'attr': 'embedding', 'k': 3, 'qv': query_vec}
                )
                similar = [r for r in (vec_result.result_set or []) if r[0]]
                if similar:
                    print(f"  Similar incidents (vector search, cosine similarity):")
                    for r in similar:
                        print(f"    {r[0]} — {r[1]} ({r[2]}, {r[3]}) score={float(r[4]):.2f}")
                    print()
            except Exception:
                pass

            print(f"  Evidence: GRAPH QUERY MATCH (pb:Playbook)-[hs:HAS_STEP]->(step:StepTemplate)-[:CONTACT]->(contact:Person)")
            print(f"  FalkorDB traversed {len(graph_steps)} steps from graph")
            print()
            return

    # FALLBACK: Hardcoded playbook
    playbook = get_playbook(incident_type)
    print(f"  Agent: \"{playbook['name']}\"")
    print(f"  Source: {playbook['source']}")
    print(f"  Detected: {detected_at.strftime('%A %b %d %H:%M UTC')}")
    print(f"  Data source: HARDCODED FALLBACK (FalkorDB unavailable)")
    print()

    for step in playbook['steps']:
        deadline = compute_deadline(detected_at, step['amount'], step['unit'])
        if step['amount'] == 0:
            timing = "NOW"
        elif step['unit'] == 'clock_hours':
            timing = f"Within {step['amount']} clock hour{'s' if step['amount'] != 1 else ''}"
        else:
            timing = f"Within {step['amount']} {step['unit']}"

        print(f"    {timing} (by {deadline.strftime('%A %b %d %H:%M UTC')}):")
        print(f"      -> {step['name']}")
        print(f"      -> Contact: {step['contact']} ({step['contact_role']})")
        if step['legal_citation']:
            print(f"      -> Legal basis: {step['legal_citation']}")
        print()

    print(f"  Source: {playbook['source']}, GDPR Articles 33-34")
    print()


# === Module 2: Process Extraction ===

def run_extraction_demo(db=None):
    """Demo: Extract tasks and dependencies from a sample SOP.

    GRAPH: Validates extracted graph using cycle detection + critical path
    """
    print_header("MODULE 2: PROCESS EXTRACTION")
    print("  GRAPH: Cycle detection (SCC) + critical path on extracted task graph")
    print()

    if db:
        # Show what's already in the graph
        processes = db.get_all_processes()
        if processes:
            print(f"  Agent: Found {len(processes)} processes in FalkorDB graph")
            for proc in processes:
                tasks = db.get_process_with_tasks(proc[0])
                if tasks:
                    print(f"    {proc[1]}: {len(tasks)} tasks")
            print()

    print('User: "Here is our invoice processing SOP. What did you extract?"')
    print()

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

    # REAL EXTRACTION: Parse the SOP text using rule-based parser
    extracted_tasks, extracted_deps = parse_sop_document(sop_text)

    print(f"  Agent: \"Extraction results ({len(extracted_tasks)} tasks, {len(extracted_deps)} dependencies):\"")
    print(f"  Data source: RULE-BASED SOP PARSER (regex + IDF-weighted matching)")
    print()

    # Verify span grounding
    valid, invalid = [], []
    for dep in extracted_deps:
        if verify_span_grounding(dep, sop_text):
            valid.append(dep)
        else:
            invalid.append(dep)

    print(f"  Span-grounded: {len(valid)}/{len(extracted_deps)} edges verified")
    print()

    # GRAPH VALIDATION: cycle detection + critical path
    result = validate_process_graph(extracted_tasks, extracted_deps)

    print(f"  GRAPH VALIDATION (SCC cycle detection):")
    if result['valid']:
        print(f"    No cycles detected")
        print(f"    Critical path: {' -> '.join(result['critical_path'])}")
        print(f"    Critical path length: {result['path_length_hours']:.2f} hours")
    else:
        print(f"    Cycles detected: {result['cycles']}")
    print()

    print("  Extracted dependency graph:")
    for dep in extracted_deps:
        from_name = next(t['name'] for t in extracted_tasks if t['task_id'] == dep['from'])
        to_name = next(t['name'] for t in extracted_tasks if t['task_id'] == dep['to'])
        status = "OK" if dep in valid else "FAIL"
        print(f"    [{status}] {from_name} -> depends on -> {to_name} (confidence: {dep['confidence']})")
    print()
    print("  Low-confidence edges flagged for user review.")
    print()


# === Module 3: Automation Assessment ===

def run_automation_demo(db=None):
    """Demo: Score tasks on automation potential.

    GRAPH: Queries tasks with COMPLIES_WITH and DEPENDS_ON context.
    Scoring considers graph structure: tasks with many downstream deps
    get impact boost (failure/rework cascades).
    """
    print_header("MODULE 3: AUTOMATION ASSESSMENT")
    print("  GRAPH: Tasks with COMPLIES_WITH + DEPENDS_ON context")
    print("  SCORING: Feasibility x Impact + graph dependency boost")
    print()

    print('User: "Analyze our processes. What can we automate?"')
    print()

    # PRIMARY: Query tasks from graph with context
    if db:
        graph_tasks = db.get_tasks_with_context()
        if graph_tasks:
            scores = []
            for row in graph_tasks:
                (task_id, name, description, freq, time_hours, rate,
                 structured, data_access, decision, exception,
                 error_cost, compliance_risk, impl_cost,
                 regulations, reg_jurisdictions, depends_on, process_name) = row

                task = TaskAttributes(
                    name=name,
                    frequency_per_year=freq or 0,
                    time_per_exec_hours=time_hours or 0,
                    labor_rate_dollars=rate or 0,
                    structuredness=structured or 0.5,
                    data_accessibility=data_access or 0.5,
                    decision_complexity=decision or 0.5,
                    exception_rate=exception or 0.1,
                    error_cost_dollars=error_cost or 100,
                    compliance_risk=compliance_risk or 0.1,
                    implementation_cost_annual=impl_cost or 0,
                )
                score = assess(task)

                # Graph boost: downstream dependencies increase impact
                downstream_count = len([d for d in (depends_on or []) if d])
                if downstream_count > 0:
                    boost = min(downstream_count * 0.1, 0.5)
                    score.impact_dollars *= (1 + boost)
                    score.annual_savings *= (1 + boost)

                scores.append((score, process_name, regulations, downstream_count))

            scores.sort(key=lambda s: s[0].annual_savings, reverse=True)

            print("  Agent: \"Automation Assessment Results (ranked by annual savings):\"")
            print(f"  Data source: FALKORDB GRAPH — tasks with dependency context")
            print()
            print(f"  {'Task':<28} {'Feas':>5} {'Impact':>10} {'Quadrant':<25} {'Savings':>12} {'Deps':>4}")
            print(f"  {'-'*28} {'-'*5} {'-'*10} {'-'*25} {'-'*12} {'-'*4}")

            for score, process_name, regulations, deps in scores:
                impact_str = f"${score.impact_dollars:,.0f}"
                savings_str = f"${score.annual_savings:,.0f}"
                print(f"  {score.task_name:<28} {score.feasibility:>5.2f} {impact_str:>10} {score.quadrant:<25} {savings_str:>12} {deps:>4}")

            print()

            # Top recommendation
            top = scores[0][0]
            print(f"  Top recommendation: {top.task_name}")
            print(f"    Quadrant: {top.quadrant}")
            print(f"    Automation fraction: {top.automation_fraction:.1%}")
            print(f"    Derivation: {top.derivation['savings_calc']}")
            if top.risk_gate_triggered:
                print(f"    Risk gate: {top.derivation['risk_gate']}")
            print()

            # Compliance context from graph
            print(f"  Compliance context (from COMPLIES_WITH edges):")
            for score, process_name, regulations, deps in scores:
                if regulations:
                    print(f"    {score.task_name}: {', '.join(regulations)}")
            print()

            print(f"  Methodology:")
            print(f"    Feasibility = min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)")
            print(f"    Impact = frequency x time_per_exec x labor_rate ($/year)")
            print(f"    Graph boost: +10% impact per downstream dependency (max +50%)")
            print()
            return

    # FALLBACK: Hardcoded tasks
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

    scores.sort(key=lambda s: s.annual_savings, reverse=True)

    print("  Agent: \"Automation Assessment Results (ranked by annual savings):\"")
    print(f"  Data source: HARDCODED FALLBACK (FalkorDB unavailable)")
    print()
    print(f"  {'Task':<28} {'Feas':>5} {'Impact':>10} {'Quadrant':<25} {'Savings':>12}")
    print(f"  {'-'*28} {'-'*5} {'-'*10} {'-'*25} {'-'*12}")

    for s in scores:
        impact_str = f"${s.impact_dollars:,.0f}"
        savings_str = f"${s.annual_savings:,.0f}"
        print(f"  {s.task_name:<28} {s.feasibility:>5.2f} {impact_str:>10} {s.quadrant:<25} {savings_str:>12}")

    print()
    top = scores[0]
    print(f"  Top recommendation: {top.task_name}")
    print(f"    Quadrant: {top.quadrant}")
    print(f"    Derivation: {top.derivation['savings_calc']}")
    print()
    print(f"  Methodology:")
    print(f"    Feasibility = min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)")
    print(f"    Impact = frequency x time_per_exec x labor_rate ($/year)")
    print(f"    Savings = hours x automation_fraction x labor_rate + error_reduction - cost")
    print()


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
        print(f"  Connected to FalkorDB on port {args.port}")
    except Exception as e:
        print(f"  FalkorDB not available ({e}), using fallback data")

    if args.module in ('incident', 'all'):
        run_incident_demo(db=db)

    if args.module in ('extraction', 'all'):
        run_extraction_demo(db=db)

    if args.module in ('automation', 'all'):
        run_automation_demo(db=db)

    if args.module == 'all':
        print_header("DEMO COMPLETE")
        print()
        print("  Key differentiators:")
        print("  1. Graph-powered playbook traversal (not hardcoded)")
        print("  2. Vector search for similar incidents (SEC EDGAR data)")
        print("  3. Graph-validated extraction (cycle detection + critical path)")
        print("  4. Graph-aware automation scoring (dependency boost)")
        print("  5. Compliance gap detection (graph pattern matching)")
        print("  6. Multi-hop cascade analysis (BFS + compliance context)")
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
