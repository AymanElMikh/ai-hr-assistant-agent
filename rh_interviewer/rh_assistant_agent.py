import os
from typing import List
from dotenv import load_dotenv

from copy import deepcopy
from langchain_core.messages import SystemMessage

# Load environment variables from a .env file
load_dotenv()

# Import the system prompt from the prompts.py file 
from rh_interviewer.prompts import SYSTEM_PROMPT
# Import the tools from the new tools.py file
from rh_interviewer.tools import tools

# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage, HumanMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END, START
from langgraph.prebuilt import ToolNode
from langgraph.checkpoint.memory import MemorySaver

# Import refactored utils with configuration
from rh_interviewer.utils import (
    build_default_config,
    evaluate_stage_completion,
    get_stage_context,
    generate_follow_up_prompts,
    determine_next_stage,
    should_transition_stage,
    update_stage_after_tool,
    initialize_state,
    print_stage_info,
    validate_environment,
    safe_invoke_graph,
)

from rh_interviewer.models import (
    AgentState,
    GlobalConfig
)

# ==============================================================================
# 1. Configuration and Constants
# ==============================================================================
class Config:
    """Configuration settings for the HR Assistant."""
    MODEL_NAME = "gpt-4o"
    TEMPERATURE = 0.2
    MAX_RETRIES = 3
    CONVERSATION_MEMORY = True
    LOG_LEVEL = "INFO"
    
    # Transition thresholds - now configurable
    MIN_COMPLETENESS_SCORE = 0.7
    FORCE_TRANSITION_INTERACTIONS = 6
    EMERGENCY_TRANSITION_SCORE = 0.5

# Get the global configuration
global_config = build_default_config()

# ==============================================================================
# 2. Define the Agent's Core Logic
# ==============================================================================
# The LLM's brain and decision-making logic.
llm = ChatOpenAI(
    model=Config.MODEL_NAME, 
    temperature=Config.TEMPERATURE,
    api_key=os.getenv("OPENAI_API_KEY")
)
llm_with_tools = llm.bind_tools(tools)

# The system prompt gives the LLM its persona and instructions.
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="messages")
])

# Create tool node for handling tool executions
tool_node = ToolNode(tools)

def should_continue(state: AgentState):
    """
    Conditional edge to determine if we should continue to tools, update the stage, or end.
    Uses configuration-driven logic to reduce hardcoded conditions.
    """
    messages = state["messages"]
    last_message = messages[-1]

    # Check if the LLM has requested a tool call
    if last_message.tool_calls:
        return "tools"
    
    # Check for stage transition using configured logic
    current_stage = state["current_stage"]
    next_stage = state["next_stage"]
    
    if next_stage != current_stage:
        print("---TEXT-BASED STAGE TRANSITION DETECTED---")
        return "update_stage"
        
    return "end"

def call_model(state: AgentState):
    """
    Improved call_model that uses configuration-driven logic and reduces hardcoded strings.
    """
    state_copy = deepcopy(state)
    original_stage = state_copy["current_stage"]
    interaction_count = state_copy.get("interaction_count", 0)
    
    print(f"---CALLING MODEL AT STAGE: {original_stage} (Interaction {interaction_count + 1})---")

    # Extract last user message more robustly
    last_user_message = _extract_last_user_message(state_copy.get("messages", []))

    # Check for natural transitions using configuration
    should_transition, target_stage = should_transition_stage(state_copy, last_user_message, global_config)
    just_signaled_transition = False
    
    if should_transition and target_stage and target_stage != original_stage:
        print(f"---NATURAL STAGE TRANSITION SIGNALLED: {original_stage} -> {target_stage}---")
        state_copy["next_stage"] = target_stage
        just_signaled_transition = True
    
    # Evaluate stage completion using configuration
    completion_metrics = evaluate_stage_completion(state_copy, global_config)
    print(f"Stage completion: {completion_metrics['completeness_score']:.2f}, Ready: {completion_metrics['ready_for_next']}")

    # Build messages for the LLM
    messages = state_copy.get("messages", []).copy()

    # Add stage-specific system context using configuration
    stage_context = get_stage_context(original_stage, global_config)
    if stage_context:
        context_text = stage_context

        # Add follow-up prompts if needed
        if (not completion_metrics.get("ready_for_next", False) 
            and interaction_count >= 1 
            and not should_transition):
            follow_up_prompts = generate_follow_up_prompts(original_stage, completion_metrics, global_config)
            if follow_up_prompts:
                context_text += f"\n\n{follow_up_prompts}"

        # Add transition messages using configuration
        if just_signaled_transition:
            context_text = _get_transition_message(target_stage, global_config) or context_text

        messages.append(SystemMessage(content=context_text))

    # Format and invoke the LLM with error handling
    formatted_messages = prompt.format_messages(messages=messages)
    try:
        response = llm_with_tools.invoke(formatted_messages)
    except Exception as e:
        print(f"LLM invocation error: {e}")
        return _create_error_state(state_copy, original_stage, interaction_count, just_signaled_transition)

    # Determine next stage using configuration
    next_stage = determine_next_stage(response, original_stage, completion_metrics, last_user_message, global_config)

    # Update stage messages safely
    stage_messages = _update_stage_messages(state_copy, original_stage, last_user_message)

    # Append assistant response to full history
    messages.append(response)

    # Calculate new interaction count
    new_interaction_count = 0 if just_signaled_transition else (interaction_count + 1)

    return {
        "messages": messages,
        "current_stage": original_stage,
        "next_stage": state_copy.get("next_stage", next_stage),
        "stage_completion_metrics": {original_stage: completion_metrics},
        "interaction_count": new_interaction_count,
        "stage_messages": stage_messages
    }

def _extract_last_user_message(messages: List[BaseMessage]) -> str:
    """Extract the last user message from the message history."""
    for msg in reversed(messages):
        role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
        content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
        if role in ("user", "human") or isinstance(msg, HumanMessage):
            if content:
                return content
    return ""

def _get_transition_message(target_stage: str, config: GlobalConfig) -> str:
    """Get transition message for a target stage from configuration."""
    transition_messages = {
        "challenges": "Great! Now let's discuss any challenges or obstacles you've faced. What specific difficulties have you encountered in your role?",
        "achievements": "Excellent! Now let's talk about your key achievements and accomplishments. What are you most proud of accomplishing?",
        "training_needs": "Perfect! Now let's identify areas for your professional development. What skills or knowledge areas would you like to improve?",
        "action_plan": "Great! Finally, let's create an action plan for your continued growth. What specific goals would you like to set?",
        "summary": "Thank you! Let me now provide a comprehensive summary of our discussion."
    }
    return transition_messages.get(target_stage, "")

def _create_error_state(state_copy: dict, original_stage: str, interaction_count: int, just_signaled_transition: bool) -> dict:
    """Create a safe error state that preserves history."""
    return {
        "messages": state_copy.get("messages", []),
        "current_stage": original_stage,
        "next_stage": state_copy.get("next_stage", original_stage),
        "stage_completion_metrics": {original_stage: {}},
        "interaction_count": 0 if just_signaled_transition else interaction_count,
        "stage_messages": state_copy.get("stage_messages", {})
    }

def _update_stage_messages(state_copy: dict, original_stage: str, last_user_message: str) -> dict:
    """Update stage messages safely."""
    stage_messages = deepcopy(state_copy.get("stage_messages", {}))
    stage_messages.setdefault(original_stage, [])
    
    if last_user_message and not last_user_message.startswith("[SYSTEM CONTEXT:"):
        stage_messages[original_stage].append(last_user_message)
    
    return stage_messages

# ==============================================================================
# 3. Build the LangGraph with Optimized Structure
# ==============================================================================
def create_graph():
    """Creates and compiles the LangGraph workflow."""
    workflow = StateGraph(AgentState)
    
    # Add nodes
    workflow.add_node("agent", call_model)
    workflow.add_node("tools", tool_node)
    workflow.add_node("update_stage", lambda state: update_stage_after_tool(state, global_config))
    
    # Set the entrypoint
    workflow.add_edge(START, "agent")
    
    # Add conditional edges
    workflow.add_conditional_edges(
        "agent",
        should_continue,
        {
            "tools": "tools",
            "update_stage": "update_stage",
            "end": END,
        }
    )
    
    # After tools, update stage and continue
    workflow.add_edge("tools", "update_stage")
    workflow.add_edge("update_stage", "agent")
    
    # Add memory for conversation persistence
    memory = MemorySaver()
    
    return workflow.compile(checkpointer=memory)

# Create the compiled app
app = create_graph()

# ==============================================================================
# 4. Main Execution Block (for running the app)
# ==============================================================================
if __name__ == "__main__":
    try:
        validate_environment(global_config)
        
        print_stage_info(global_config.initial_stage, global_config)
        
        # Initialize state using configuration
        current_state = initialize_state(
            global_config,
            initial_message="Hello! Let's start with your professional advancements and milestones since your last review."
        )
        
        print("AI:", current_state["messages"][0].content)
        
        # Define conversation turns (could be moved to config)
        conversation_turns = [
            "I led a new project to integrate our customer service and sales databases, which improved our lead conversion rate by 15% in Q3. I also mentored two junior developers on the project.",
            "I learned Java and Python for web development and data analysis projects. I also automated a CV generation tool that has been a huge help for our users.",
            "Yes, I was facing some challenges in finding information about documentation of the tools I used to develop with. This was a difficult obstacle to overcome."
        ]
        
        # Process each turn of the conversation
        for i, user_input in enumerate(conversation_turns):
            print(f"\n--- Turn {i+1} ---")
            print(f"User: {user_input}")
            
            current_state["messages"].append(HumanMessage(content=user_input))
            result, error = safe_invoke_graph(app, current_state)
            
            if result:
                print("AI:", result["messages"][-1].content)
                print_stage_info(result["current_stage"], global_config)
                current_state = result
            else:
                print("An error occurred during execution.")
                break

    except EnvironmentError as e:
        print(f"Warning: {e}")