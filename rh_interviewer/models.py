# rh_interviewer/models.py

import uuid
from datetime import datetime
from typing import Dict, Any, Optional, Annotated, List, TypedDict
from dataclasses import dataclass, asdict, field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

# ==============================================================================
# 📦 Core Data Models (Migrated from utils.py)
# ==============================================================================

@dataclass
class APIResponse:
    """Standard API response structure."""
    success: bool
    message: str
    data: Optional[Dict[Any, Any]] = None
    error: Optional[str] = None
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}

@dataclass
class TransitionConfig:
    """Configuration for stage transitions to reduce hardcoded values."""
    min_completeness_score: float = 0.7
    emergency_completeness_score: float = 0.5
    max_interactions_before_force: int = 6
    min_interactions_for_emergency: int = 3
    
    continue_signals: List[str] = field(default_factory=lambda: [
        "next", "continue", "move on", "done", "finished", 
        "that's it", "let's proceed", "ready"
    ])
    
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

@dataclass
class StageConfig:
    """Configuration for individual stages."""
    pretty_name: str
    context_text: str
    min_interactions: int = 1
    min_word_count: int = 50
    required_keywords: List[str] = field(default_factory=list)
    depth_indicators: List[str] = field(default_factory=list)
    follow_up_template: str = "To ensure we capture everything important, could you elaborate on: {missing}?"
    completion_threshold: float = 0.7
    force_transition_interactions: int = 6

@dataclass
class GlobalConfig:
    """Global configuration for the HR assistant."""
    stage_order: List[str] = field(default_factory=lambda: [
        "advancements", "challenges", "achievements", "training_needs", "action_plan", "summary"
    ])
    stages: Dict[str, StageConfig] = field(default_factory=dict)
    transition_config: TransitionConfig = field(default_factory=TransitionConfig)
    completion_weights: CompletionWeights = field(default_factory=CompletionWeights)
    initial_stage: str = "advancements"
    required_env_vars: List[str] = field(default_factory=lambda: [
        "OPENAI_API_KEY", "LANGCHAIN_API_KEY"
    ])

# ==============================================================================
# 📦 Type Definitions
# ==============================================================================

class AgentState(TypedDict):
    """Agent state type definition."""
    messages: Annotated[List[BaseMessage], add_messages]
    current_stage: str
    captured_data: Dict[str, Any]
    next_stage: str
    stage_completion_metrics: Dict[str, Any]
    interaction_count: int
    stage_messages: Dict[str, List[str]]

StageName = str

# ==============================================================================
# 📦 API Response Models
# ==============================================================================

@dataclass
class SessionInfo:
    """Session information structure."""
    session_id: str
    current_stage: str
    next_stage: str
    interaction_count: int
    completed_stages: list
    progress_percentage: float
    stage_completion_metrics: Dict[str, Any]

@dataclass
class MessageInfo:
    """Message information structure."""
    content: str
    role: str
    timestamp: str
    stage: str

# ==============================================================================
# 🧠 Session Management
# ==============================================================================

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
            completion_threshold=0.6,
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

def initialize_state(cfg: Optional[GlobalConfig] = None, initial_message: Optional[str] = None) -> AgentState:
    """Initialize agent state with configuration."""
    if cfg is None:
        cfg = build_default_config()
    
    if initial_message is None:
        initial_stage_config = cfg.stages.get(cfg.initial_stage)
        initial_message = initial_stage_config.context_text if initial_stage_config else "Hello! Let's begin your performance review."

    return {
        "messages": [],  # Will be populated with initial message by the caller
        "current_stage": cfg.initial_stage,
        "captured_data": {},
        "next_stage": cfg.initial_stage,
        "stage_completion_metrics": {},
        "interaction_count": 0,
        "stage_messages": {},
    }

class SessionManager:
    """
    Manages user sessions and their states.
    NOTE: The current implementation uses in-memory storage, which is suitable
    for development but NOT for production. For a robust solution, consider
    using Redis, a database, or another persistent store.
    """
    def __init__(self):
        self.global_config = build_default_config()
        self.sessions: Dict[str, Dict] = {}
    
    def create_session(self) -> str:
        session_id = str(uuid.uuid4())
        initial_state = initialize_state(self.global_config)
        self.sessions[session_id] = {
            'state': initial_state,
            'created_at': datetime.now(),
            'last_activity': datetime.now(),
            'config': {"configurable": {"thread_id": f"hr_session_{session_id}"}}
        }
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict]:
        return self.sessions.get(session_id)
    
    def update_session(self, session_id: str, state: Dict) -> bool:
        if session_id in self.sessions:
            self.sessions[session_id]['state'] = state
            self.sessions[session_id]['last_activity'] = datetime.now()
            return True
        return False
    
    def delete_session(self, session_id: str) -> bool:
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def get_session_info(self, session_id: str) -> Optional[SessionInfo]:
        session_data = self.get_session(session_id)
        if not session_data:
            return None
        
        state = session_data['state']
        current_stage = state.get('current_stage', 'advancements')
        next_stage = state.get('next_stage', current_stage)
        
        stage_order = self.global_config.stage_order
        try:
            current_idx = stage_order.index(current_stage)
            progress = ((current_idx + 1) / len(stage_order)) * 100
            completed_stages = stage_order[:current_idx]
        except ValueError:
            progress = 0
            completed_stages = []
        
        return SessionInfo(
            session_id=session_id,
            current_stage=current_stage,
            next_stage=next_stage,
            interaction_count=state.get('interaction_count', 0),
            completed_stages=completed_stages,
            progress_percentage=round(progress, 2),
            stage_completion_metrics=state.get('stage_completion_metrics', {})
        )

# Initialize session manager as a global singleton within the models module
session_manager = SessionManager()