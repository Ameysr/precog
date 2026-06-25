"""Memory/context-retention test templates and evaluation for all agent types.

6 context-loss patterns:
1. referential_forgetting  - agent forgets info user mentioned earlier
2. constraint_dropping     - agent ignores earlier constraints
3. preference_reversal     - agent loses track of latest preference
4. multi_turn_chain_break  - agent loses connection across 5+ turns
5. topic_interruption_loss - agent forgets context after topic switch
6. cross_session_carryover - agent doesn't persist info across sessions
"""

import json
from typing import Any

from agent_types import AgentType, TestDimension
from schemas import TestCase


MEMORY_TEMPLATES: dict[str, dict[str, Any]] = {
    "referential_forgetting": {
        "label": "Referential Forgetting",
        "description": "Agent forgets a specific detail the user mentioned earlier in the conversation.",
        "template_prompt": """You are testing an agent's ability to retain referential context.
Start a conversation where the user provides a specific detail (e.g., account number, date, preference).
After {distractor_turns} turns of unrelated discussion, circle back and ask the agent to recall that detail.
The agent MUST remember the exact detail without the user repeating it.""",
        "distractor_turns": 3,
        "expected_behavior": "Agent recalls the exact detail from earlier in the conversation without user repeating it.",
        "forbidden_behavior": "Agent says 'I don't know' or 'You didn't mention that' or asks user to repeat.",
    },
    "constraint_dropping": {
        "label": "Constraint Dropping",
        "description": "User sets a constraint early, then agent ignores it later.",
        "template_prompt": """You are testing an agent's ability to remember user-imposed constraints.
The user provides a firm constraint early (e.g., "I only want options under ₹1000", "Don't touch my demat account").
After {distractor_turns} turns, the user asks for suggestions or actions that could violate the constraint.
The agent MUST remember and respect the original constraint.""",
        "distractor_turns": 2,
        "expected_behavior": "Agent respects the original constraint and does not suggest/do anything violating it.",
        "forbidden_behavior": "Agent suggests options or takes actions that violate the constraint set by user.",
    },
    "preference_reversal": {
        "label": "Preference Reversal Tracking",
        "description": "User changes their preference mid-conversation and agent must track the latest.",
        "template_prompt": """You are testing an agent's ability to track changing user preferences.
The user states a preference (e.g., "I prefer growth funds"), but then reverses it later (e.g., "Actually no, I want dividend funds").
After {distractor_turns} turns, ask about their investment preference.
The agent MUST use the LATEST preference, not the original one.""",
        "distractor_turns": 2,
        "expected_behavior": "Agent correctly identifies and uses the LATEST preference the user stated.",
        "forbidden_behavior": "Agent uses the original/outdated preference instead of the latest one.",
    },
    "multi_turn_chain_break": {
        "label": "Multi-Turn Chain Break",
        "description": "Agent loses connection between early and late conversation turns in a 5+ turn chain.",
        "template_prompt": """You are testing an agent's ability to maintain coherence across a long conversation chain.
Create a {num_steps}-step workflow where each step depends on information from step 1.
Step 1: User provides a unique identifier or key detail.
Steps 2-{num_minus_1}: Intermediate processing steps with the agent.
Step {num_steps}: User asks the agent to reference the detail from step 1.
The agent MUST still connect the final step back to step 1.""",
        "num_steps": 6,
        "expected_behavior": "Agent connects the final step back to information provided in step 1.",
        "forbidden_behavior": "Agent treats the final step as a new/isolated request, disconnected from earlier context.",
    },
    "topic_interruption_loss": {
        "label": "Topic Interruption Recovery",
        "description": "User switches to an unrelated topic, then returns to the original topic — agent forgets the original context.",
        "template_prompt": """You are testing an agent's ability to recover context after a topic interruption.
Turn 1: User starts discussing Topic A with specific details (account info, issue description).
Turn 2-3: User abruptly switches to Topic B (completely unrelated) and has a full sub-conversation.
Turn 4: User returns to Topic A and references the details from Turn 1.
The agent MUST smoothly pick up Topic A context without asking the user to repeat themselves.""",
        "distractor_turns": 2,
        "expected_behavior": "Agent seamlessly resumes Topic A context after the interruption without asking user to repeat.",
        "forbidden_behavior": "Agent says 'What were we discussing?' or asks user to re-explain Topic A details.",
    },
    "cross_session_carryover": {
        "label": "Cross-Session Carryover Failure",
        "description": "User provides information in session 1, then in a new session, agent doesn't remember it.",
        "template_prompt": """You are testing an agent's ability to carry context across sessions.
Session 1: User provides important profile information (e.g., "I'm a student investor", "My PAN is ABCDE1234F").
End session.
Session 2: User starts a new session and asks about something related to the profile info from session 1.
The agent MUST recall the session 1 information and use it to provide contextually aware responses.""",
        "expected_behavior": "Agent recalls session 1 information in session 2 without the user repeating it.",
        "forbidden_behavior": "Agent treats session 2 as entirely fresh, asks for information already provided in session 1.",
    },
}


def generate_memory_tests(
    agent_type: AgentType = AgentType.CONVERSATIONAL,
    sector: str | None = None,
    count: int = 6,
) -> list[TestCase]:
    tests = []
    template_keys = list(MEMORY_TEMPLATES.keys())
    selected = template_keys[:count]

    for key in selected:
        tpl = MEMORY_TEMPLATES[key]
        turn_count = tpl.get("distractor_turns", 3)
        num_steps = tpl.get("num_steps", 6)

        tests.append(TestCase(
            agent_type=agent_type,
            dimension=TestDimension.MEMORY_CONTEXT,
            scenario_label=key,
            scenario_description=tpl["description"],
            prompt_sequence=[tpl["template_prompt"].format(
                distractor_turns=turn_count,
                num_steps=num_steps,
                num_minus_1=num_steps - 1,
            )],
            expected_response_patterns=[tpl["expected_behavior"]],
            forbidden_response_patterns=[tpl["forbidden_behavior"]],
            context_requirements=[
                "must_recall_earlier_information",
                "must_not_ask_user_to_repeat",
                "must_maintain_coherence_across_turns",
            ],
            failure_mode=key,
            severity="high" if key in ("cross_session_carryover",) else "medium",
            verification_scenarios=[
                f"verify_{key}_no_context_loss",
                f"verify_{key}_fluid_resumption",
            ],
            why_it_matters=f"Agent {key.replace('_', ' ')} means users must repeat themselves, destroying trust and efficiency.",
        ))
    return tests


def evaluate_context_retention(
    conversation: list[dict],
    context_requirements: list[str],
) -> dict[str, Any]:
    """LLM-as-judge evaluation of context retention.
    
    Args:
        conversation: list of {"role": "user"/"assistant", "content": str}
        context_requirements: what the agent should remember
    
    Returns:
        dict with scores and analysis
    """
    from utils import call_llm
    from pydantic import BaseModel

    class ContextEval(BaseModel):
        context_retained: bool
        retention_score: float
        evidence: list[str]
        failures: list[str]
        explanation: str

    conv_text = json.dumps(conversation, indent=2)
    req_text = "\n".join(f"- {r}" for r in context_requirements)

    prompt = f"""You are evaluating an AI agent's context retention capability.

CONTEXT REQUIREMENTS (what the agent should have remembered):
{req_text}

CONVERSATION HISTORY:
{conv_text}

Evaluate:
1. Did the agent retain context across the entire conversation?
2. Score 0.0 - 1.0 how much context was retained (1.0 = perfect)
3. List specific evidence of context retention
4. List specific failures where context was lost
5. Brief explanation

Return valid JSON:
{{
    "context_retained": true/false,
    "retention_score": 0.0-1.0,
    "evidence": ["list of specific lines showing retention"],
    "failures": ["list of specific failures"],
    "explanation": "brief explanation"
}}"""

    try:
        result = call_llm(prompt, ContextEval)
        return {
            "context_retained": result.context_retained,
            "retention_score": result.retention_score,
            "evidence": result.evidence,
            "failures": result.failures,
            "explanation": result.explanation,
        }
    except Exception as e:
        return {
            "context_retained": False,
            "retention_score": 0.0,
            "evidence": [],
            "failures": [str(e)],
            "explanation": f"Evaluation failed: {e}",
        }
