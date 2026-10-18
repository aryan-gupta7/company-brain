"""Fetch real cybersecurity breach disclosures from SEC EDGAR and ingest into FalkorDB.

Uses the SEC EDGAR Full-Text Search API (free, no API key).
Fetches 8-K Item 1.05 filings (material cybersecurity incidents).

Usage:
    uv run python -m demo.fetch_sec_breaches
    uv run python -m demo.fetch_sec_breaches --count 10
    uv run python -m demo.fetch_sec_breaches --port 6380
"""

import sys; sys.path.insert(0, 'src')

import argparse
import json
import urllib.request
import urllib.parse
from datetime import datetime

from core.falkordb_client import CompanyBrainDB
from core.embeddings import embed_text


SEC_EDGAR_URL = "https://efts.sec.gov/LATEST/search-index"


def fetch_sec_breaches(count: int = 10) -> list:
    """Fetch 8-K Item 1.05 filings from SEC EDGAR."""
    params = {
        'q': '"Item 1.05"',
        'forms': '8-K',
        'size': str(count),
    }
    url = SEC_EDGAR_URL + '?' + urllib.parse.urlencode(params)

    req = urllib.request.Request(url)
    req.add_header('User-Agent', 'CompanyBrain/1.0 (research@example.com)')

    print(f"  Fetching {count} filings from SEC EDGAR...")

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            data = json.loads(response.read().decode())
    except Exception as e:
        print(f"  ⚠️  Could not fetch from SEC: {e}")
        return []

    hits = data.get('hits', {}).get('hits', [])
    total = data.get('hits', {}).get('total', {}).get('value', 0)
    print(f"  Found {total} total filings, processing {len(hits)}")

    breaches = []
    for hit in hits:
        src = hit.get('_source', {})

        # Extract company name (remove ticker/CIK suffix)
        display_name = src.get('display_names', ['Unknown'])[0]
        company_name = display_name.split('  (CIK')[0].strip() if display_name else 'Unknown'

        breach = {
            'incident_id': f"sec_{src.get('adsh', 'unknown').replace('-', '_')}",
            'company_name': company_name,
            'type': 'cybersecurity_incident',
            'severity': 'material',  # SEC Item 1.05 = material incident
            'detected_at': src.get('file_date', 'unknown'),
            'filing_date': src.get('file_date', 'unknown'),
            'status': 'disclosed',
            'items': src.get('items', []),
            'description': f"{company_name} disclosed a material cybersecurity incident on {src.get('file_date', 'unknown')}",
        }
        breaches.append(breach)

    return breaches


def ingest_breaches(db: CompanyBrainDB, breaches: list):
    """Ingest breach data into FalkorDB."""
    print(f"\n  Ingesting {len(breaches)} breach disclosures...")

    for breach in breaches:
        # Create incident node
        db.graph.query(
            """
            MERGE (i:Incident {incident_id: $incident_id})
            SET i.company_name = $company_name,
                i.type = $type,
                i.severity = $severity,
                i.detected_at = $detected_at,
                i.filing_date = $filing_date,
                i.status = $status,
                i.description = $description,
                i.source = 'SEC EDGAR 8-K Item 1.05',
                i.disclosure_type = 'regulatory_filing'
            """,
            breach
        )

        # Generate and store embedding
        emb = embed_text(breach['description'])
        db.update_node_embedding('Incident', 'incident_id', breach['incident_id'], emb)

        print(f"    ✅ {breach['company_name']} ({breach['filing_date']})")

    print(f"\n  ✅ {len(breaches)} breach disclosures ingested!")


def main():
    parser = argparse.ArgumentParser(description="Fetch SEC breach data into FalkorDB")
    parser.add_argument('--count', type=int, default=10, help='Number of filings to fetch')
    parser.add_argument('--port', type=int, default=6380, help='FalkorDB port')
    args = parser.parse_args()

    print()
    print("  Fetching SEC 8-K Item 1.05 Cybersecurity Breach Disclosures")
    print("  " + "─" * 50)
    print()

    db = CompanyBrainDB(port=args.port)

    breaches = fetch_sec_breaches(args.count)
    if breaches:
        ingest_breaches(db, breaches)

        # Show what was ingested
        print("\n  Ingested incidents:")
        incidents = db.get_all_incidents()
        for inc in incidents:
            print(f"    {inc[0]}: type={inc[1]}, severity={inc[2]}, status={inc[3]}")
    else:
        print("  No breaches fetched. Check network connection.")


if __name__ == '__main__':
    main()
