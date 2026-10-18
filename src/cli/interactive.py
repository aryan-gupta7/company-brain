"""Interactive CLI for Company Brain.

Judges/reviewers can type natural-language queries and get responses
backed by the FalkorDB Process Knowledge Graph.

Usage:
    uv run python -m cli.interactive
    uv run python -m cli.interactive --port 6380
    uv run python -m cli.interactive --mock  # Use mock data (no FalkorDB)
"""

import sys; sys.path.insert(0, 'src')

import argparse
from datetime import datetime
from agent.agent import classify_intent, CompanyBrainAgent
from core.deadline_calculator import compute_deadline
from core.automation_scoring import assess, TaskAttributes
from core.graph_utils import validate_process_graph, verify_span_grounding
from demo.seed_data import get_playbook, DEMO_TASKS


def format_response(response: dict) -> str:
    """Format an agent response for display."""
    lines = []
    intent = response.get('intent', 'unknown')

    if intent == 'incident_response':
        lines.append(f"📋 Playbook: {response.get('playbook_name', 'N/A')}")
        lines.append(f"   Source: {response.get('playbook_source', 'N/A')}")
        lines.append(f"   Detected: {response.get('detected_at', 'N/A')}")
        lines.append("")

        for step in response.get('steps', []):
            lines.append(f"  ⏱️  {step['deadline']}: {step['name']}")
            lines.append(f"     Contact: {step['contact']} ({step['contact_role']})")
            if step.get('legal_basis'):
                lines.append(f"     Legal basis: {step['legal_basis']}")
            lines.append("")

        if response.get('disclaimer'):
            lines.append(f"  {response['disclaimer']}")

    elif intent == 'automation_assessment':
        lines.append("📊 Automation Assessment")
        lines.append("")
        tasks = DEMO_TASKS
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
            scores.append(assess(task))

        scores.sort(key=lambda s: s.annual_savings, reverse=True)

        lines.append(f"  {'Task':<30} {'Feas':>5} {'Impact':>10} {'Quadrant':<25} {'Savings':>12}")
        lines.append(f"  {'─'*30} {'─'*5} {'─'*10} {'─'*25} {'─'*12}")

        for s in scores:
            impact_str = f"${s.impact_dollars:,.0f}"
            savings_str = f"${s.annual_savings:,.0f}"
            lines.append(f"  {s.task_name:<30} {s.feasibility:>5.2f} {impact_str:>10} {s.quadrant:<25} {savings_str:>12}")

        lines.append("")
        lines.append("  Methodology: Feasibility = min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)")
        lines.append("               Impact = frequency × time_per_exec × labor_rate ($/year)")

    elif intent == 'cascade_analysis':
        lines.append("🔗 Cascade Analysis")
        lines.append("   " + response.get('response', ''))

    elif intent == 'compliance_check':
        lines.append("⚖️  Compliance Check")
        lines.append("   " + response.get('response', ''))
        if response.get('frameworks'):
            lines.append(f"   Frameworks: {', '.join(response['frameworks'])}")

    elif intent == 'process_extraction':
        lines.append("📄 Process Extraction")
        lines.append("   " + response.get('response', ''))
        if response.get('pipeline'):
            lines.append(f"   Pipeline: {response['pipeline']}")

    else:
        lines.append("🤖 Company Brain")
        lines.append("   " + response.get('response', ''))
        if response.get('available_intents'):
            lines.append(f"   Available: {', '.join(response['available_intents'])}")

    return "\n".join(lines)


def run_interactive(agent: CompanyBrainAgent):
    """Run the interactive CLI loop."""
    print()
    print("=" * 70)
    print("  🧠 COMPANY BRAIN — FalkorDB Hackathon 2026")
    print("  Process Knowledge Graph Agent")
    print("=" * 70)
    print()
    print("  Ask about: incidents, automation, processes, compliance, cascades")
    print("  Commands: /help, /demo, /stats, /vendors, /incidents, /search <term>, /similar <text>, /cascade <vendor_id>, /quit")
    print()

    while True:
        try:
            query = input("  You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  Goodbye!")
            break

        if not query:
            continue

        if query.lower() in ('/quit', '/exit', 'quit', 'exit'):
            print("  Goodbye!")
            break

        if query.lower() == '/help':
            print()
            print("  Available query types:")
            print("    • Incident: 'data breach detected', 'ransomware attack'")
            print("    • Automation: 'what can we automate?', 'automation assessment'")
            print("    • Process: 'extract process from SOP', 'upload workflow'")
            print("    • Cascade: 'what if vendor X goes down?', 'blast radius'")
            print("    • Compliance: 'GDPR deadlines', 'regulatory requirements'")
            print()
            print("  Commands: /help, /demo, /stats, /vendors, /incidents, /search <term>, /similar <text>, /cascade <vendor_id>, /quit")
            print()
            print("  New features:")
            print("    /search <term>       — Full-text search (RediSearch TF-IDF)")
            print("    /similar <text>      — Vector similarity search (HNSW, 384-dim)")
            print("    /cascade <vendor_id> — Blast radius analysis")
            print()
            print("  Examples:")
            print("    /similar ransomware attack")
            print("    /cascade v_cloudhost")
            print("    /search invoice")
            continue

        if query.lower() == '/demo':
            from demo.run_demo import run_incident_demo, run_extraction_demo, run_automation_demo
            run_incident_demo()
            run_extraction_demo()
            run_automation_demo()
            continue

        if query.lower() == '/stats':
            try:
                stats = agent.db.get_graph_stats()
                print()
                print("  Graph Statistics:")
                total = 0
                for label, count in stats['nodes'].items():
                    if count > 0:
                        print(f"    {label}: {count}")
                        total += count
                print(f"    Total nodes: {total}")
                print(f"    Total relationships: {sum(stats['relationships'].values())}")
                print()
            except Exception as e:
                print(f"  ⚠️  Could not fetch stats: {e}")
            continue

        if query.lower() == '/vendors':
            try:
                vendors = agent.db.get_all_vendors()
                print()
                print("  Vendors:")
                for v in vendors:
                    print(f"    {v[1]} ({v[2]}) — risk: {v[3]}")
                print()
            except Exception as e:
                print(f"  ⚠️  Could not fetch vendors: {e}")
            continue

        if query.lower() == '/incidents':
            try:
                incidents = agent.db.get_all_incidents()
                print()
                print("  Incidents:")
                for i in incidents:
                    print(f"    {i[0]}: {i[1]} ({i[2]}) — {i[3]}")
                print()
            except Exception as e:
                print(f"  ⚠️  Could not fetch incidents: {e}")
            continue

        if query.lower().startswith('/search '):
            term = query[8:].strip()
            if term:
                try:
                    results = agent.db.full_text_search_tasks(term)
                    print()
                    print(f"  Full-text search: '{term}'")
                    for r in results:
                        print(f"    {r[0]}: {r[1]} (score: {r[3]})")
                    print()
                except Exception as e:
                    print(f"  ⚠️  Search error: {e}")
            continue

        if query.lower().startswith('/similar '):
            term = query[9:].strip()
            if term:
                try:
                    from core.embeddings import embed_text
                    query_vec = embed_text(term)
                    result = agent.db.graph.query(
                        'CALL db.idx.vector.queryNodes(\$label, \$attr, \$k, vecf32(\$qv)) YIELD node, score RETURN node.incident_id, node.company_name, node.type, node.severity, score ORDER BY score DESC LIMIT 5',
                        {'label': 'Incident', 'attr': 'embedding', 'k': 5, 'qv': query_vec}
                    )
                    print()
                    print(f"  Similar incidents: '{term}'")
                    for row in (result.result_set or []):
                        name = row[1] if row[1] else row[0]
                        print(f"    {name} — {row[2]} ({row[3]}) score={row[4]:.2f}")
                    print()
                except Exception as e:
                    print(f"  ⚠️  Vector search error: {e}")
            continue

        if query.lower().startswith('/cascade '):
            vendor_id = query[9:].strip()
            if vendor_id:
                try:
                    results = agent.db.get_cascade_impact(vendor_id)
                    print()
                    print(f"  Cascade impact: {vendor_id}")
                    for r in results:
                        print(f"    {r[0]}: {r[1]} - {r[2]}")
                    print()
                except Exception as e:
                    print(f"  ⚠️  Cascade error: {e}")
            continue

        # Classify and handle
        intent = classify_intent(query)
        print(f"  [Intent: {intent}]")

        if intent == 'incident_response':
            response = agent._handle_incident(query)
        elif intent == 'automation_assessment':
            response = agent._handle_automation(query)
        elif intent == 'process_extraction':
            response = agent._handle_extraction(query)
        elif intent == 'cascade_analysis':
            response = agent._handle_cascade(query)
        elif intent == 'compliance_check':
            response = agent._handle_compliance(query)
        else:
            response = agent._handle_general(query)

        print()
        print(format_response(response))
        print()


def main():
    parser = argparse.ArgumentParser(description="Company Brain Interactive CLI")
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port')
    parser.add_argument('--mock', action='store_true', help='Use mock data (no FalkorDB)')
    args = parser.parse_args()

    # Load playbook data for the agent
    playbook_data = {
        'data_breach': get_playbook('data_breach'),
        'ransomware': get_playbook('ransomware'),
    }

    if args.mock:
        agent = CompanyBrainAgent(playbook_data=playbook_data)
        print("  Running in MOCK mode (no FalkorDB connection)")
    else:
        try:
            from core.falkordb_client import CompanyBrainDB
            db = CompanyBrainDB(port=args.port)
            # Verify connection
            db.query("RETURN 1 AS test")
            agent = CompanyBrainAgent(playbook_data=playbook_data)
            agent.db = db  # Attach DB for /stats command
            print(f"  Connected to FalkorDB on port {args.port}")
        except Exception as e:
            print(f"  ⚠️  Could not connect to FalkorDB: {e}")
            print("  Falling back to mock mode")
            agent = CompanyBrainAgent(playbook_data=playbook_data)

    run_interactive(agent)


if __name__ == '__main__':
    main()
