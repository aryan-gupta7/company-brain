"""Seed data for Company Brain demo.

Curated playbook data (NOT extracted from documents).
Uses StepTemplate label to prevent ingestion from modifying playbooks.
"""

from datetime import datetime


# --- Playbook: Data Breach Response ---
# Source: NIST SP 800-61 Rev. 2
# Deadlines: GDPR Art. 33 (72h from awareness), GDPR Art. 48 (48h from awareness)

DATA_BREACH_PLAYBOOK = {
    'playbook_id': 'pb_data_breach',
    'name': 'Data Breach Response',
    'incident_type': 'data_breach',
    'version': '1.0',
    'last_reviewed': '2026-10-01',
    'source': 'NIST SP 800-61 Rev. 2',
    'steps': [
        {
            'step_id': 'step_isolate',
            'name': 'Isolate Affected Systems',
            'order': 1,
            'amount': 0,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_forensics',
            'name': 'Engage External Forensics',
            'order': 2,
            'amount': 1,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'SecureCorp IR Team',
            'contact_role': 'External Forensics',
            'legal_citation': None,
        },
        {
            'step_id': 'step_legal_hold',
            'name': 'Issue Legal Hold',
            'order': 3,
            'amount': 2,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'James Wilson',
            'contact_role': 'General Counsel',
            'legal_citation': None,
        },
        {
            'step_id': 'step_gdpr_assess',
            'name': 'GDPR Breach Assessment',
            'order': 4,
            'amount': 24,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness',
        },
        {
            'step_id': 'step_gdpr_file',
            'name': 'GDPR Regulatory Filing',
            'order': 5,
            'amount': 72,
            'unit': 'clock_hours',
            'trigger': 'awareness',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness — file with supervisory authority',
        },
        {
            'step_id': 'step_notify',
            'name': 'Customer Notification',
            'order': 6,
            'amount': 48,
            'unit': 'clock_hours',
            'trigger': 'awareness',
            'contact': 'Alex Rivera',
            'contact_role': 'VP Marketing',
            'legal_citation': 'GDPR Art. 34: without undue delay if high risk to individuals',
        },
    ],
}


# --- Playbook: Ransomware Response ---
RANSOMWARE_PLAYBOOK = {
    'playbook_id': 'pb_ransomware',
    'name': 'Ransomware Response',
    'incident_type': 'ransomware',
    'version': '1.0',
    'last_reviewed': '2026-10-01',
    'source': 'NIST SP 800-61 Rev. 2',
    'steps': [
        {
            'step_id': 'step_rw_isolate',
            'name': 'Isolate Network Segments',
            'order': 1,
            'amount': 0,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_rw_assess',
            'name': 'Assess Scope of Infection',
            'order': 2,
            'amount': 2,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Sarah Chen',
            'contact_role': 'CISO',
            'legal_citation': None,
        },
        {
            'step_id': 'step_rw_gdpr',
            'name': 'GDPR Breach Assessment',
            'order': 3,
            'amount': 24,
            'unit': 'clock_hours',
            'trigger': 'detection',
            'contact': 'Maria Garcia',
            'contact_role': 'DPO',
            'legal_citation': 'GDPR Art. 33: 72 hours from awareness',
        },
    ],
}


# --- All playbooks ---
PLAYBOOKS = {
    'data_breach': DATA_BREACH_PLAYBOOK,
    'ransomware': RANSOMWARE_PLAYBOOK,
}


# --- Cypher seed statements for FalkorDB ---
# Creates the playbook graph with StepTemplate nodes (not Task)

SEED_CYPHER = """
// Create playbook
CREATE (pb:Playbook {
  playbook_id: 'pb_data_breach',
  name: 'Data Breach Response',
  incident_type: 'data_breach',
  version: '1.0',
  last_reviewed: '2026-10-01',
  source_citation: 'NIST SP 800-61 Rev. 2'
})

// Create step templates (StepTemplate label, NOT Task)
CREATE (s1:StepTemplate {step_id: 'step_isolate', name: 'Isolate Affected Systems', contact_role: 'CISO'})
CREATE (s2:StepTemplate {step_id: 'step_forensics', name: 'Engage External Forensics', contact_role: 'External_Forensics'})
CREATE (s3:StepTemplate {step_id: 'step_legal_hold', name: 'Issue Legal Hold', contact_role: 'General_Counsel'})
CREATE (s4:StepTemplate {step_id: 'step_gdpr_assess', name: 'GDPR Breach Assessment', contact_role: 'DPO'})
CREATE (s5:StepTemplate {step_id: 'step_gdpr_file', name: 'GDPR Regulatory Filing', contact_role: 'DPO'})
CREATE (s6:StepTemplate {step_id: 'step_notify', name: 'Customer Notification', contact_role: 'VP_Marketing'})

// Link playbook to steps (deadline metadata on edges only)
CREATE (pb)-[:HAS_STEP {order: 1, amount: 0, unit: 'clock_hours', trigger: 'detection'}]->(s1)
CREATE (pb)-[:HAS_STEP {order: 2, amount: 1, unit: 'clock_hours', trigger: 'detection'}]->(s2)
CREATE (pb)-[:HAS_STEP {order: 3, amount: 2, unit: 'clock_hours', trigger: 'detection'}]->(s3)
CREATE (pb)-[:HAS_STEP {order: 4, amount: 24, unit: 'clock_hours', trigger: 'detection', legal_citation: 'GDPR Art. 33: 72 hours from awareness'}]->(s4)
CREATE (pb)-[:HAS_STEP {order: 5, amount: 72, unit: 'clock_hours', trigger: 'awareness', legal_citation: 'GDPR Art. 33: 72 hours from awareness'}]->(s5)
CREATE (pb)-[:HAS_STEP {order: 6, amount: 48, unit: 'clock_hours', trigger: 'awareness', legal_citation: 'GDPR Art. 34: without undue delay if high risk'}]->(s6)

// Create contacts
CREATE (ciso:Person {person_id: 'p_ciso', name: 'Sarah Chen', role: 'CISO', department: 'Engineering'})
CREATE (gc:Person {person_id: 'p_gc', name: 'James Wilson', role: 'General Counsel', department: 'Legal'})
CREATE (dpo:Person {person_id: 'p_dpo', name: 'Maria Garcia', role: 'DPO', department: 'Legal'})
CREATE (sec:Person {person_id: 'p_sec', name: 'SecureCorp IR Team', role: 'External_Forensics', department: 'External'})
CREATE (vp:Person {person_id: 'p_vp', name: 'Alex Rivera', role: 'VP_Marketing', department: 'Marketing'})

// Link contacts to steps
CREATE (s1)-[:CONTACT]->(ciso)
CREATE (s2)-[:CONTACT]->(sec)
CREATE (s3)-[:CONTACT]->(gc)
CREATE (s4)-[:CONTACT]->(dpo)
CREATE (s5)-[:CONTACT]->(dpo)
CREATE (s6)-[:CONTACT]->(vp)

// Create vector indexes (384-dim for all-MiniLM-L6-v2)
CREATE VECTOR INDEX FOR (t:Task) ON (t.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (d:Document) ON (d.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (p:Person) ON (p.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
CREATE VECTOR INDEX FOR (i:Incident) ON (i.embedding) OPTIONS {dimension: 384, similarityFunction: 'cosine'}
"""


# --- Demo company: processes and tasks ---

DEMO_TASKS = [
    {
        'task_id': 't_invoice_recon',
        'name': 'Invoice Reconciliation',
        'description': 'Match received invoices against purchase orders and payment records',
        'frequency_per_year': 52,
        'time_per_exec_hours': 3.85,
        'structuredness': 0.9,
        'data_accessibility': 0.95,
        'decision_complexity': 0.2,
        'exception_rate': 0.1,
        'error_cost_dollars': 500,
        'compliance_risk': 0.1,
        'labor_rate_dollars': 42,
        'implementation_cost_annual': 1200,
    },
    {
        'task_id': 't_expense_report',
        'name': 'Expense Report Review',
        'description': 'Review and approve employee expense reports',
        'frequency_per_year': 24,
        'time_per_exec_hours': 1.5,
        'structuredness': 0.7,
        'data_accessibility': 0.8,
        'decision_complexity': 0.4,
        'exception_rate': 0.3,
        'error_cost_dollars': 200,
        'compliance_risk': 0.2,
        'labor_rate_dollars': 35,
        'implementation_cost_annual': 800,
    },
    {
        'task_id': 't_strategy_review',
        'name': 'Executive Strategy Review',
        'description': 'Quarterly strategic planning and market analysis',
        'frequency_per_year': 4,
        'time_per_exec_hours': 8,
        'structuredness': 0.2,
        'data_accessibility': 0.3,
        'decision_complexity': 0.9,
        'exception_rate': 0.8,
        'error_cost_dollars': 50000,
        'compliance_risk': 0.1,
        'labor_rate_dollars': 150,
        'implementation_cost_annual': 0,
    },
    {
        'task_id': 't_data_entry',
        'name': 'Customer Data Entry',
        'description': 'Enter customer information from forms into CRM',
        'frequency_per_year': 260,
        'time_per_exec_hours': 0.5,
        'structuredness': 0.95,
        'data_accessibility': 0.9,
        'decision_complexity': 0.1,
        'exception_rate': 0.05,
        'error_cost_dollars': 100,
        'compliance_risk': 0.3,
        'labor_rate_dollars': 25,
        'implementation_cost_annual': 600,
    },
]


# --- Demo company: processes ---

DEMO_PROCESSES = [
    {
        'process_id': 'proc_finance',
        'name': 'Finance & Accounting',
        'domain': 'Finance',
        'description': 'All financial operations including invoicing, expenses, and reporting',
        'owner_person_id': 'p_cfo',
        'task_ids': ['t_invoice_recon', 't_expense_report'],
    },
    {
        'process_id': 'proc_sales',
        'name': 'Sales & CRM',
        'domain': 'Sales',
        'description': 'Customer relationship management and data entry',
        'owner_person_id': 'p_vp',
        'task_ids': ['t_data_entry'],
    },
    {
        'process_id': 'proc_strategy',
        'name': 'Strategic Planning',
        'domain': 'Executive',
        'description': 'Quarterly strategy reviews and market analysis',
        'owner_person_id': 'p_ceo',
        'task_ids': ['t_strategy_review'],
    },
]


# --- Demo company: documents ---

DEMO_DOCUMENTS = [
    {
        'doc_id': 'doc_onboarding_sop',
        'title': 'Employee Onboarding Procedure (SOP-HR-003)',
        'type': 'SOP',
        'format': 'text',
        'source_quote': 'After receiving the signed offer letter, IT creates the Active Directory account',
    },
    {
        'doc_id': 'doc_invoice_sop',
        'title': 'Invoice Processing Procedure',
        'type': 'SOP',
        'format': 'text',
        'source_quote': 'After receiving the invoice, match it against the purchase order',
    },
    {
        'doc_id': 'doc_data_breach_pb',
        'title': 'Data Breach Response Playbook',
        'type': 'Playbook',
        'format': 'PDF',
        'source_quote': 'NIST SP 800-61 Rev. 2',
    },
]


# --- Demo company: vendors ---

DEMO_VENDORS = [
    {
        'entity_id': 'v_securecorp',
        'name': 'SecureCorp IR',
        'type': 'Incident Response',
        'contact_info': 'ir@securecorp.com',
        'risk_score': 0.2,
        'status': 'active',
        'provides_for_task_ids': ['step_forensics'],
    },
    {
        'entity_id': 'v_cloudhost',
        'name': 'CloudHost Inc',
        'type': 'Cloud Infrastructure',
        'contact_info': 'support@cloudhost.io',
        'risk_score': 0.4,
        'status': 'active',
        'provides_for_process_ids': ['proc_finance', 'proc_sales'],
    },
    {
        'entity_id': 'v_crm_vendor',
        'name': 'CRMPro',
        'type': 'CRM Software',
        'contact_info': 'help@crmpro.com',
        'risk_score': 0.3,
        'status': 'active',
        'provides_for_task_ids': ['t_data_entry'],
    },
]


# --- Demo company: incidents ---

DEMO_INCIDENTS = [
    {
        'incident_id': 'inc_2026_001',
        'type': 'data_breach',
        'severity': 'high',
        'detected_at': '2026-10-16T14:30:00',
        'status': 'active',
        'triggers_playbook_id': 'pb_data_breach',
    },
    {
        'incident_id': 'inc_2026_002',
        'type': 'ransomware',
        'severity': 'critical',
        'detected_at': '2026-09-28T09:15:00',
        'status': 'resolved',
        'triggers_playbook_id': 'pb_ransomware',
    },
]


# --- Additional people (for ownership and cascade) ---

DEMO_PEOPLE_EXTRA = [
    {'person_id': 'p_cfo', 'name': 'Robert Kim', 'role': 'CFO', 'department': 'Finance'},
    {'person_id': 'p_ceo', 'name': 'Diana Ross', 'role': 'CEO', 'department': 'Executive'},
]


# --- Task dependencies (for cascade analysis) ---

TASK_DEPENDENCIES = [
    {'from': 't_expense_report', 'to': 't_invoice_recon',
     'source_quote': 'Expense reports reference invoice reconciliation data',
     'confidence': 0.7},
    {'from': 't_strategy_review', 'to': 't_data_entry',
     'source_quote': 'Strategy review uses customer data from CRM',
     'confidence': 0.6},
]


# --- Compliance mappings ---

COMPLIANCE_MAPPINGS = [
    {'task_id': 't_data_entry', 'reg_id': 'gdpr_eu',
     'source_quote': 'Customer data entry must comply with GDPR Art. 33'},
    {'task_id': 't_data_entry', 'reg_id': 'ccpa_ca',
     'source_quote': 'California customer data subject to CCPA'},
    {'task_id': 't_data_entry', 'reg_id': 'dpdpa_in',
     'source_quote': 'Customer data processing under DPDPA 2023 Section 8(6)'},
    {'task_id': 't_data_entry', 'reg_id': 'cert_in',
     'source_quote': 'CERT-In April 2022 Directive: 6-hour breach reporting'},
    {'task_id': 't_invoice_recon', 'reg_id': 'sec_8k',
     'source_quote': 'Financial reconciliation data for SEC reporting'},
]


# --- India-specific regulation data ---
# DPDPA 2023: Digital Personal Data Protection Act (India)
# CERT-In: Indian Computer Emergency Response Team
# IT Act 2000: Information Technology Act (India)

INDIA_REGULATIONS = [
    {
        'reg_id': 'dpc_in',
        'name': 'DPDPA 2023',
        'full_name': 'Digital Personal Data Protection Act, 2023',
        'jurisdiction': 'India',
        'citation': 'DPDPA 2023, Section 8(6): notify Data Protection Board on personal data breach',
        'breach_notification_hours': 72,
        'max_penalty_inr': 2500000000,  # ₹250 crore
        'penalty_usd_approx': 30000000,  # ~$30M USD
        'status': 'In force (phased: core Nov 2025, penalties Nov 2026, remainder May 2027)',
        'enacted': '2023-08-11',
        'key_provisions': 'Data fiduciary obligations, Data Principal rights, Data Protection Board of India',
    },
    {
        'reg_id': 'cert_in',
        'name': 'CERT-In Directive',
        'full_name': 'CERT-In April 2022 Directions (Section 70B IT Act)',
        'jurisdiction': 'India',
        'citation': 'CERT-In 2022 Directive: report cyber incidents within 6 hours',
        'breach_notification_hours': 6,
        'max_penalty_inr': None,
        'penalty_usd_approx': None,
        'status': 'In force since April 2022',
        'enacted': '2022-04-28',
        'key_provisions': '6-hour breach reporting for high-severity incidents, ICT logs within India, NTP sync',
    },
    {
        'reg_id': 'it_act_india',
        'name': 'IT Act 2000',
        'full_name': 'Information Technology Act, 2000 (India)',
        'jurisdiction': 'India',
        'citation': 'IT Act Section 72A: disclosure of information in breach of lawful contract',
        'breach_notification_hours': None,
        'max_penalty_inr': 500000,  # ₹5 lakh
        'penalty_usd_approx': 6000,  # ~$6K USD
        'status': 'In force',
        'enacted': '2000-06-17',
        'key_provisions': 'Section 43A: compensation for data breach; Section 72A: criminal penalty up to 3 years + ₹5L fine',
    },
]

# India-specific playbook step (CERT-In 6-hour notification)
INDIA_BREACH_PLAYBOOK_EXTENSION = {
    'step_id': 'step_cert_in_notify',
    'name': 'CERT-In Incident Notification (6 hours)',
    'order': 7,
    'amount': 6,
    'unit': 'clock_hours',
    'trigger': 'detection',
    'contact': 'CERT-In Nodal Officer',
    'contact_role': 'Government Cyber Response',
    'legal_citation': 'CERT-In April 2022 Directive (Section 70B, IT Act 2000): 6-hour breach reporting for high-severity incidents',
}


def get_playbook(incident_type: str) -> dict:
    """Get a curated playbook by incident type."""
    return PLAYBOOKS.get(incident_type)


def get_demo_tasks() -> list:
    """Get demo tasks for automation assessment."""
    return DEMO_TASKS


def get_demo_processes() -> list:
    """Get demo processes."""
    return DEMO_PROCESSES


def get_demo_documents() -> list:
    """Get demo documents."""
    return DEMO_DOCUMENTS


def get_demo_vendors() -> list:
    """Get demo vendors."""
    return DEMO_VENDORS


def get_demo_incidents() -> list:
    """Get demo incidents."""
    return DEMO_INCIDENTS


def get_demo_people_extra() -> list:
    """Get additional people for ownership/cascade."""
    return DEMO_PEOPLE_EXTRA


def get_task_dependencies() -> list:
    """Get task dependencies for cascade analysis."""
    return TASK_DEPENDENCIES


def get_compliance_mappings() -> list:
    """Get task-to-regulation compliance mappings."""
    return COMPLIANCE_MAPPINGS


def get_india_regulations() -> list:
    """Get India-specific regulation data."""
    return INDIA_REGULATIONS


def get_india_playbook_extension() -> dict:
    """Get India-specific playbook step (CERT-In 6h notification)."""
    return INDIA_BREACH_PLAYBOOK_EXTENSION
