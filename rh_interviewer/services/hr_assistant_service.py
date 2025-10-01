import os  # IMPORTANT : Ajouter l'importation de 'os'
from typing import List, Tuple, Optional, Dict, Any
from copy import deepcopy
from flask import current_app
from langchain_core.messages import SystemMessage, BaseMessage, HumanMessage

# Import the system prompt from the prompts.py file 
from rh_interviewer.prompts.system_prompt import SYSTEM_PROMPT
# Import the DocumentTools class
from rh_interviewer.tools.document_tools import DocumentTools
# Import the InterviewService
from rh_interviewer.services.interview_service import InterviewService

# LangChain and LangGraph imports
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

from rh_interviewer.schemas import (
    AgentState,
    GlobalConfig
)

# ==============================================================================
# 🎯 Core HRAssistantService Class
# ==============================================================================

class HRAssistantService:
    """Service class for HR Assistant functionality."""
    
    def __init__(self, interview_service: InterviewService):
        """Initialize the HR Assistant service with dependency injection."""
        self.interview_service = interview_service
        
        # Create DocumentTools instance with injected service
        document_tools = DocumentTools(self.interview_service)
        self.tools = document_tools.tools
        
        self.config = self._build_config()
        self.global_config = build_default_config()
        self.llm = self._setup_llm()  # L'initialisation du LLM se produit ici
        self.llm_with_tools = self.llm.bind_tools(self.tools)
        self.prompt = self._setup_prompt()
        self.tool_node = ToolNode(self.tools)
        self.app = self._create_graph()
        
        # Note: Environment validation is handled at app startup in run.py
    
    def _build_config(self):
        """Build configuration for the service."""
        class Config:
            MODEL_NAME = "gpt-4o"
            TEMPERATURE = 0.2
            MAX_RETRIES = 3
            CONVERSATION_MEMORY = True
            LOG_LEVEL = "INFO"
            MIN_COMPLETENESS_SCORE = 0.7
            FORCE_TRANSITION_INTERACTIONS = 6
            EMERGENCY_TRANSITION_SCORE = 0.5
        
        return Config()
    
    def _setup_llm(self) -> ChatOpenAI:
        """
        Setup the language model using Flask configuration or os.environ.
        Retrieves the OpenAI API key from the most reliable source during startup.
        """
        # 🎯 CORRECTION: Tenter de récupérer la clé API directement depuis os.environ.
        # Nous savons que run.py charge l'environnement correctement.
        api_key = os.environ.get('OPENAI_API_KEY')
        
        # Bien que nous ayons corrigé run.py, nous gardons la vérification
        # car elle est spécifique à ce service.
        if not api_key:
            # Le message d'erreur est plus précis maintenant.
            raise ValueError(
                "OPENAI_API_KEY not found in environment variables. "
                "Please ensure it's set in your .env file and re-run the application."
            )
        
        return ChatOpenAI(
            model=self.config.MODEL_NAME, 
            temperature=self.config.TEMPERATURE,
            api_key=api_key  # On passe la clé explicitement à ChatOpenAI
        )
    
    def _setup_prompt(self) -> ChatPromptTemplate:
        """Setup the chat prompt template."""
        return ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            MessagesPlaceholder(variable_name="messages")
        ])
    
    def _should_continue(self, state: AgentState) -> str:
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
    
    def _call_model(self, state: AgentState) -> Dict[str, Any]:
        """
        Improved call_model that uses configuration-driven logic and reduces hardcoded strings.
        """
        state_copy = deepcopy(state)
        original_stage = state_copy["current_stage"]
        interaction_count = state_copy.get("interaction_count", 0)
        
        print(f"---CALLING MODEL AT STAGE: {original_stage} (Interaction {interaction_count + 1})---")

        # Extract last user message more robustly
        last_user_message = self._extract_last_user_message(state_copy.get("messages", []))

        # Check for natural transitions using configuration
        should_transition, target_stage = should_transition_stage(state_copy, last_user_message, self.global_config)
        just_signaled_transition = False
        
        if should_transition and target_stage and target_stage != original_stage:
            print(f"---NATURAL STAGE TRANSITION SIGNALLED: {original_stage} -> {target_stage}---")
            state_copy["next_stage"] = target_stage
            just_signaled_transition = True
        
        # Evaluate stage completion using configuration
        completion_metrics = evaluate_stage_completion(state_copy, self.global_config)
        print(f"Stage completion: {completion_metrics['completeness_score']:.2f}, Ready: {completion_metrics['ready_for_next']}")

        # Build messages for the LLM
        messages = state_copy.get("messages", []).copy()

        # Add stage-specific system context using configuration
        stage_context = get_stage_context(original_stage, self.global_config)
        if stage_context:
            context_text = stage_context

            # Add follow-up prompts if needed
            if (not completion_metrics.get("ready_for_next", False) 
                and interaction_count >= 1 
                and not should_transition):
                follow_up_prompts = generate_follow_up_prompts(original_stage, completion_metrics, self.global_config)
                if follow_up_prompts:
                    context_text += f"\n\n{follow_up_prompts}"

            # Add transition messages using configuration
            if just_signaled_transition:
                context_text = self._get_transition_message(target_stage, self.global_config) or context_text

            messages.append(SystemMessage(content=context_text))

        # Format and invoke the LLM with error handling
        formatted_messages = self.prompt.format_messages(messages=messages)
        try:
            response = self.llm_with_tools.invoke(formatted_messages)
        except Exception as e:
            print(f"LLM invocation error: {e}")
            return self._create_error_state(state_copy, original_stage, interaction_count, just_signaled_transition)

        # Determine next stage using configuration
        next_stage = determine_next_stage(response, original_stage, completion_metrics, last_user_message, self.global_config)

        # Update stage messages safely
        stage_messages = self._update_stage_messages(state_copy, original_stage, last_user_message)

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
    
    def _extract_last_user_message(self, messages: List[BaseMessage]) -> str:
        """Extract the last user message from the message history."""
        for msg in reversed(messages):
            role = getattr(msg, "role", None) or (msg.get("role") if isinstance(msg, dict) else None)
            content = getattr(msg, "content", None) or (msg.get("content") if isinstance(msg, dict) else None)
            if role in ("user", "human") or isinstance(msg, HumanMessage):
                if content:
                    return content
        return ""
    
    def _get_transition_message(self, target_stage: str, config: GlobalConfig) -> str:
        """Get transition message for a target stage from configuration."""
        transition_messages = {
            "challenges": "Great! Now let's discuss any challenges or obstacles you've faced. What specific difficulties have you encountered in your role?",
            "achievements": "Excellent! Now let's talk about your key achievements and accomplishments. What are you most proud of accomplishing?",
            "training_needs": "Perfect! Now let's identify areas for your professional development. What skills or knowledge areas would you like to improve?",
            "action_plan": "Great! Finally, let's create an action plan for your continued growth. What specific goals would you like to set?",
            "summary": "Thank you! Let me now provide a comprehensive summary of our discussion."
        }
        return transition_messages.get(target_stage, "")
    
    def _create_error_state(self, state_copy: dict, original_stage: str, interaction_count: int, just_signaled_transition: bool) -> dict:
        """Create a safe error state that preserves history."""
        return {
            "messages": state_copy.get("messages", []),
            "current_stage": original_stage,
            "next_stage": state_copy.get("next_stage", original_stage),
            "stage_completion_metrics": {original_stage: {}},
            "interaction_count": 0 if just_signaled_transition else interaction_count,
            "stage_messages": state_copy.get("stage_messages", {})
        }
    
    def _update_stage_messages(self, state_copy: dict, original_stage: str, last_user_message: str) -> dict:
        """Update stage messages safely."""
        stage_messages = deepcopy(state_copy.get("stage_messages", {}))
        stage_messages.setdefault(original_stage, [])
        
        if last_user_message and not last_user_message.startswith("[SYSTEM CONTEXT:"):
            stage_messages[original_stage].append(last_user_message)
        
        return stage_messages
    
    def _create_graph(self):
        """Creates and compiles the LangGraph workflow."""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._call_model)
        workflow.add_node("tools", self.tool_node)
        workflow.add_node("update_stage", lambda state: update_stage_after_tool(state, self.global_config))
        
        # Set the entrypoint
        workflow.add_edge(START, "agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
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
    
    def initialize_conversation_state(self, initial_message: Optional[str] = None) -> AgentState:
        """Initialize a new conversation state."""
        default_message = "Hello! Let's start with your professional advancements and milestones since your last review."
        message = initial_message or default_message
        
        return initialize_state(
            self.global_config,
            initial_message=message
        )
    
    def process_message(self, state: AgentState, config: Optional[Dict] = None) -> Tuple[Optional[AgentState], Optional[str]]:
        """
        Process a message through the agent graph.
        
        Args:
            state: The current conversation state
            config: Optional configuration for the graph invocation
            
        Returns:
            Tuple of (result_state, error_message)
        """
        return safe_invoke_graph(self.app, state, config)
    
    def get_stage_information(self, stage: str) -> Dict[str, Any]:
        """Get information about a specific stage."""
        return {
            "stage": stage,
            "context": get_stage_context(stage, self.global_config),
            "config": self.global_config
        }
    
    def evaluate_completion(self, state: AgentState) -> Dict[str, Any]:
        """Evaluate stage completion for the current state."""
        return evaluate_stage_completion(state, self.global_config)


# ==============================================================================
# 🎯 Refactored Factory Function for Flask App Context
# ==============================================================================

def create_hr_assistant_service() -> HRAssistantService:
    """
    Factory function to create a new HRAssistantService instance.
    This function should be called from the app's initialization logic.
    """
    
    # Use the services already attached to the app context
    services = current_app.extensions['services']
    interview_service = services['interview_service']
    
    return HRAssistantService(interview_service)