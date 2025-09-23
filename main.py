import os
from langchain_core.messages import AIMessage, HumanMessage

# Import the compiled graph and the agent's state definition
from rh_assistant_agent import app, AgentState

# ==============================================================================
# Main Application Loop
# ==============================================================================
if __name__ == "__main__":
    print("Welcome to the AI HR Assistant for Annual Performance Reviews!")
    print("Let's start by discussing your professional advancements since the last review.")
    print("Type 'exit' to quit.")
    print("-----------------------------------")
    
    # We will maintain the conversation state across turns
    current_state: AgentState = {
        "input": None,
        "chat_history": [AIMessage(content="Hello! Let's start with your professional advancements and milestones since your last review.")],
        "current_stage": "advancements",
        "captured_data": {}
    }
    
    while True:
        user_input = input("You: ")
        if user_input.lower() == "exit":
            break
        
        # Update the state with the new user input
        current_state["input"] = user_input
        current_state["chat_history"].append(HumanMessage(content=user_input))
        
        # Invoke the graph with the updated state
        next_state = app.invoke(current_state)
        
        # The new state is the result of the graph's execution
        current_state.update(next_state)
        
        # The final message is the last message in the chat history
        final_response = current_state['chat_history'][-1].content
        print(f"Assistant: {final_response}")
        print("-----------------------------------")
        
        # Update the current stage based on the tool call
        if "agent_outcome" in current_state and isinstance(current_state["agent_outcome"], dict):
            last_tool_call_name = current_state["agent_outcome"]["name"]
            
            if last_tool_call_name == "document_advancement":
                current_state["current_stage"] = "challenges"
            elif last_tool_call_name == "document_challenge":
                current_state["current_stage"] = "achievements"
            elif last_tool_call_name == "document_achievement":
                current_state["current_stage"] = "training_needs"
            elif last_tool_call_name == "document_training_need":
                current_state["current_stage"] = "action_plan"
            elif last_tool_call_name == "document_action_plan":
                current_state["current_stage"] = "summary"
            else:
                pass # Stay in the same stage or end
