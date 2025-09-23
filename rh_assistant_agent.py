from typing import TypedDict, List, Union, Literal

# Import the system prompt from the prompts.py file
from prompts import SYSTEM_PROMPT
# Import the tools from the new tools.py file
from tools import tools


from dotenv import load_dotenv
load_dotenv(".env")

# Make sure to set up your environment variables
# before running this script, e.g., for OpenAI:
# os.environ["OPENAI_API_KEY"] = "your-api-key-here"

# Install necessary libraries using uv:
# uv pip install langchain-openai langchain-community langchain langgraph

# LangChain and LangGraph imports
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langgraph.graph import StateGraph, END, START

# ==============================================================================
# 1. Define the Agent's State and Graph Structure
# ==============================================================================
class AgentState(TypedDict):
    """
    Represents the state of our graph.
    The state is a dictionary that tracks the conversation, the current
    discussion stage, and any captured data.
    """
    input: str
    chat_history: List[BaseMessage]
    current_stage: Literal["start", "advancements", "challenges", "achievements", "training_needs", "action_plan", "summary"]
    captured_data: dict


# ==============================================================================
# 2. Define the Agent's Core Logic
# ==============================================================================
# The LLM's brain and decision-making logic.
llm = ChatOpenAI(model="gpt-4o", temperature=0.2)
llm_with_tools = llm.bind_tools(tools)

# The system prompt gives the LLM its persona and instructions.
prompt = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    MessagesPlaceholder(variable_name="chat_history")
])


def call_llm(state: AgentState):
    """
    This is the main 'brain' node. It uses the LLM to decide what to do next.
    It can either call a tool or respond directly to the user.
    """
    print(f"---CALLING LLM AT STAGE: {state['current_stage']}---")
    
    # We combine the system prompt with the current chat history
    messages = prompt.format_messages(chat_history=state['chat_history'])
    response = llm_with_tools.invoke(messages)
    
    # Append the AI's response to the chat history
    state['chat_history'].append(response)
    
    # LangChain's tool-calling logic will create a message with `tool_calls`
    if response.tool_calls:
        print("---LLM DECIDED TO USE A TOOL---")
        # Return the first tool call to be executed
        return {"agent_outcome": response.tool_calls[0]}
    else:
        # If no tool is called, the LLM provides a final answer.
        print("---LLM DECIDED TO RESPOND DIRECTLY---")
        return {"agent_outcome": "final_response"}


def call_tool(state: AgentState):
    """
    This node executes the tool that was chosen by the LLM.
    """
    print("---CALLING TOOL---")
    tool_call = state['agent_outcome']
    tool_name = tool_call['name']
    tool_args = tool_call['args']
    
    # Look up the function to run based on the name from the `tools` list
    tool_to_run = {t.name: t for t in tools}[tool_name]
    tool_output = tool_to_run.invoke(tool_args)
    
    print(f"---TOOL OUTPUT: {tool_output}---")
    
    # The tool output is added to the chat history as a ToolMessage.
    state['chat_history'].append(ToolMessage(content=tool_output, tool_call_id=tool_call['id']))
    
    # Return the tool's output
    return {"tool_output": tool_output}

def route_to_next_stage(state: AgentState):
    """
    This conditional edge routes the conversation to the next logical stage
    or ends the process if the summary is complete.
    """
    # Check the current tool's name to determine the next stage
    last_tool_call_name = state['agent_outcome']['name']
    
    if last_tool_call_name == "document_advancement":
        return "challenges"
    elif last_tool_call_name == "document_challenge":
        return "achievements"
    elif last_tool_call_name == "document_achievement":
        return "training_needs"
    elif last_tool_call_name == "document_training_need":
        return "action_plan"
    elif last_tool_call_name == "document_action_plan":
        return "summary"
    else:
        return "end"


# ==============================================================================
# 3. Build the LangGraph
# ==============================================================================
workflow = StateGraph(AgentState)

# Define the nodes for our state machine
workflow.add_node("advancements", call_llm)
workflow.add_node("challenges", call_llm)
workflow.add_node("achievements", call_llm)
workflow.add_node("training_needs", call_llm)
workflow.add_node("action_plan", call_llm)
workflow.add_node("call_tool", call_tool)
workflow.add_node("summary", call_llm)


# Define the entry point and the transition from there
workflow.add_edge(START, "advancements")
workflow.add_edge("advancements", "call_tool")
workflow.add_edge("challenges", "call_tool")
workflow.add_edge("achievements", "call_tool")
workflow.add_edge("training_needs", "call_tool")
workflow.add_edge("action_plan", "call_tool")


# After a tool call, we use a router to decide the next stage
workflow.add_conditional_edges(
    "call_tool",
    route_to_next_stage,
    {
        "challenges": "challenges",
        "achievements": "achievements",
        "training_needs": "training_needs",
        "action_plan": "action_plan",
        "summary": "summary",
        "end": END,
    }
)

# After the summary is generated, the graph ends
workflow.add_edge("summary", END)

# Compile the graph
app = workflow.compile()
