"""Cascade Analysis Demo — blast radius + compliance risk propagation.

Shows how the agent traces the impact of a vendor failure through the
Process Knowledge Graph, combining multi-hop BFS with compliance context.

MODULE 4: Uses FalkorDB for:
1. Multi-hop BFS cascade (Vendor → Process → Task → downstream Tasks)
2. Vendor risk propagation (Vendor → Task → Regulation)
3. Compliance impact (which obligations are at risk)
4. Graph-powered critical path analysis

Usage:
    uv run python -m demo.cascade_demo
"""

import sys; sys.path.insert(0, 'src')


def run_cascade_demo():
    """Run the cascade analysis demo."""
    from core.falkordb_client import CompanyBrainDB

    print()
    print("=" * 70)
    print("  MODULE 4: CASCADE ANALYSIS (Blast Radius + Compliance)")
    print("  GRAPH: Multi-hop BFS + compliance risk propagation")
    print("=" * 70)
    print()

    # Connect to FalkorDB
    try:
        db = CompanyBrainDB(port=6380)
        db.query("RETURN 1 AS test")
    except Exception as e:
        print(f"  Could not connect to FalkorDB: {e}")
        print("  Run: docker start falkordb-hackathon")
        return

    # ====================================================================
    # EXAMPLE 1: CloudHost cascade
    # ====================================================================
    print('User: "What happens if CloudHost goes down?"')
    print()

    results = db.get_cascade_impact('v_cloudhost')

    if results:
        processes = [r for r in results if 'Process' in r[0]]
        tasks = [r for r in results if 'Task' in r[0]]

        print(f"  Agent: CloudHost failure blast radius — {len(results)} entities affected")
        print()
        print(f"  GRAPH TRAVERSAL (3-hop BFS):")
        print(f"    Hop 1: Vendor -> PROVIDES_SERVICE_FOR -> Process/Task")
        print(f"    Hop 2: Process -> HAS_TASK -> Task")
        print(f"    Hop 3: Task -> DEPENDS_ON -> Task")
        print()

        if processes:
            print(f"  Processes affected ({len(processes)}):")
            for r in processes:
                print(f"    {r[2]}")
            print()

        if tasks:
            print(f"  Tasks affected ({len(tasks)}):")
            for r in tasks:
                print(f"    {r[2]}")
            print()
    else:
        print("  No cascade data found. Run seed_graph.py first.")
        print()

    # ====================================================================
    # EXAMPLE 2: Risk propagation with compliance context
    # ====================================================================
    print('  --- Compliance Risk Propagation ---')
    print()

    risk_data = db.get_vendor_risk_propagation('v_cloudhost')
    if risk_data:
        compliance_items = [r for r in risk_data if r[3]]  # has regulation
        if compliance_items:
            print(f"  Compliance obligations at risk from CloudHost failure:")
            for r in compliance_items:
                entity_name, entity_type, task_name, regulation, jurisdiction, risk = r
                print(f"    {entity_name} -> {task_name} -> {regulation} ({jurisdiction})")
            print()

    # ====================================================================
    # EXAMPLE 3: CRM vendor cascade
    # ====================================================================
    print('User: "What about CRMPro?"')
    print()

    results2 = db.get_cascade_impact('v_crm_vendor')
    if results2:
        print(f"  Agent: CRMPro failure impact — {len(results2)} entities")
        for r in results2:
            print(f"    {r[2]} ({r[0][0]})")
        print()

    # ====================================================================
    # EXAMPLE 4: Process critical path (graph algorithm)
    # ====================================================================
    print('  --- Process Critical Path (Graph Algorithm) ---')
    print()

    critical = db.get_process_critical_path('proc_finance')
    if critical:
        print(f"  Finance process critical path:")
        for row in critical:
            task_id, task_name, time_hours, depth, chain = row
            chain_str = ' -> '.join(chain[:5]) if chain else 'N/A'
            print(f"    {task_name}: {time_hours}h, depth={depth}, chain=[{chain_str}]")
        print()

    # ====================================================================
    # SUMMARY
    # ====================================================================
    print("  Evidence subgraph:")
    print("    Vendor -> PROVIDES_SERVICE_FOR -> Process -> HAS_TASK -> Task")
    print("    Task -> DEPENDS_ON -> Task (downstream)")
    print("    Task -> COMPLIES_WITH -> Regulation (compliance at risk)")
    print()

    # Show all vendors
    vendors = db.get_all_vendors()
    if vendors:
        print("  All vendors in graph:")
        for v in vendors:
            print(f"    {v[1]} (risk: {v[3]}, id: {v[0]})")
        print()

    print("  Cascade analysis shows potential impact.")
    print("  Actual business impact depends on SLA terms and failover capabilities.")
    print()


if __name__ == '__main__':
    run_cascade_demo()
