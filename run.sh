#!/usr/bin/env bash
# Company Brain — FalkorDB Hackathon 2026
# Master run script for judges/reviewers
set -e

cd "$(dirname "$0")"

export PYTHONPATH=src

echo "======================================================================"
echo "  🧠 COMPANY BRAIN — FalkorDB Hackathon 2026"
echo "======================================================================"
echo ""

# --- Check FalkorDB ---
echo "Checking FalkorDB..."
if docker ps | grep -q falkordb-hackathon; then
    echo "  ✅ FalkorDB container running"
else
    echo "  ⚠️  FalkorDB container not found. Starting..."
    docker run -d --name falkordb-hackathon \
        -p 6380:6379 -p 3001:3000 \
        falkordb/falkordb:latest 2>/dev/null || true
    sleep 3
    echo "  ✅ FalkorDB started on port 6380"
fi
echo ""

# --- Seed graph ---
echo "Seeding graph..."
uv run python -m demo.seed_graph --reset 2>&1 | grep -v "^$"
echo ""

# --- Generate embeddings ---
echo "Generating embeddings (FastEmbed, 384-dim)..."
uv run python -m demo.generate_embeddings 2>&1 | grep -v "^$"
echo ""

# --- Fetch SEC breach data ---
echo "Fetching SEC 8-K Item 1.05 breach disclosures..."
uv run python -m demo.fetch_sec_breaches --count 20 2>&1 | grep -v "^$"
echo ""

# --- Run tests ---
echo "Running tests (60 tests)..."
uv run python -m pytest src/tests/ -q 2>&1 | tail -3
echo ""

# --- Run demos ---
echo "======================================================================"
echo "  DEMO 1: INCIDENT RESPONSE"
echo "======================================================================"
uv run python -m demo.run_demo --module incident 2>&1

echo "======================================================================"
echo "  DEMO 2: PROCESS EXTRACTION & INGESTION"
echo "======================================================================"
uv run python -m demo.ingestion_demo 2>&1

echo "======================================================================"
echo "  DEMO 3: AUTOMATION ASSESSMENT"
echo "======================================================================"
uv run python -m demo.run_demo --module automation 2>&1

echo "======================================================================"
echo "  DEMO 4: CASCADE ANALYSIS (Blast Radius)"
echo "======================================================================"
uv run python -m demo.cascade_demo 2>&1

echo "======================================================================"
echo "  DEMO 5: VECTOR SEARCH + SIMILAR INCIDENTS"
echo "======================================================================"
PYTHONPATH=src uv run python -c "
from core.falkordb_client import CompanyBrainDB
from core.embeddings import embed_text
db = CompanyBrainDB(port=6380)

print()
print('User: \"Find similar incidents to a ransomware attack\"')
print()
query_vec = embed_text('ransomware attack encryption data')
result = db.graph.query(
    'CALL db.idx.vector.queryNodes(\$label, \$attr, \$k, vecf32(\$qv)) YIELD node, score RETURN node.incident_id, node.company_name, node.type, node.severity, score ORDER BY score DESC LIMIT 5',
    {'label': 'Incident', 'attr': 'embedding', 'k': 5, 'qv': query_vec}
)
print('Agent: \"Similar incidents (vector search, cosine similarity):\"')
print()
for i, row in enumerate(result.result_set or [], 1):
    name = row[1] if row[1] else row[0]
    print(f'  {i}. {name} — {row[2]} ({row[3]}) similarity={row[4]:.2f}')
print()
print('  Source: SEC EDGAR 8-K Item 1.05 filings (real public data)')
print('  Embeddings: BAAI/bge-small-en-v1.5 (384-dim, FastEmbed/ONNX)')
print()
" 2>&1

echo "======================================================================"
echo "  DEMO 6: SECURITY"
echo "======================================================================"
uv run python -m demo.security_demo 2>&1

echo "======================================================================"
echo "  ALL DEMOS COMPLETE"
echo "======================================================================"
echo ""
echo "  To try the interactive CLI:"
echo "    uv run python -m cli.interactive"
echo ""
echo "  FalkorDB GUI: http://localhost:3001"
echo ""
echo "  Graph stats:"
PYTHONPATH=src uv run python -c "
from core.falkordb_client import CompanyBrainDB
db = CompanyBrainDB(port=6380)
stats = db.get_graph_stats()
print(f'    {sum(stats[\"nodes\"].values())} nodes, {sum(stats[\"relationships\"].values())} relationships')
" 2>&1
echo ""
