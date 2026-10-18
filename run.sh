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
echo "  DEMO 4: SECURITY"
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
