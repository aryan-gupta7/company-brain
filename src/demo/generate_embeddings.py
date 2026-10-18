"""Generate and store embeddings for all nodes in FalkorDB.

Uses FastEmbed (ONNX Runtime, no torch) with BAAI/bge-small-en-v1.5 (384-dim).

Usage:
    uv run python -m demo.generate_embeddings
    uv run python -m demo.generate_embeddings --port 6380
"""

import sys; sys.path.insert(0, 'src')

import argparse
from core.falkordb_client import CompanyBrainDB
from core.embeddings import (
    embed_task, embed_document, embed_person, embed_incident, embed_regulation,
    embed_text, get_dimension,
)


def generate_all_embeddings(db: CompanyBrainDB):
    """Generate embeddings for all nodes and store in FalkorDB."""
    print(f"Generating embeddings ({get_dimension()}-dim)...")
    print()

    # Ensure vector indexes exist
    print("  Creating vector indexes...")
    db.create_vector_indexes()
    print("  ✅ Vector indexes ready")
    print()

    # Tasks
    print("  Embedding tasks...")
    tasks = db.get_all_tasks()
    for task_id, task_name in tasks:
        # Get full task details
        result = db.query(
            "MATCH (t:Task {task_id: $tid}) RETURN t.name, t.description",
            {'tid': task_id}
        )
        if result:
            name, desc = result[0]
            task_data = {'name': name, 'description': desc or ''}
            emb = embed_task(task_data)
            db.update_node_embedding('Task', 'task_id', task_id, emb)
            print(f"    ✅ {task_id}: {name}")

    # Documents
    print("  Embedding documents...")
    docs = db.query("MATCH (d:Document) RETURN d.doc_id, d.title, d.type")
    for doc_id, title, doc_type in (docs or []):
        doc_data = {'title': title, 'type': doc_type or ''}
        emb = embed_document(doc_data)
        db.update_node_embedding('Document', 'doc_id', doc_id, emb)
        print(f"    ✅ {doc_id}: {title}")

    # Persons
    print("  Embedding persons...")
    people = db.query("MATCH (p:Person) RETURN p.person_id, p.name, p.role, p.department")
    for pid, name, role, dept in (people or []):
        person_data = {'name': name, 'role': role or '', 'department': dept or ''}
        emb = embed_person(person_data)
        db.update_node_embedding('Person', 'person_id', pid, emb)
        print(f"    ✅ {pid}: {name}")

    # Incidents
    print("  Embedding incidents...")
    incidents = db.query("MATCH (i:Incident) RETURN i.incident_id, i.type, i.severity, i.status")
    for iid, itype, severity, status in (incidents or []):
        inc_data = {'type': itype or '', 'severity': severity or '', 'status': status or ''}
        emb = embed_incident(inc_data)
        db.update_node_embedding('Incident', 'incident_id', iid, emb)
        print(f"    ✅ {iid}: {itype} ({severity})")

    # Regulations
    print("  Embedding regulations...")
    regs = db.query("MATCH (r:Regulation) RETURN r.reg_id, r.name, r.jurisdiction, r.citation")
    for rid, rname, jurisdiction, citation in (regs or []):
        reg_data = {'name': rname, 'jurisdiction': jurisdiction or '', 'citation': citation or ''}
        emb = embed_regulation(reg_data)
        db.update_node_embedding('Regulation', 'reg_id', rid, emb)
        print(f"    ✅ {rid}: {rname}")

    print()
    print("  ✅ All embeddings generated and stored!")


def main():
    parser = argparse.ArgumentParser(description="Generate embeddings for FalkorDB nodes")
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port')
    args = parser.parse_args()

    db = CompanyBrainDB(port=args.port)
    generate_all_embeddings(db)


if __name__ == '__main__':
    main()
