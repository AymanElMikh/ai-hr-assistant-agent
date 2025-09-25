"""Improved utils for LangGraph HR Assistant

This module centralizes configuration, reduces hardcoded values,
and provides clearer transition logic with less overlap.

Key improvements:
- Moved hardcoded strings to configuration
- Simplified transition conditions to reduce overlap
- Made transition thresholds configurable
- Separated concerns more clearly
"""
from __future__ import annotations

import os
import re
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from langchain_core.messages import AIMessage, BaseMessage
from langgraph.graph.message import add_messages

logger = logging.getLogger(__name__)
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# ---------------- CONFIGURABLE CONSTANTS ----------------

@dataclass
class TransitionConfig:
    """Configuration for stage transitions to reduce hardcoded values."""
    # Completion thresholds
    min_completeness_score: float = 0.7
    emergency_completeness_score: float = 0.5
    max_interactions_before_force: int = 6
    min_interactions_for_emergency: int = 3
    
    # User intent signals
    continue_signals: List[str] = field(default_factory=lambda: [
        "next", "continue", "move on", "done", "finished", 
        "that's it", "let's proceed", "ready"
    ])
    
    # Transition messages
    transition_messages: Dict[str, str] = field(default_factory=lambda: {
        "challenges": "Great! Now let's discuss any challenges or obstacles you've faced.",
        "achievements": "Excellent! Now let's talk about your key achievements and accomplishments.",
        "training_needs": "Perfect! Now let's identify areas for your professional development.",
        "action_plan": "Great! Finally, let's create an action plan for your continued growth.",
        "summary": "Thank you! Let me now provide a comprehensive summary of our discussion."
    })

@dataclass
class CompletionWeights:
    """Configurable weights for completion scoring."""
    keyword_coverage: float = 0.25
    depth_score: float = 0.25
    interactions: float = 0.20
    words: float = 0.15
    examples: float = 0.15

# ---------------- CORE CONFIGURATION ----------------

StageName = str

@dataclass
class StageConfig:
    pretty_name: str
    context_text: str
    min_interactions: int = 1
    min_word_count: int = 50
    required_keywords: List[str] = field(default_factory=list)
    depth_indicators: List[str] = field(default_factory=list)
    follow_up_template: str = "To ensure we capture everything important, could you elaborate on: {missing}?"
    # Stage-specific thresholds
    completion_threshold: float = 0.7
    force_transition_interactions: int = 6

@dataclass
class GlobalConfig:
    stage_order: List[StageName]
    stages: Dict[StageName, StageConfig]
    transition_config: TransitionConfig = field(default_factory=TransitionConfig)
    completion_weights: CompletionWeights = field(default_factory=CompletionWeights)
    required_env_vars: List[str] = field(default_factory=lambda: ["OPENAI_API_KEY"])
    initial_stage: StageName = "advancements"

# ---------------------------------------------------------------------------
# AgentState type definition
# ---------------------------------------------------------------------------

from typing import TypedDict, Annotated

class AgentState(TypedDict):
    messages: Annotated[List[BaseMessage], add_messages]
    current_stage: str
    captured_data: Dict[str, Any]
    next_stage: str
    stage_completion_metrics: Dict[str, Any]
    interaction_count: int
    stage_messages: Dict[str, List[str]]

# ---------------------------------------------------------------------------
# Configuration builder with improved defaults
# ---------------------------------------------------------------------------

def build_default_config() -> GlobalConfig:
    """Build the default configuration with improved stage definitions."""
    stages = {
        "advancements": StageConfig(
            pretty_name="📈 Professional Advancements & Milestones",
            context_text="Focus on documenting professional advancements and milestones since the last review. Please share specific examples of your growth and development.",
            min_interactions=2,
            min_word_count=100,
            required_keywords=["skill", "project", "responsibility", "improvement", "achievement", "learn", "develop", "growth"],
            depth_indicators=["specific", "example", "result", "impact", "implemented", "created", "led", "managed"],
            completion_threshold=0.7,
            force_transition_interactions=5,
        ),
        "challenges": StageConfig(
            pretty_name="⚠️ Challenges & Obstacles",
            context_text="Now let's discuss the challenges and obstacles you've faced. Understanding these helps identify areas for support and improvement.",
            min_interactions=2,
            min_word_count=80,
            required_keywords=["challenge", "difficult", "obstacle", "problem", "barrier", "issue", "struggle"],
            depth_indicators=["approach", "solution", "overcome", "learned", "adapted", "resolved", "handled"],
            completion_threshold=0.6,  # Lower threshold as this can be sensitive
            force_transition_interactions=4,
        ),
        "achievements": StageConfig(
            pretty_name="🏆 Key Achievements & Accomplishments",
            context_text="Let's talk about your key achievements and accomplishments. Focus on measurable results and positive impacts.",
            min_interactions=2,
            min_word_count=120,
            required_keywords=["accomplished", "delivered", "exceeded", "successful", "completed", "achieved", "won"],
            depth_indicators=["metric", "percentage", "number", "result", "impact", "recognition", "outcome", "improved"],
            completion_threshold=0.75,
            force_transition_interactions=6,
        ),
        "training_needs": StageConfig(
            pretty_name="📚 Training & Development Needs",
            context_text="What training or development areas would be most beneficial for your growth? Consider both technical and soft skills.",
            min_interactions=1,
            min_word_count=60,
            required_keywords=["skill", "training", "development", "learn", "improve", "certification", "course"],
            depth_indicators=["specific", "goal", "timeline", "program", "mentor", "practice"],
            completion_threshold=0.6,
            force_transition_interactions=4,
        ),
        "action_plan": StageConfig(
            pretty_name="📋 Action Plan & Goals",
            context_text="Let's create a concrete action plan for your professional development. Focus on specific, measurable goals with timelines.",
            min_interactions=2,
            min_word_count=100,
            required_keywords=["goal", "plan", "objective", "timeline", "action", "target", "milestone"],
            depth_indicators=["specific", "measurable", "deadline", "resource", "steps", "review"],
            completion_threshold=0.75,
            force_transition_interactions=5,
        ),
        "summary": StageConfig(
            pretty_name="📊 Performance Review Summary",
            context_text="Generating comprehensive summary of our discussion.",
            min_interactions=0,
            min_word_count=0,
            required_keywords=[],
            depth_indicators=[],
            completion_threshold=0.0,
            force_transition_interactions=1,
        ),
    }

    return GlobalConfig(
        stage_order=["advancements", "challenges", "achievements", "training_needs", "action_plan", "summary"],
        stages=stages,
    )

# ---------------------------------------------------------------------------
# Improved utility functions
# ---------------------------------------------------------------------------

def get_stage_responses(state: AgentState, stage: str) -> List[str]:
    """Return the list of user responses stored for a given stage."""
    return state.get("stage_messages", {}).get(stage, [])

def calculate_keyword_coverage(text: str, keywords: List[str]) -> float:
    """Calculate fraction of keywords present in text."""
    if not keywords:
        return 1.0
    lowered = text.lower()
    found = sum(1 for k in keywords if k.lower() in lowered)
    return found / len(keywords)

def calculate_depth_score(text: str, depth_indicators: List[str]) -> float:
    """Calculate depth score based on presence of depth indicators."""
    if not depth_indicators:
        return 1.0
    lowered = text.lower()
    found = sum(1 for d in depth_indicators if d.lower() in lowered)
    return min(found / len(depth_indicators), 1.0)

def has_specific_examples(text: str) -> bool:
    """Check if text contains specific examples using improved heuristics."""
    if not text:
        return False
    
    lowered = text.lower()
    
    # Check for numerical data
    has_numbers = bool(re.search(r"\d+[\.,]?\d*\s*%?", text))
    
    # Check for example indicators
    example_indicators = [
        "for example", "such as", "specifically", "in particular", "including",
        "like", "instance", "case", "project", "when", "during", "resulted in"
    ]
    has_example_words = any(ind in lowered for ind in example_indicators)
    
    # Check for detailed descriptions
    is_detailed = len(text.split()) > 80
    
    return has_numbers or has_example_words or is_detailed

# ---------------------------------------------------------------------------
# Improved completion evaluation
# ---------------------------------------------------------------------------

def evaluate_stage_completion(state: AgentState, cfg: Optional[GlobalConfig] = None) -> Dict[str, Any]:
    """Evaluate stage completion with configurable weights and thresholds."""
    if cfg is None:
        cfg = build_default_config()

    current_stage = state.get("current_stage", cfg.initial_stage)
    sc = cfg.stages.get(current_stage, StageConfig(pretty_name=current_stage, context_text=""))

    stage_responses = get_stage_responses(state, current_stage)
    combined_text = " ".join(stage_responses)
    interaction_count = state.get("interaction_count", 0)

    # Calculate component scores
    word_count = len(combined_text.split())
    keyword_coverage = calculate_keyword_coverage(combined_text, sc.required_keywords)
    depth_score = calculate_depth_score(combined_text, sc.depth_indicators)
    specific_examples = has_specific_examples(combined_text)

    # Basic requirement checks
    min_interactions_met = interaction_count >= sc.min_interactions
    min_words_met = word_count >= sc.min_word_count

    # Weighted completeness score using configuration
    weights = cfg.completion_weights
    components = [
        keyword_coverage * weights.keyword_coverage,
        depth_score * weights.depth_score,
        (1.0 if min_interactions_met else 0.5) * weights.interactions,
        (1.0 if min_words_met else 0.3) * weights.words,
        (1.0 if specific_examples else 0.4) * weights.examples,
    ]
    
    completeness_score = sum(components)

    # Determine readiness using stage-specific thresholds
    ready_for_next = _determine_readiness(
        completeness_score, interaction_count, sc, cfg.transition_config
    )

    return {
        "interaction_count": interaction_count,
        "word_count": word_count,
        "keyword_coverage": keyword_coverage,
        "depth_score": depth_score,
        "min_interactions_met": min_interactions_met,
        "min_words_met": min_words_met,
        "has_specific_examples": specific_examples,
        "completeness_score": completeness_score,
        "ready_for_next": ready_for_next,
    }

def _determine_readiness(completeness_score: float, interaction_count: int, 
                        stage_config: StageConfig, transition_config: TransitionConfig) -> bool:
    """Determine if stage is ready for transition using non-overlapping conditions."""
    
    # Primary readiness condition
    if completeness_score >= stage_config.completion_threshold and interaction_count >= stage_config.min_interactions:
        return True
    
    # Emergency transition (force forward if stuck)
    if interaction_count >= stage_config.force_transition_interactions:
        return completeness_score >= transition_config.emergency_completeness_score
    
    # Extended interaction with decent progress
    if interaction_count >= transition_config.min_interactions_for_emergency * 2:
        return completeness_score >= 0.6
    
    return False

# ---------------------------------------------------------------------------
# Intent detection and transition logic
# ---------------------------------------------------------------------------

def detect_conversation_intent(user_message: str, current_stage: str, cfg: Optional[GlobalConfig] = None) -> str:
    """Detect user intent for stage transitions with improved logic."""
    if cfg is None:
        cfg = build_default_config()

    text = (user_message or "").lower().strip()
    
    # Check for explicit continuation signals
    if any(sig in text for sig in cfg.transition_config.continue_signals):
        return "continue"
    
    # Check for stage-specific keywords
    stage_scores = {}
    for stage_name, sc in cfg.stages.items():
        if stage_name == current_stage:
            continue
        
        all_keywords = sc.required_keywords + sc.depth_indicators
        if all_keywords:
            matches = sum(1 for kw in all_keywords if kw.lower() in text)
            stage_scores[stage_name] = matches / len(all_keywords)
    
    # Return stage with highest keyword match if above threshold
    if stage_scores:
        best_stage = max(stage_scores.items(), key=lambda x: x[1])
        if best_stage[1] >= 0.3:  # Configurable threshold
            return best_stage[0]
    
    return current_stage

def should_transition_stage(state: AgentState, user_message: Optional[str] = None, 
                          cfg: Optional[GlobalConfig] = None) -> Tuple[bool, str]:
    """Determine if stage should transition with simplified, non-overlapping logic."""
    if cfg is None:
        cfg = build_default_config()

    current_stage = state.get("current_stage", cfg.initial_stage)
    completion_metrics = evaluate_stage_completion(state, cfg)
    
    # Get next stage in order
    try:
        idx = cfg.stage_order.index(current_stage)
        next_stage = cfg.stage_order[idx + 1] if idx + 1 < len(cfg.stage_order) else None
    except ValueError:
        return False, current_stage
    
    if not next_stage:
        return False, current_stage
    
    # Check user intent first (highest priority)
    if user_message:
        detected = detect_conversation_intent(user_message, current_stage, cfg)
        if detected == "continue" and completion_metrics.get("ready_for_next", False):
            return True, next_stage
        elif detected == next_stage:
            # Allow transition to immediate next stage if minimum requirements met
            if (completion_metrics.get("completeness_score", 0) >= 0.5 
                and completion_metrics.get("interaction_count", 0) >= 1):
                return True, next_stage
    
    # Automatic transition when truly ready
    if completion_metrics.get("ready_for_next", False):
        return True, next_stage
    
    return False, current_stage

# ---------------------------------------------------------------------------
# Context and follow-up generation
# ---------------------------------------------------------------------------

def get_stage_context(stage: str, cfg: Optional[GlobalConfig] = None) -> str:
    """Get stage context from configuration."""
    if cfg is None:
        cfg = build_default_config()
    sc = cfg.stages.get(stage)
    return sc.context_text if sc else ""

def generate_follow_up_prompts(stage: str, metrics: Dict[str, Any], 
                             cfg: Optional[GlobalConfig] = None) -> str:
    """Generate follow-up prompts based on missing elements."""
    if cfg is None:
        cfg = build_default_config()
    
    sc = cfg.stages.get(stage)
    if not sc:
        return ""

    missing = []
    
    # Check what's missing based on metrics
    if metrics.get("word_count", 0) < sc.min_word_count:
        missing.append("more detailed explanation")
    
    if metrics.get("keyword_coverage", 0) < 0.5 and sc.required_keywords:
        missing.append(f"discussion of: {', '.join(sc.required_keywords[:3])}")
    
    if not metrics.get("has_specific_examples", False):
        missing.append("specific examples or metrics")
    
    if not missing:
        return ""
    
    return sc.follow_up_template.format(missing=", ".join(missing))

# ---------------------------------------------------------------------------
# Next stage determination
# ---------------------------------------------------------------------------

def determine_next_stage(response: AIMessage, current_stage: str, completion_metrics: Dict[str, Any], 
                        user_message: Optional[str] = None, cfg: Optional[GlobalConfig] = None) -> str:
    """Determine next stage with simplified logic to avoid overlap."""
    if cfg is None:
        cfg = build_default_config()

    # Get the next logical stage
    try:
        idx = cfg.stage_order.index(current_stage)
        next_stage = cfg.stage_order[idx + 1] if idx + 1 < len(cfg.stage_order) else current_stage
    except ValueError:
        return current_stage

    # Tool-driven transitions (highest priority for structured flow)
    tool_calls = getattr(response, "tool_calls", None)
    if tool_calls and completion_metrics.get("ready_for_next", False):
        tool_name = _extract_tool_name(tool_calls)
        if tool_name:
            tool_stage_map = {
                "document_advancement": "challenges",
                "document_challenge": "achievements", 
                "document_achievement": "training_needs",
                "document_training_need": "action_plan",
                "document_action_plan": "summary",
            }
            mapped_stage = tool_stage_map.get(tool_name)
            if mapped_stage and mapped_stage == next_stage:
                return mapped_stage

    # User intent (only if ready or minimum criteria met)
    if user_message:
        detected = detect_conversation_intent(user_message, current_stage, cfg)
        if detected == next_stage and completion_metrics.get("completeness_score", 0) >= 0.5:
            return next_stage

    # Force transition if stuck too long with minimal progress
    sc = cfg.stages.get(current_stage, StageConfig(pretty_name=current_stage, context_text=""))
    if completion_metrics.get("interaction_count", 0) >= sc.force_transition_interactions:
        if completion_metrics.get("completeness_score", 0) >= cfg.transition_config.emergency_completeness_score:
            logger.info("Forcing stage transition due to extended interaction")
            return next_stage

    return current_stage

def _extract_tool_name(tool_calls) -> Optional[str]:
    """Extract tool name from tool calls safely."""
    try:
        first = tool_calls[0] if isinstance(tool_calls, (list, tuple)) and tool_calls else tool_calls
        return first.get("name") if isinstance(first, dict) else getattr(first, "name", None)
    except Exception:
        return None

# ---------------------------------------------------------------------------
# Stage update functionality
# ---------------------------------------------------------------------------

def update_stage_after_tool(state: AgentState, cfg: Optional[GlobalConfig] = None) -> AgentState:
    """Apply staged transition and reset counters."""
    if cfg is None:
        cfg = build_default_config()

    next_stage = state.get("next_stage", state.get("current_stage"))
    current_stage = state.get("current_stage")

    if next_stage and next_stage != current_stage:
        logger.info("Stage transition: %s -> %s", current_stage, next_stage)
        return {
            "current_stage": next_stage,
            "interaction_count": 0,
            "next_stage": next_stage,
        }

    return {"current_stage": current_stage}

# ---------------------------------------------------------------------------
# Initialization and helper functions
# ---------------------------------------------------------------------------

def initialize_state(cfg: Optional[GlobalConfig] = None, initial_message: Optional[str] = None) -> AgentState:
    """Initialize agent state with configuration."""
    if cfg is None:
        cfg = build_default_config()
    
    if initial_message is None:
        initial_stage_config = cfg.stages.get(cfg.initial_stage)
        initial_message = initial_stage_config.context_text if initial_stage_config else "Hello! Let's begin your performance review."

    return {
        "messages": [AIMessage(content=initial_message)],
        "current_stage": cfg.initial_stage,
        "captured_data": {},
        "next_stage": cfg.initial_stage,
        "stage_completion_metrics": {},
        "interaction_count": 0,
        "stage_messages": {},
    }

def print_stage_info(stage: str, cfg: Optional[GlobalConfig] = None) -> None:
    """Print stage information using configuration."""
    if cfg is None:
        cfg = build_default_config()
    
    sc = cfg.stages.get(stage)
    info = sc.pretty_name if sc else f"Current Stage: {stage}"
    separator = "=" * max(50, len(info) + 10)
    logger.info("\n%s\n%s\n%s", separator, info, separator)

def validate_environment(cfg: Optional[GlobalConfig] = None) -> None:
    """Validate required environment variables."""
    if cfg is None:
        cfg = build_default_config()
    
    missing = [v for v in cfg.required_env_vars if not os.getenv(v)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def safe_invoke_graph(app, state: AgentState, config: Optional[Dict[str, Any]] = None) -> Tuple[Optional[AgentState], Optional[str]]:
    """Safely invoke the graph with error handling."""
    try:
        if config is None:
            config = {"configurable": {"thread_id": "default"}}
        result = app.invoke(state, config)
        return result, None
    except Exception as e:
        logger.exception("Error during graph execution")
        return None, str(e)

# ---------------------------------------------------------------------------
# Exported interface
# ---------------------------------------------------------------------------

__all__ = [
    "StageConfig",
    "GlobalConfig", 
    "TransitionConfig",
    "CompletionWeights",
    "build_default_config",
    "get_stage_responses",
    "evaluate_stage_completion",
    "get_stage_context",
    "generate_follow_up_prompts", 
    "determine_next_stage",
    "should_transition_stage",
    "update_stage_after_tool",
    "initialize_state",
    "print_stage_info",
    "validate_environment",
    "safe_invoke_graph",
    "AgentState",
]