import json
from langchain_core.tools import tool
from typing import TypedDict, List, Union, Literal

# ==============================================================================
# 2. Define the Tools for the HR Assistant (Dummy Functionality)
# ==============================================================================
# These tools will be called by the LLM to capture and "save" the interview data.
# In the MVP, they just print to the console. Later, they will save to a database.

@tool
def document_advancement(description: str) -> str:
    """
    Documents a significant professional advancement or milestone.
    Call this tool when the employee describes their progress since the last review.
    """
    print(f"--- TOOL CALLED: Documenting Advancement ---")
    print(f"   Advancement: {description}")
    return "Advancement successfully documented. Please proceed to the next topic."

@tool
def document_challenge(description: str) -> str:
    """
    Documents a challenge or obstacle the employee has faced.
    Call this tool when the employee describes a challenge they encountered.
    """
    print(f"--- TOOL CALLED: Documenting Challenge ---")
    print(f"   Challenge: {description}")
    return "Challenge successfully documented. Moving on."

@tool
def document_achievement(description: str) -> str:
    """
    Documents a key achievement or success.
    Call this tool when the employee highlights a key achievement.
    """
    print(f"--- TOOL CALLED: Documenting Achievement ---")
    print(f"   Achievement: {description}")
    return "Achievement successfully documented. What else can we add?"

@tool
def document_training_need(training_type: str, reason: str) -> str:
    """
    Documents a specific training or professional development need.
    Call this tool when the employee mentions a formation or skill they need to learn.
    """
    print(f"--- TOOL CALLED: Documenting Training Need ---")
    print(f"   Training Type: {training_type}, Reason: {reason}")
    return "Training need documented. Is there any other support you require?"

@tool
def document_action_plan(goal: str, deadline: str, next_steps: str) -> str:
    """
    Documents a concrete, time-bound action plan for the employee.
    Call this tool to finalize a plan for the upcoming year.
    """
    print(f"--- TOOL CALLED: Documenting Action Plan ---")
    print(f"   Goal: {goal}, Deadline: {deadline}, Next Steps: {next_steps}")
    return "Action plan documented. Thank you, let's now summarize our discussion."


# List of all tools available to the agent
tools = [
    document_advancement,
    document_challenge,
    document_achievement,
    document_training_need,
    document_action_plan
]
