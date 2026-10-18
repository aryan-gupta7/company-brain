"""Seed the FalkorDB graph with curated playbooks, tasks, and regulations.

Connects to FalkorDB running on port 6380 and populates the company_brain graph.

Usage:
    uv run python -m demo.seed_graph
    uv run python -m demo.seed_graph --port 6380
    uv run python -m demo.seed_graph --reset  # Delete all data first
"""

import sys; sys.path.insert(0, 'src')

import argparse
from demo.seed_data import (
    DATA_BREACH_PLAYBOOK, RANSOMWARE_PLAYBOOK, DEMO_TASKS,
    DEMO_PROCESSES, DEMO_DOCUMENTS, DEMO_VENDORS, DEMO_INCIDENTS,
    DEMO_PEOPLE_EXTRA, TASK_DEPENDENCIES, COMPLIANCE_MAPPINGS,
)
from core.falkordb_client import CompanyBrainDB


# --- Regulations ---
REGULATIONS = [
    {
        'reg_id': 'gdpr_eu',
        'name': 'GDPR (EU) 2016/679',
        'jurisdiction': 'European Union',
        'citation': 'Regulation (EU) 2016/679, Articles 33-34',
        'effective_date': '2018-05-25',
    },
    {
        'reg_id': 'ccpa_ca',
        'name': 'CCPA Cal. Civ. Code §1798.100',
        'jurisdiction': 'California, USA',
        'citation': 'California Civil Code §1798.100 et seq.',
        'effective_date': '2020-01-01',
    },
    {
        'reg_id': 'hipaa_privacy',
        'name': 'HIPAA Privacy Rule',
        'jurisdiction': 'United States',
        'citation': '45 CFR §164.530',
        'effective_date': '2003-04-14',
    },
    {
        'reg_id': 'sec_8k',
        'name': 'SEC Form 8-K Reporting',
        'jurisdiction': 'United States',
        'citation': '17 CFR §249.308 — material cybersecurity incidents',
        'effective_date': '2023-12-18',
    },
]


def seed_all(db: CompanyBrainDB, reset: bool = False):
    """Seed all curated data into FalkorDB."""
    print("Seeding Company Brain graph...")
    print()

    if reset:
        print("  Resetting graph (deleting all data)...")
        try:
            db.query("MATCH (n) DETACH DELETE n")
            print("  ✅ Graph cleared")
        except Exception as e:
            print(f"  ⚠️  Reset warning: {e}")
        print()

    # --- Playbooks ---
    print("  Seeding playbooks...")
    playbooks = [DATA_BREACH_PLAYBOOK, RANSOMWARE_PLAYBOOK]
    # Fix: seed_playbooks expects 'source' but seed_data uses 'source' not 'source_citation'
    for pb in playbooks:
        # Add source_citation field expected by CompanyBrainDB
        pb['source_citation'] = pb.get('source', pb.get('source_citation', ''))
        for step in pb['steps']:
            # Ensure contact_role is set
            if 'contact' in step and 'contact_role' not in step:
                step['contact_role'] = step['contact']

    db.seed_playbooks(playbooks)
    print(f"  ✅ {len(playbooks)} playbooks seeded")

    # --- Tasks ---
    print("  Seeding tasks...")
    db.seed_tasks(DEMO_TASKS)
    print(f"  ✅ {len(DEMO_TASKS)} tasks seeded")

    # --- Regulations ---
    print("  Seeding regulations...")
    db.seed_regulations(REGULATIONS)
    print(f"  ✅ {len(REGULATIONS)} regulations seeded")

    # --- Additional people ---
    print("  Seeding people (ownership/cascade)...")
    db.seed_people(DEMO_PEOPLE_EXTRA)
    print(f"  ✅ {len(DEMO_PEOPLE_EXTRA)} people seeded")

    # --- Processes ---
    print("  Seeding processes...")
    db.seed_processes(DEMO_PROCESSES, DEMO_TASKS)
    print(f"  ✅ {len(DEMO_PROCESSES)} processes seeded")

    # --- Documents ---
    print("  Seeding documents...")
    db.seed_documents(DEMO_DOCUMENTS)
    print(f"  ✅ {len(DEMO_DOCUMENTS)} documents seeded")

    # --- Vendors ---
    print("  Seeding vendors...")
    db.seed_vendors(DEMO_VENDORS)
    print(f"  ✅ {len(DEMO_VENDORS)} vendors seeded")

    # --- Incidents ---
    print("  Seeding incidents...")
    db.seed_incidents(DEMO_INCIDENTS)
    print(f"  ✅ {len(DEMO_INCIDENTS)} incidents seeded")

    # --- Task dependencies ---
    print("  Seeding task dependencies...")
    db.seed_task_dependencies(TASK_DEPENDENCIES)
    print(f"  ✅ {len(TASK_DEPENDENCIES)} dependencies seeded")

    # --- Compliance mappings ---
    print("  Seeding compliance mappings...")
    db.seed_compliance_mappings(COMPLIANCE_MAPPINGS)
    print(f"  ✅ {len(COMPLIANCE_MAPPINGS)} compliance mappings seeded")

    # --- Create indexes ---
    print("  Creating indexes...")
    try:
        db.create_fulltext_indexes()
        print("  ✅ Full-text indexes created")
    except Exception as e:
        print(f"  ⚠️  Full-text index warning: {e}")

    try:
        db.create_range_indexes()
        print("  ✅ Range indexes created")
    except Exception as e:
        print(f"  ⚠️  Range index warning: {e}")

    # Vector indexes require actual embedding data; skip if no embeddings
    # (Would be created when documents/tasks have embeddings populated)
    print("  ⏭️  Vector indexes: created when embeddings are populated")

    # --- Stats ---
    print()
    stats = db.get_graph_stats()
    print("  Graph statistics:")
    total_nodes = 0
    for label, count in stats['nodes'].items():
        if count > 0:
            print(f"    {label}: {count}")
            total_nodes += count
    print(f"    Total nodes: {total_nodes}")
    total_rels = sum(stats['relationships'].values())
    print(f"    Total relationships: {total_rels}")
    print()
    print("  ✅ Seeding complete!")


def main():
    parser = argparse.ArgumentParser(description="Seed FalkorDB graph with Company Brain data")
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port (default: 6380)')
    parser.add_argument('--host', type=str, default='localhost', help='FalkorDB host')
    parser.add_argument('--graph', type=str, default='company_brain', help='Graph name')
    parser.add_argument('--reset', action='store_true', help='Delete all data before seeding')
    args = parser.parse_args()

    db = CompanyBrainDB(host=args.host, port=args.port, graph_name=args.graph)
    seed_all(db, reset=args.reset)


if __name__ == '__main__':
    main()
