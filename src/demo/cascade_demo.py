"""Cascade Analysis Demo — blast radius / cross-department impact.

Shows how the agent traces the impact of a vendor failure or task delay
through the Process Knowledge Graph.

Usage:
    uv run python -m demo.cascade_demo
"""

import sys; sys.path.insert(0, 'src')

from demo.seed_data import get_demo_vendors


def run_cascade_demo():
    """Run the cascade analysis demo."""
    from core.falkordb_client import CompanyBrainDB

    print()
    print("=" * 70)
    print("  🔗 MODULE 4: CASCADE ANALYSIS (Blast Radius)")
    print("=" * 70)
    print()

    # Connect to FalkorDB
    try:
        db = CompanyBrainDB(port=6380)
        db.query("RETURN 1 AS test")
    except Exception as e:
        print(f"  ⚠️  Could not connect to FalkorDB: {e}")
        print("  Run: docker start falkordb-hackathon")
        return

    print('User: "What happens if CloudHost goes down?"')
    print()

    # Query cascade
    results = db.get_cascade_impact('v_cloudhost')

    if results:
        print("Agent: \"CloudHost failure impact — 5 entities affected:\"")
        print()

        processes = [r for r in results if r[0] == ['Process']]
        tasks = [r for r in results if r[0] == ['Task']]

        if processes:
            print("  📂 Processes affected:")
            for r in processes:
                print(f"     • {r[2]}")
            print()

        if tasks:
            print("  📋 Tasks affected:")
            for r in tasks:
                print(f"     • {r[2]}")
            print()

        print(f"  💥 Total blast radius: {len(results)} entities")
        print()
    else:
        print("  No cascade data found. Run seed_graph.py first.")
        print()

    # Second example: CRM vendor
    print('User: "What about CRMPro?"')
    print()

    results2 = db.get_cascade_impact('v_crm_vendor')

    if results2:
        print("Agent: \"CRMPro failure impact — 1 entity affected:\"")
        print()
        for r in results2:
            print(f"  📋 {r[2]} (Task)")
        print()
    else:
        print("  No cascade data found.")
        print()

    # Show evidence path
    print("  📊 Evidence subgraph:")
    print("    Vendor → PROVIDES_SERVICE_FOR → Process → HAS_TASK → Task")
    print("    Vendor → PROVIDES_SERVICE_FOR → Task")
    print()

    # Show all vendors
    vendors = db.get_all_vendors()
    if vendors:
        print("  All vendors in graph:")
        for v in vendors:
            print(f"    • {v[1]} (risk: {v[3]})")
        print()

    print("  ⚠️  Cascade analysis shows potential impact.")
    print("  Actual business impact depends on SLA terms and failover capabilities.")
    print()


if __name__ == '__main__':
    run_cascade_demo()
