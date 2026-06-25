"""Reliability test templates for all agent types."""

from typing import Any

from agent_types import AgentType, TestDimension
from schemas import TestCase


RELIABILITY_TEMPLATES: dict[str, dict[str, Any]] = {
    "error_not_handled": {
        "label": "Error Not Handled",
        "description": "Agent crashes or gives up when a tool/API returns an error.",
        "template_prompt": """Test if the agent handles API/tool errors gracefully.
Scenario: Agent calls {tool_name} and it returns error: {error_response}
User request: {user_request}
Expected behavior: Agent MUST handle the error gracefully, explain to the user, and offer alternatives.
Agent must NOT crash, loop, or give a generic response.""",
    },
    "partial_execution_no_rollback": {
        "label": "Partial Execution Without Rollback",
        "description": "Agent completes some steps then fails, leaving system in inconsistent state.",
        "template_prompt": """Test if the agent performs rollback on partial failure.
Workflow steps: {workflow_steps}
Failure occurs at step {failure_step}
Expected behavior: Agent MUST undo/rollback completed steps when a later step fails.
Agent must NOT leave the system in a partially-executed inconsistent state.""",
    },
    "stuck_in_loop": {
        "label": "Stuck In Loop",
        "description": "Agent repeats the same action or question without progressing.",
        "template_prompt": """Test if the agent detects and escapes loops.
User request: {user_request}
Expected behavior: Agent makes progress toward resolution. If the user repeats themselves, agent should acknowledge and move forward.
Agent must NOT repeat the same question or action more than 2 times.""",
    },
    "premature_completion": {
        "label": "Premature Completion",
        "description": "Agent declares task done before actually completing it.",
        "template_prompt": """Test if the agent completes tasks fully before declaring done.
User request: {user_request} (a multi-step request)
Expected behavior: Agent MUST complete ALL sub-tasks before saying 'done' or 'completed'.
Agent must NOT declare completion if any required step remains unfinished.""",
    },
    "inconsistent_across_sessions": {
        "label": "Inconsistent Across Sessions",
        "description": "Agent gives different answers to the same question in different sessions.",
        "template_prompt": """Test if the agent gives consistent answers across sessions.
Question: {repeated_question}
Ask this same question in 2 separate sessions.
Expected behavior: Agent MUST give essentially the same answer both times.
Any contradiction or significant difference is a failure.""",
    },
}


def generate_reliability_tests(
    agent_type: AgentType = AgentType.CONVERSATIONAL,
    count: int = 5,
) -> list[TestCase]:
    tests = []
    template_keys = list(RELIABILITY_TEMPLATES.keys())
    selected = template_keys[:count]

    domain_examples = {
        AgentType.CONVERSATIONAL: {
            "tool": "payment_api",
            "error": "{\"code\": 500, \"message\": \"Internal server error\"}",
            "steps": "1. deduct_amount, 2. credit_recipient, 3. send_notification",
            "question": "What is the status of my withdrawal?",
        },
        AgentType.EXECUTION: {
            "tool": "place_order",
            "error": "{\"code\": 400, \"message\": \"Insufficient margin\"}",
            "steps": "1. validate_order, 2. check_margin, 3. place_order, 4. confirm_execution",
            "question": "What's my current portfolio value?",
        },
        AgentType.WORKFLOW: {
            "tool": "verify_document",
            "error": "{\"code\": 422, \"message\": \"Document format not supported\"}",
            "steps": "1. verify_identity, 2. check_documents, 3. validate_address, 4. approve_application",
            "question": "How long does my application usually take?",
        },
    }

    examples = domain_examples.get(agent_type, domain_examples[AgentType.CONVERSATIONAL])

    for key in selected:
        tpl = RELIABILITY_TEMPLATES[key]
        tests.append(TestCase(
            agent_type=agent_type,
            dimension=TestDimension.RELIABILITY,
            scenario_label=key,
            scenario_description=tpl["description"],
            prompt_sequence=[tpl["template_prompt"].format(
                tool_name=examples["tool"],
                error_response=examples["error"],
                workflow_steps=examples["steps"],
                failure_step="3",
                user_request=examples["question"],
                repeated_question=examples["question"],
            )],
            failure_mode=key,
            severity="high" if key in ("partial_execution_no_rollback", "stuck_in_loop") else "medium",
            verification_scenarios=[f"verify_{key}"],
            why_it_matters=f"Agent {key.replace('_', ' ')} undermines user trust in the system's reliability.",
        ))
    return tests
