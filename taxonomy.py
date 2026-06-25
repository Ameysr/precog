"""Agent-type and dimension-aware taxonomy. Supports all agent types and test dimensions."""

from agent_types import AgentType, TestDimension, get_failure_types_for_dimension
from schemas import TestCase


CORE_TAXONOMY: dict[str, list[dict]] = {
    "fintech": [
        {"id": "kyc_verification", "name": "KYC Verification", "description": "User asking about KYC approval time, rejection, document upload"},
        {"id": "order_execution", "name": "Order Execution", "description": "Order not executing, pending, slippage complaints"},
        {"id": "withdrawal", "name": "Withdrawal", "description": "Money withdrawal not processing, stuck, reversed"},
        {"id": "chart_data", "name": "Chart / Data", "description": "Price charts not updating, wrong historical data"},
        {"id": "gtt_order", "name": "GTT / Trigger Order", "description": "GTT not triggering, creation errors"},
        {"id": "margin_shortfall", "name": "Margin / RMS", "description": "Position squared off, margin requirement issues"},
        {"id": "fraud_dispute", "name": "Fraud / Unauthorized", "description": "Unauthorized transaction, account compromised"},
        {"id": "dp_charges", "name": "DP Charges / Fees", "description": "Demat charges, AMC fee, hidden costs"},
        {"id": "ipo_allotment", "name": "IPO Allotment", "description": "IPO not allotted, refund not received"},
        {"id": "pledged_stock", "name": "Pledged Stock", "description": "Pledged shares not visible, pledge release"},
        {"id": "account_locked", "name": "Account Locked", "description": "Account unexpectedly locked, trading restricted"},
        {"id": "notifications", "name": "Notifications", "description": "Order confirmation not received, alerts missing"},
        {"id": "referral_reward", "name": "Referral / Reward", "description": "Referral bonus not credited, cashback missing"},
        {"id": "mf_redemption", "name": "MF Redemption", "description": "MF redemption delay, switch order wrong NAV"},
        {"id": "tax_report", "name": "Tax Report", "description": "Capital gains statement unavailable, P&L mismatch"},
    ],
    "insurtech": [
        {"id": "claim_status", "name": "Claim Status", "description": "Claim not processed, stuck, documents requested repeatedly"},
        {"id": "policy_renewal", "name": "Policy Renewal", "description": "Policy lapsed, renewal premium changed"},
        {"id": "coverage_dispute", "name": "Coverage Dispute", "description": "Claim denied due to exclusion, coverage misunderstanding"},
        {"id": "premium_payment", "name": "Premium Payment", "description": "Payment declined, auto-debit failed"},
        {"id": "nominee_update", "name": "Nominee Update", "description": "Nominee change not reflecting, beneficiary details"},
    ],
    "ecommerce": [
        {"id": "order_tracking", "name": "Order Tracking", "description": "Order not updating, tracking number invalid"},
        {"id": "refund", "name": "Refund", "description": "Refund not processed, partial refund dispute"},
        {"id": "product_quality", "name": "Product Quality", "description": "Damaged product, wrong item delivered"},
        {"id": "cancellation", "name": "Cancellation", "description": "Cannot cancel, cancellation fee dispute"},
        {"id": "return_exchange", "name": "Return / Exchange", "description": "Return not accepted, exchange delayed"},
    ],
    "saas": [
        {"id": "billing", "name": "Billing", "description": "Wrong charge, double billing, plan upgrade issues"},
        {"id": "account_access", "name": "Account Access", "description": "Cannot login, account suspended, SSO failure"},
        {"id": "feature_bug", "name": "Feature Bug", "description": "Feature not working, regression, unexpected behavior"},
        {"id": "data_export", "name": "Data Export", "description": "Export fails, missing data, wrong format"},
        {"id": "integration", "name": "Integration", "description": "Third-party integration broken, webhook failing"},
    ],
    "healthtech": [
        {"id": "appointment", "name": "Appointment", "description": "Cannot book, reschedule, or cancel appointment"},
        {"id": "prescription", "name": "Prescription", "description": "Prescription not available, refill denied"},
        {"id": "lab_report", "name": "Lab Report", "description": "Report delayed, results missing, wrong patient data"},
        {"id": "consultation", "name": "Consultation", "description": "Doctor not available, video call failed"},
        {"id": "insurance_claim", "name": "Insurance Claim", "description": "Claim submission failed, coverage question"},
    ],
}


EXECUTION_AGENT_TAXONOMY = [
    {"id": "api_call_correctness", "name": "API Call Correctness", "description": "Agent calls correct endpoint with correct params"},
    {"id": "parameter_validation", "name": "Parameter Validation", "description": "Agent validates required params before calling"},
    {"id": "idempotency", "name": "Idempotency", "description": "Duplicate calls do not cause double execution"},
    {"id": "error_handling", "name": "Error Handling", "description": "Agent handles API errors gracefully"},
    {"id": "authorization", "name": "Authorization", "description": "Agent checks permissions before executing"},
    {"id": "rollback", "name": "Rollback", "description": "Agent reverses failed transaction"},
    {"id": "rate_limiting", "name": "Rate Limiting", "description": "Agent respects API rate limits"},
    {"id": "confirmation", "name": "Confirmation", "description": "Agent asks confirmation before destructive action"},
]

WORKFLOW_AGENT_TAXONOMY = [
    {"id": "step_ordering", "name": "Step Ordering", "description": "Agent executes steps in correct sequence"},
    {"id": "state_persistence", "name": "State Persistence", "description": "Agent maintains state across workflow steps"},
    {"id": "dependency_resolution", "name": "Dependency Resolution", "description": "Agent resolves step dependencies correctly"},
    {"id": "partial_failure", "name": "Partial Failure", "description": "Agent handles mid-workflow failure without data loss"},
    {"id": "completion_signalling", "name": "Completion Signalling", "description": "Agent signals completion correctly"},
    {"id": "timeout_handling", "name": "Timeout Handling", "description": "Agent handles step timeouts without aborting entire workflow"},
    {"id": "parallel_execution", "name": "Parallel Execution", "description": "Agent correctly executes parallel steps"},
    {"id": "compensation", "name": "Compensation", "description": "Agent undoes completed steps on rollback"},
]

RAG_AGENT_TAXONOMY = [
    {"id": "retrieval_relevance", "name": "Retrieval Relevance", "description": "Agent retrieves relevant documents for query"},
    {"id": "source_attribution", "name": "Source Attribution", "description": "Agent cites sources correctly"},
    {"id": "hallucination_prevention", "name": "Hallucination Prevention", "description": "Agent does not invent facts beyond retrieved context"},
    {"id": "context_window", "name": "Context Window", "description": "Agent handles large context without losing signal"},
    {"id": "query_reformulation", "name": "Query Reformulation", "description": "Agent reformulates queries for better retrieval"},
    {"id": "confidence_scoring", "name": "Confidence Scoring", "description": "Agent expresses uncertainty when appropriate"},
    {"id": "multi_hop_reasoning", "name": "Multi-hop Reasoning", "description": "Agent combines multiple sources for complex queries"},
]

AUTONOMOUS_AGENT_TAXONOMY = [
    {"id": "tool_selection", "name": "Tool Selection", "description": "Agent picks the correct tool for the task"},
    {"id": "task_decomposition", "name": "Task Decomposition", "description": "Agent breaks complex task into subtasks correctly"},
    {"id": "safety_boundary", "name": "Safety Boundary", "description": "Agent stays within allowed tool/scope boundaries"},
    {"id": "loop_detection", "name": "Loop Detection", "description": "Agent detects and escapes infinite loops"},
    {"id": "progress_reporting", "name": "Progress Reporting", "description": "Agent reports progress to user"},
    {"id": "human_handoff", "name": "Human Handoff", "description": "Agent escalates to human when stuck"},
    {"id": "memory_persistence", "name": "Memory Persistence", "description": "Agent remembers context across long sessions"},
]

AGENT_TYPE_TAXONOMIES = {
    AgentType.CONVERSATIONAL: CORE_TAXONOMY,
    AgentType.EXECUTION: {"*": EXECUTION_AGENT_TAXONOMY},
    AgentType.WORKFLOW: {"*": WORKFLOW_AGENT_TAXONOMY},
    AgentType.RAG: {"*": RAG_AGENT_TAXONOMY},
    AgentType.AUTONOMOUS: {"*": AUTONOMOUS_AGENT_TAXONOMY},
}


def get_taxonomy_for_agent(agent_type: AgentType, sector: str | None = None) -> list[dict]:
    taxonomies = AGENT_TYPE_TAXONOMIES.get(agent_type, AGENT_TYPE_TAXONOMIES[AgentType.CONVERSATIONAL])
    if agent_type == AgentType.CONVERSATIONAL and isinstance(taxonomies, dict):
        if sector and sector in taxonomies:
            return taxonomies[sector]
        return taxonomies.get("fintech", [])
    return list(taxonomies.get("*", []))


def get_intents_for_sector(sector_name: str, profile_intents: list[str] | None = None) -> list[dict]:
    tax = CORE_TAXONOMY.get(sector_name, [])
    if not profile_intents:
        return tax
    profile_lower = [i.lower() for i in profile_intents]
    matched = []
    for t in tax:
        name_parts = t["name"].lower()
        desc_parts = t["description"].lower()
        search_space = name_parts + " " + desc_parts
        if any(p in search_space or search_space in p for p in profile_lower):
            matched.append(t)
        elif any(kw in search_space for p in profile_lower for kw in p.split() if len(kw) > 3):
            matched.append(t)
    return matched if matched else tax


def generate_dimension_test_templates(agent_type: AgentType, dimension: TestDimension, sector: str | None = None) -> list[TestCase]:
    templates = []
    taxonomy = get_taxonomy_for_agent(agent_type, sector)
    failure_types = get_failure_types_for_dimension(dimension)

    for intent in taxonomy:
        for ft in failure_types[:2]:
            templates.append(TestCase(
                agent_type=agent_type,
                dimension=dimension,
                intent_match_id=intent["id"],
                intent_match=intent["name"],
                failure_mode=ft,
                scenario_label=f"{intent['id']}:{ft}",
                scenario_description=f"Test {ft} for {intent['name']}",
                severity="medium",
                verification_scenarios=[f"verify_{intent['id']}_{ft}"],
            ))
    return templates
