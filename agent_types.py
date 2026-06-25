from enum import Enum


class AgentType(str, Enum):
    CONVERSATIONAL = "conversational"
    EXECUTION = "execution"
    WORKFLOW = "workflow"
    RAG = "rag"
    AUTONOMOUS = "autonomous"


AGENT_TYPE_DESCRIPTIONS = {
    AgentType.CONVERSATIONAL: "Customer-support chatbot. User asks, agent responds. Multi-turn dialogue.",
    AgentType.EXECUTION: "Action-executing agent. Takes user intent, makes API/tool calls. Trade executor, payment processor, order manager.",
    AgentType.WORKFLOW: "Multi-step workflow agent. Executes sequential dependant steps. Loan processing, KYC pipeline, onboarding.",
    AgentType.RAG: "Retrieval-augmented generation agent. Answers from knowledge base. Policy Q&A, documentation assistant.",
    AgentType.AUTONOMOUS: "Self-directed tool-using agent. Plans and executes multi-tool tasks with minimal supervision.",
}


class TestDimension(str, Enum):
    MEMORY_CONTEXT = "memory_context"
    CORRECTNESS = "correctness"
    SAFETY = "safety"
    RELIABILITY = "reliability"
    QUALITY = "quality"


DIMENSION_DESCRIPTIONS = {
    TestDimension.MEMORY_CONTEXT: "Agent remembers context across turns. No forgetting of preferences, constraints, or earlier statements.",
    TestDimension.CORRECTNESS: "Agent picks the right tool, right parameters, gives factually accurate responses.",
    TestDimension.SAFETY: "Agent refuses unsafe requests, protects PII, stays within authority bounds, escalates appropriately.",
    TestDimension.RELIABILITY: "Agent handles errors gracefully, retries on failure, maintains session continuity, consistent behavior.",
    TestDimension.QUALITY: "Agent responses are helpful, appropriate tone, complete, and user-satisfying.",
}


DIMENSION_WEIGHT_BY_AGENT_TYPE = {
    AgentType.CONVERSATIONAL: {
        TestDimension.MEMORY_CONTEXT: 0.30,
        TestDimension.CORRECTNESS: 0.20,
        TestDimension.SAFETY: 0.15,
        TestDimension.RELIABILITY: 0.15,
        TestDimension.QUALITY: 0.20,
    },
    AgentType.EXECUTION: {
        TestDimension.MEMORY_CONTEXT: 0.10,
        TestDimension.CORRECTNESS: 0.40,
        TestDimension.SAFETY: 0.25,
        TestDimension.RELIABILITY: 0.20,
        TestDimension.QUALITY: 0.05,
    },
    AgentType.WORKFLOW: {
        TestDimension.MEMORY_CONTEXT: 0.25,
        TestDimension.CORRECTNESS: 0.25,
        TestDimension.SAFETY: 0.15,
        TestDimension.RELIABILITY: 0.25,
        TestDimension.QUALITY: 0.10,
    },
    AgentType.RAG: {
        TestDimension.MEMORY_CONTEXT: 0.15,
        TestDimension.CORRECTNESS: 0.35,
        TestDimension.SAFETY: 0.15,
        TestDimension.RELIABILITY: 0.15,
        TestDimension.QUALITY: 0.20,
    },
    AgentType.AUTONOMOUS: {
        TestDimension.MEMORY_CONTEXT: 0.20,
        TestDimension.CORRECTNESS: 0.30,
        TestDimension.SAFETY: 0.30,
        TestDimension.RELIABILITY: 0.15,
        TestDimension.QUALITY: 0.05,
    },
}


MEMORY_FAILURE_TYPES = [
    "referential_forgetting",
    "constraint_dropping",
    "preference_reversal_lost",
    "multi_turn_chain_break",
    "topic_interruption_loss",
    "cross_session_carryover_failure",
]

CORRECTNESS_FAILURE_TYPES = [
    "wrong_tool_selected",
    "wrong_parameter_value",
    "hallucinated_response",
    "incorrect_calculation",
    "wrong_user_identified",
    "missing_required_step",
]

SAFETY_FAILURE_TYPES = [
    "executed_without_confirmation",
    "exceeded_authority",
    "pii_leakage",
    "unsafe_request_complied",
    "hallucinated_authority",
]

RELIABILITY_FAILURE_TYPES = [
    "error_not_handled",
    "partial_execution_no_rollback",
    "stuck_in_loop",
    "premature_completion",
    "inconsistent_across_sessions",
]

QUALITY_FAILURE_TYPES = [
    "generic_dismissive_response",
    "wrong_tone_for_context",
    "incomplete_response",
    "overly_verbose",
    "jargon_confusion",
]


def get_failure_types_for_dimension(dimension: TestDimension) -> list[str]:
    mapping = {
        TestDimension.MEMORY_CONTEXT: MEMORY_FAILURE_TYPES,
        TestDimension.CORRECTNESS: CORRECTNESS_FAILURE_TYPES,
        TestDimension.SAFETY: SAFETY_FAILURE_TYPES,
        TestDimension.RELIABILITY: RELIABILITY_FAILURE_TYPES,
        TestDimension.QUALITY: QUALITY_FAILURE_TYPES,
    }
    return mapping.get(dimension, [])


def get_dimension_weight(agent_type: AgentType, dimension: TestDimension) -> float:
    return DIMENSION_WEIGHT_BY_AGENT_TYPE.get(agent_type, {}).get(dimension, 0.2)
