# rh_interviewer/config.py

from typing import Dict, List
from dataclasses import dataclass, field
from .models import InterviewStage

# ==============================================================================
# 📦 Configuration Classes
# ==============================================================================

@dataclass
class TransitionConfig:
    """Configuration for stage transitions"""
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
    """Configurable weights for completion scoring"""
    keyword_coverage: float = 0.25
    depth_score: float = 0.25
    interactions: float = 0.20
    words: float = 0.15
    examples: float = 0.15

@dataclass
class StageConfig:
    """Configuration for individual interview stages"""
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
class InterviewConfig:
    """Main configuration for the interview system"""
    stage_order: List[InterviewStage] = field(default_factory=lambda: [
        InterviewStage.ADVANCEMENTS, 
        InterviewStage.CHALLENGES, 
        InterviewStage.ACHIEVEMENTS, 
        InterviewStage.TRAINING_NEEDS, 
        InterviewStage.ACTION_PLAN, 
        InterviewStage.SUMMARY
    ])
    stages: Dict[InterviewStage, StageConfig] = field(default_factory=dict)
    transition_config: TransitionConfig = field(default_factory=TransitionConfig)
    completion_weights: CompletionWeights = field(default_factory=CompletionWeights)
    initial_stage: InterviewStage = InterviewStage.ADVANCEMENTS
    required_env_vars: List[str] = field(default_factory=lambda: [
        "OPENAI_API_KEY", "LANGCHAIN_API_KEY"
    ])

def build_default_config() -> InterviewConfig:
    """Build the default interview configuration"""
    stages = {
        InterviewStage.ADVANCEMENTS: StageConfig(
            pretty_name="📈 Professional Advancements & Milestones",
            context_text="Focus on documenting professional advancements and milestones since the last review. Please share specific examples of your growth and development.",
            min_interactions=2,
            min_word_count=100,
            required_keywords=["skill", "project", "responsibility", "improvement", "achievement", "learn", "develop", "growth"],
            depth_indicators=["specific", "example", "result", "impact", "implemented", "created", "led", "managed"],
            completion_threshold=0.7,
            force_transition_interactions=5,
        ),
        InterviewStage.CHALLENGES: StageConfig(
            pretty_name="⚠️ Challenges & Obstacles",
            context_text="Now let's discuss the challenges and obstacles you've faced. Understanding these helps identify areas for support and improvement.",
            min_interactions=2,
            min_word_count=80,
            required_keywords=["challenge", "difficult", "obstacle", "problem", "barrier", "issue", "struggle"],
            depth_indicators=["approach", "solution", "overcome", "learned", "adapted", "resolved", "handled"],
            completion_threshold=0.6,
            force_transition_interactions=4,
        ),
        InterviewStage.ACHIEVEMENTS: StageConfig(
            pretty_name="🏆 Key Achievements & Accomplishments",
            context_text="Let's talk about your key achievements and accomplishments. Focus on measurable results and positive impacts.",
            min_interactions=2,
            min_word_count=120,
            required_keywords=["accomplished", "delivered", "exceeded", "successful", "completed", "achieved", "won"],
            depth_indicators=["metric", "percentage", "number", "result", "impact", "recognition", "outcome", "improved"],
            completion_threshold=0.75,
            force_transition_interactions=6,
        ),
        InterviewStage.TRAINING_NEEDS: StageConfig(
            pretty_name="📚 Training & Development Needs",
            context_text="What training or development areas would be most beneficial for your growth? Consider both technical and soft skills.",
            min_interactions=1,
            min_word_count=60,
            required_keywords=["skill", "training", "development", "learn", "improve", "certification", "course"],
            depth_indicators=["specific", "goal", "timeline", "program", "mentor", "practice"],
            completion_threshold=0.6,
            force_transition_interactions=4,
        ),
        InterviewStage.ACTION_PLAN: StageConfig(
            pretty_name="📋 Action Plan & Goals",
            context_text="Let's create a concrete action plan for your professional development. Focus on specific, measurable goals with timelines.",
            min_interactions=2,
            min_word_count=100,
            required_keywords=["goal", "plan", "objective", "timeline", "action", "target", "milestone"],
            depth_indicators=["specific", "measurable", "deadline", "resource", "steps", "review"],
            completion_threshold=0.75,
            force_transition_interactions=5,
        ),
        InterviewStage.SUMMARY: StageConfig(
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

    return InterviewConfig(stages=stages)