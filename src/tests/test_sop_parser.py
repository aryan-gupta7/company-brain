"""Tests for the SOP parser — rule-based extraction of tasks and dependencies."""

import sys; sys.path.insert(0, 'src')

from core.sop_parser import (
    parse_sop_document,
    parse_sop_tasks,
    parse_sop_dependencies,
    _tokenize,
    _match_score,
    _compute_idf,
    _normalize_word,
)


# --- Test SOP texts ---

INVOICE_SOP = """
Invoice Processing Procedure

1. Receive invoice from vendor via email
2. Match invoice against purchase order
3. Verify line items and amounts
4. Check budget approval
5. Submit for payment approval
6. Process payment
7. File paid invoice

After receiving the invoice, match it against the purchase order.
After matching is complete, verify all line items.
After verification, check budget approval before submitting.
After budget approval, submit for payment approval.
After payment approval, process the payment.
After payment is processed, file the paid invoice.
"""

ONBOARDING_SOP = """
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


class TestNormalizeWord:
    def test_basic(self):
        assert _normalize_word("running") == "runn"
        assert _normalize_word("matched") == "match"
        assert _normalize_word("processes") == "process"
        assert _normalize_word("verification") == "verific"

    def test_no_suffix_match(self):
        # Words that don't end with known suffixes stay as-is
        assert _normalize_word("receive") == "receive"
        assert _normalize_word("invoice") == "invoice"
        # "payment" ends with "ment" → "pay"
        assert _normalize_word("payment") == "pay"

    def test_punctuation(self):
        assert _normalize_word("hello.") == "hello"
        assert _normalize_word("(test)") == "test"


class TestTokenize:
    def test_basic(self):
        tokens = _tokenize("Receive invoice from vendor")
        assert "receive" in tokens
        assert "invoice" in tokens
        assert "vendor" in tokens
        # Stop words filtered
        assert "from" not in tokens

    def test_empty(self):
        assert _tokenize("") == []
        assert _tokenize("the a an") == []


class TestParseSopTasks:
    def test_invoice_sop(self):
        tasks = parse_sop_tasks(INVOICE_SOP)
        assert len(tasks) == 7
        assert tasks[0]['task_id'] == 'task_1'
        assert tasks[0]['name'] == 'Receive invoice from vendor via email'
        assert tasks[6]['task_id'] == 'task_7'
        assert 'File paid invoice' in tasks[6]['name']

    def test_onboarding_sop(self):
        tasks = parse_sop_tasks(ONBOARDING_SOP)
        assert len(tasks) == 8
        assert tasks[0]['name'] == 'HR receives signed offer letter from candidate'

    def test_empty(self):
        assert parse_sop_tasks("") == []
        assert parse_sop_tasks("No numbered steps here") == []

    def test_all_have_time(self):
        tasks = parse_sop_tasks(INVOICE_SOP)
        for t in tasks:
            assert 'time_per_exec_hours' in t
            assert t['time_per_exec_hours'] > 0


class TestParseSopDependencies:
    def test_invoice_sop(self):
        tasks = parse_sop_tasks(INVOICE_SOP)
        deps = parse_sop_dependencies(INVOICE_SOP, tasks)
        assert len(deps) == 6

        # Check chain: task_2 -> task_1, task_3 -> task_2, etc.
        dep_map = {(d['from'], d['to']) for d in deps}
        assert ('task_2', 'task_1') in dep_map
        assert ('task_3', 'task_2') in dep_map
        assert ('task_4', 'task_3') in dep_map
        assert ('task_5', 'task_4') in dep_map
        assert ('task_6', 'task_5') in dep_map
        assert ('task_7', 'task_6') in dep_map

    def test_onboarding_sop(self):
        tasks = parse_sop_tasks(ONBOARDING_SOP)
        deps = parse_sop_dependencies(ONBOARDING_SOP, tasks)
        assert len(deps) == 7

    def test_no_self_loops(self):
        tasks = parse_sop_tasks(INVOICE_SOP)
        deps = parse_sop_dependencies(INVOICE_SOP, tasks)
        for d in deps:
            assert d['from'] != d['to'], f"Self-loop found: {d}"

    def test_all_have_quotes(self):
        tasks = parse_sop_tasks(INVOICE_SOP)
        deps = parse_sop_dependencies(INVOICE_SOP, tasks)
        for d in deps:
            assert d.get('source_quote'), f"Missing source_quote: {d}"
            assert d.get('confidence', 0) > 0


class TestParseSopDocument:
    def test_full_pipeline(self):
        tasks, deps = parse_sop_document(INVOICE_SOP)
        assert len(tasks) == 7
        assert len(deps) == 6

        # All deps reference valid task IDs
        task_ids = {t['task_id'] for t in tasks}
        for d in deps:
            assert d['from'] in task_ids, f"Unknown from: {d['from']}"
            assert d['to'] in task_ids, f"Unknown to: {d['to']}"

    def test_onboarding_full(self):
        tasks, deps = parse_sop_document(ONBOARDING_SOP)
        assert len(tasks) == 8
        assert len(deps) == 7


class TestMatchScore:
    def test_exact_match(self):
        idf = {'receive': 1.0, 'invoic': 1.0}
        score = _match_score("receive invoice", "Receive invoice from vendor via email", idf)
        assert score > 0.5

    def test_no_match(self):
        idf = {'xyz': 1.0}
        score = _match_score("completely different words", "Receive invoice", idf)
        assert score == 0.0

    def test_prefix_match(self):
        """Stemmed words with shared prefix should match."""
        idf = {'verif': 1.0, 'line': 1.0, 'item': 1.0}
        score = _match_score("verification", "Verify line items", idf)
        assert score > 0.0
