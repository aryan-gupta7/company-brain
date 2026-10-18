"""Document Ingestion Demo — span-grounded process extraction.

Shows how an SOP document would be parsed, tasks extracted,
dependencies identified, and span-grounding verified.

In production, this uses GraphRAG SDK + LLM for extraction.
For the demo, we show the pipeline with a sample SOP and
simulated extraction results that go through span verification.

Usage:
    uv run python -m demo.ingestion_demo
"""

import sys; sys.path.insert(0, 'src')

from core.graph_utils import (
    build_task_graph,
    detect_cycles,
    find_critical_path,
    validate_process_graph,
    verify_span_grounding,
    verify_all_spans,
    derive_confidence_for_edge,
)
from core.sop_parser import parse_sop_document


# --- Sample SOP document ---
SOP_TEXT = """
Employee Onboarding Procedure (SOP-HR-003, Rev 2.1)

1. HR receives signed offer letter from candidate
2. IT creates Active Directory account
3. IT assigns laptop and equipment
4. HR schedules first-day orientation
5. Manager prepares 30-60-90 day plan
6. HR enrolls employee in benefits portal
7. IT grants system access (email, VPN, GitHub)
8. Manager conducts first-week check-in

Dependencies:
- After receiving the signed offer letter, IT creates the Active Directory account.
- After the AD account is created, IT assigns a laptop and equipment.
- After the AD account is created, HR schedules the first-day orientation.
- After the laptop is assigned, IT grants system access (email, VPN, GitHub).
- After orientation is scheduled, the Manager prepares the 30-60-90 day plan.
- After the offer letter is received, HR enrolls the employee in the benefits portal.
- After system access is granted, the Manager conducts the first-week check-in.
"""


# --- REAL EXTRACTION: Parse the SOP text using rule-based parser ---
# In production: GraphRAG SDK chunks the document, LLM extracts these.
# For demo: we use a deterministic regex + IDF-weighted matching parser.
EXTRACTED_TASKS, EXTRACTED_DEPS = parse_sop_document(SOP_TEXT)

# Simulated additional extraction runs (for agreement scoring)
# These simulate what a second/third LLM extraction run might produce.
EXTRACTED_DEPS_RUN_2 = [
    {'from': d['from'], 'to': d['to'], 'source_quote': d['source_quote'], 'confidence': d['confidence'] - 0.05}
    for d in EXTRACTED_DEPS
]
# Remove one edge to simulate extraction inconsistency
if len(EXTRACTED_DEPS_RUN_2) > 1:
    EXTRACTED_DEPS_RUN_2.pop()

EXTRACTED_DEPS_RUN_3 = [
    {'from': d['from'], 'to': d['to'], 'source_quote': d['source_quote'], 'confidence': d['confidence']}
    for d in EXTRACTED_DEPS
]


def run_ingestion_demo():
    """Run the document ingestion demo."""
    print()
    print("=" * 70)
    print("  📄 MODULE 2: DOCUMENT INGESTION & PROCESS EXTRACTION")
    print("=" * 70)
    print()
    print("  User: \"Here is our Employee Onboarding SOP. What did you extract?\"")
    print(f"  Document: SOP-HR-003, Rev 2.1 ({len(SOP_TEXT)} chars)")
    print()

    # --- Step 1: Span-grounding verification ---
    print("  Step 1: Span-grounding verification")
    print("  " + "─" * 50)
    valid, invalid = verify_all_spans(EXTRACTED_DEPS, SOP_TEXT)

    print(f"  ✅ Verified: {len(valid)}/{len(EXTRACTED_DEPS)} edges have verbatim source quotes")
    if invalid:
        print(f"  ❌ Failed: {len(invalid)} edges")
        for dep in invalid:
            print(f"     {dep.get('span_error', 'Unknown error')}")
    print()

    # --- Step 2: Graph validation ---
    print("  Step 2: Graph validation")
    print("  " + "─" * 50)
    result = validate_process_graph(EXTRACTED_TASKS, EXTRACTED_DEPS)

    if result['valid']:
        print(f"  ✅ No cycles detected")
        print(f"  📊 Critical path: {' → '.join(result['critical_path'])}")
        print(f"  ⏱️  Critical path length: {result['path_length_hours']:.2f} hours")
    else:
        print(f"  ❌ Cycles detected: {result['cycles']}")
    print()

    # --- Step 3: Multi-run agreement scoring ---
    print("  Step 3: Agreement scoring (3 extraction runs)")
    print("  " + "─" * 50)
    all_runs = [EXTRACTED_DEPS, EXTRACTED_DEPS_RUN_2, EXTRACTED_DEPS_RUN_3]

    print(f"  {'Edge':<35} {'Runs':>5} {'Agreement':>10}")
    print(f"  {'─'*35} {'─'*5} {'─'*10}")

    for dep in EXTRACTED_DEPS:
        edge_key = (dep['from'], dep['to'])
        from_name = next(t['name'] for t in EXTRACTED_TASKS if t['task_id'] == dep['from'])
        to_name = next(t['name'] for t in EXTRACTED_TASKS if t['task_id'] == dep['to'])
        agreement = derive_confidence_for_edge(edge_key, all_runs)
        edge_label = f"{from_name[:15]} → {to_name[:15]}"
        runs_found = sum(1 for run in all_runs if any(
            (e.get('from'), e.get('to')) == edge_key for e in run
        ))
        flag = "⚠️" if agreement < 0.9 else "✅"
        print(f"  {flag} {edge_label:<33} {runs_found}/3 {agreement:>8.0%}")

    print()
    print("  ⚠️  Low agreement edges flagged for user review.")
    print("  Agreement measures consistency across runs, NOT correctness.")
    print()

    # --- Step 4: Summary ---
    print("  Step 4: Extraction summary")
    print("  " + "─" * 50)
    print(f"  Tasks extracted: {len(EXTRACTED_TASKS)}")
    print(f"  Dependencies: {len(EXTRACTED_DEPS)}")
    print(f"  Span-grounded: {len(valid)}/{len(EXTRACTED_DEPS)}")
    print(f"  Graph valid: {'Yes' if result['valid'] else 'No'}")
    print(f"  Critical path: {result['path_length_hours']:.2f} hours")
    print()
    print("  Pipeline: Parse → Chunk → Extract → Span Verify → Validate → User Review")
    print("  (Production: GraphRAG SDK + LLM extraction)")
    print()


if __name__ == '__main__':
    run_ingestion_demo()
