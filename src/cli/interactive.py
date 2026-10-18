"""Interactive CLI for Company Brain.

Judges/reviewers can type natural-language queries and get responses
backed by the FalkorDB Process Knowledge Graph. Every agent handler
queries FalkorDB for its core data — the graph shapes what the agent does.

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
from core.llm_client import llm
from demo.seed_data import get_playbook, DEMO_TASKS


def format_response(response: dict) -> str:
    """Format an agent response for display. Renders graph-powered responses."""
    lines = []

    # Show LLM summary if available
    if response.get('llm_summary'):
        lines.append(f"  {response['llm_summary']}")
        lines.append("")

    intent = response.get('intent', 'unknown')

    if intent == 'incident_response':
        lines.append(f" Playbook: {response.get('playbook_name', 'N/A')}")
        lines.append(f"   Source: {response.get('playbook_source', 'N/A')}")
        lines.append(f"   Detected: {response.get('detected_at', 'N/A')}")
        if response.get('data_source'):
            lines.append(f"   Data: {response['data_source']}")
        lines.append("")

        for step in response.get('steps', []):
            lines.append(f"  {step['deadline']}: {step['name']}")
            lines.append(f"     Contact: {step['contact']} ({step['contact_role']})")
            if step.get('legal_basis'):
                lines.append(f"     Legal basis: {step['legal_basis']}")
            lines.append("")

        # Similar incidents from vector search
        similar = response.get('similar_incidents', [])
        if similar:
            lines.append("  Similar incidents (vector search):")
            for s in similar:
                lines.append(f"    {s['company']} - {s['type']} ({s['severity']}) score={s['score']:.2f}")
            lines.append("")

        if response.get('disclaimer'):
            lines.append(f"  {response['disclaimer']}")

    elif intent == 'automation_assessment':
        scores = response.get('scores')
        if scores:
            lines.append("  Automation Assessment (graph-powered)")
            lines.append(f"  {response.get('data_source', '')}")
            lines.append("")
            lines.append(f"  {'Task':<28} {'Feas':>5} {'Impact':>10} {'Quadrant':<25} {'Savings':>12}")
            lines.append(f"  {'─'*28} {'─'*5} {'─'*10} {'─'*25} {'─'*12}")

            for s in scores:
                impact_str = f"${s['impact_dollars']:,.0f}"
                savings_str = f"${s['annual_savings']:,.0f}"
                lines.append(f"  {s['task_name']:<28} {s['feasibility']:>5.2f} {impact_str:>10} {s['quadrant']:<25} {savings_str:>12}")

            lines.append("")
            graph_ctx = response.get('graph_context', [])
            if graph_ctx:
                lines.append("  Graph context:")
                for ctx in graph_ctx:
                    regs = ', '.join(ctx['regulations']) if ctx['regulations'] else 'none'
                    lines.append(f"    {ctx['task_id']}: process={ctx['process']}, deps={ctx['downstream_deps']}, regs={regs}")
                lines.append("")

            lines.append("  Methodology: Feasibility = min(structuredness, data_access, 1-decision_complexity, 1-exception_rate)")
            lines.append("               Impact = frequency x time_per_exec x labor_rate ($/year)")
            lines.append("               Graph boost: +10% per downstream dependency")
        else:
            lines.append("  Automation Assessment")
            lines.append(f"  {response.get('response', '')}")

    elif intent == 'cascade_analysis':
        lines.append("  Cascade Analysis")
        if response.get('data_source'):
            lines.append(f"  {response.get('data_source')}")
        lines.append("")

        if response.get('available_vendors'):
            lines.append("  Available vendors:")
            for v in response.get('available_vendors'):
                lines.append(f"    {v['name']} ({v['entity_id']}) - risk: {v['risk_score']}")
            lines.append("")

        if response.get('blast_radius') is not None:
            lines.append(f"  Blast radius: {response['blast_radius']} entities affected")
            lines.append("")
            if response.get('affected_processes'):
                lines.append("  Processes affected:")
                for p in response['affected_processes']:
                    lines.append(f"    {p['name']}")
                lines.append("")
            if response.get('affected_tasks'):
                lines.append("  Tasks affected:")
                for t in response['affected_tasks']:
                    lines.append(f"    {t['name']}")
                lines.append("")
            if response.get('compliance_at_risk'):
                lines.append("  Compliance obligations at risk:")
                for c in response['compliance_at_risk']:
                    lines.append(f"    {c['entity']} -> {c['task']} -> {c['regulation']} ({c['jurisdiction']})")
                lines.append("")
        elif response.get('response'):
            lines.append(f"  {response['response']}")

    elif intent == 'compliance_check':
        lines.append("  Compliance Check")
        if response.get('data_source'):
            lines.append(f"  {response.get('data_source')}")
        lines.append("")

        if response.get('regulations'):
            lines.append("  Regulations in graph:")
            for r in response['regulations']:
                lines.append(f"    {r['name']} ({r['jurisdiction']})")
            lines.append("")

        if response.get('compliance_gaps'):
            lines.append(f"  Compliance gaps ({len(response['compliance_gaps'])}):")
            for g in response['compliance_gaps']:
                lines.append(f"    {g['name']} (risk: {g['risk']}) - no compliance edge in graph")
            lines.append("")

        if response.get('india_details'):
            lines.append("  India framework:")
            for d in response['india_details']:
                lines.append(f"    {d['name']}: {d['deadline']} | {d['applies_to']} | {d['penalty']}")
            lines.append("")

    elif intent == 'process_extraction':
        lines.append("  Process Extraction")
        if response.get('data_source'):
            lines.append(f"  {response.get('data_source')}")
        lines.append("")

        if response.get('documents'):
            lines.append("  Documents in graph:")
            for d in response['documents']:
                lines.append(f"    {d['title']} ({d['type']})")
            lines.append("")

        if response.get('extracted_processes'):
            for proc in response['extracted_processes']:
                status = "valid" if proc['valid'] else "HAS CYCLES"
                lines.append(f"  Process: {proc['process']} - {proc['task_count']} tasks, {proc['dependency_count']} deps [{status}]")
            lines.append("")

        if response.get('pipeline'):
            lines.append(f"  Pipeline: {response['pipeline']}")

    else:
        lines.append("  Company Brain")
        lines.append(f"  {response.get('response', '')}")
        if response.get('llm_generated'):
            lines.append("  [Generated by LongCat LLM]")
        if response.get('available_intents'):
            lines.append(f"  Available: {', '.join(response['available_intents'])}")

    return "\n".join(lines)


def run_interactive(agent: CompanyBrainAgent):
    """Run the interactive CLI loop."""
    print()
    print("=" * 70)
    print("  COMPANY BRAIN - FalkorDB Hackathon 2026")
    print("  Process Knowledge Graph Agent")
    print("=" * 70)
    print()
    llm_status = "LongCat LLM" if llm.available else "keywords only (set LONGCAT_API_KEY to enable LLM)"
    print(f"  LLM: {llm_status}")
    if agent.db:
        print(f"  FalkorDB: connected (graph queries enabled)")
    else:
        print(f"  FalkorDB: NOT connected (using fallback data)")
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

        if query.lower() == '/llm':
            if llm.available:
                test_query = "data breach detected in production"
                print(f"\n  LLM test - classifying: '{test_query}'")
                intent = llm.classify_intent(test_query)
                print(f"  Intent: {intent}")
                print(f"  Model: {llm.model}")
            else:
                print("\n  LLM not available. Set LONGCAT_API_KEY environment variable.")
            print()
            continue

        if query.lower() == '/help':
            print()
            print("  Available query types:")
            print("    Incident: 'data breach detected', 'ransomware attack'")
            print("    Automation: 'what can we automate?', 'automation assessment'")
            print("    Process: 'extract process from SOP', 'upload workflow'")
            print("    Cascade: 'what if vendor X goes down?', 'blast radius'")
            print("    Compliance: 'GDPR deadlines', 'regulatory requirements'")
            print()
            print("  Commands: /help, /demo, /stats, /vendors, /incidents, /search <term>, /similar <text>, /cascade <vendor_id>, /quit")
            print()
            print("  Search commands:")
            print("    /search <term>       - Full-text search (RediSearch TF-IDF)")
            print("    /similar <text>      - Vector similarity search (HNSW, 384-dim)")
            print("    /cascade <vendor_id> - Blast radius analysis")
            print()
            continue

        if query.lower() == '/demo':
            from demo.run_demo import run_incident_demo, run_extraction_demo, run_automation_demo
            run_incident_demo(db=agent.db)
            run_extraction_demo(db=agent.db)
            run_automation_demo(db=agent.db)
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
                print(f"  Could not fetch stats: {e}")
            continue

        if query.lower() == '/vendors':
            try:
                vendors = agent.db.get_all_vendors()
                print()
                print("  Vendors:")
                for v in vendors:
                    print(f"    {v[1]} ({v[2]}) - risk: {v[3]}")
                print()
            except Exception as e:
                print(f"  Could not fetch vendors: {e}")
            continue

        if query.lower() == '/incidents':
            try:
                incidents = agent.db.get_all_incidents()
                print()
                print("  Incidents:")
                for i in incidents:
                    print(f"    {i[0]}: {i[1]} ({i[2]}) - {i[3]}")
                print()
            except Exception as e:
                print(f"  Could not fetch incidents: {e}")
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
                    print(f"  Search error: {e}")
            continue

        if query.lower().startswith('/similar '):
            term = query[9:].strip()
            if term:
                try:
                    from core.embeddings import embed_text
                    query_vec = embed_text(term)
                    result = agent.db.graph.query(
                        'CALL db.idx.vector.queryNodes($label, $attr, $k, vecf32($qv)) YIELD node, score RETURN node.incident_id, node.company_name, node.type, node.severity, score ORDER BY score DESC LIMIT 5',
                        {'label': 'Incident', 'attr': 'embedding', 'k': 5, 'qv': query_vec}
                    )
                    print()
                    print(f"  Similar incidents: '{term}'")
                    for row in (result.result_set or []):
                        name = row[1] if row[1] else row[0]
                        print(f"    {name} - {row[2]} ({row[3]}) score={row[4]:.2f}")
                    print()
                except Exception as e:
                    print(f"  Vector search error: {e}")
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
                    print(f"  Cascade error: {e}")
            continue

        # Use the agent's public handle() method - it queries FalkorDB
        response = agent.handle(query)
        intent = response.get('intent', 'unknown')

        print(f"  [Intent: {intent}]")
        if response.get('data_source'):
            print(f"  [Data: {response['data_source']}]")
        print()
        print(format_response(response))
        print()


def main():
    parser = argparse.ArgumentParser(description="Company Brain Interactive CLI")
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port')
    parser.add_argument('--mock', action='store_true', help='Use mock data (no FalkorDB)')
    args = parser.parse_args()

    # Load playbook data for the agent (fallback)
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
            db.query("RETURN 1 AS test")
            agent = CompanyBrainAgent(db=db, playbook_data=playbook_data)
            print(f"  Connected to FalkorDB on port {args.port}")
        except Exception as e:
            print(f"  Could not connect to FalkorDB: {e}")
            print("  Falling back to mock mode")
            agent = CompanyBrainAgent(playbook_data=playbook_data)

    run_interactive(agent)


if __name__ == '__main__':
    main()
