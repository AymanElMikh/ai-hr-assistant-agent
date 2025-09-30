# rh_interviewer/tools/document_tools.py

import json
from langchain_core.tools import tool
from typing import List, Optional
from pydantic import BaseModel, Field  # Import Pydantic BaseModel and Field
from rh_interviewer.services.interview_service import InterviewService

class DocumentTools:
    def __init__(self, interview_service: InterviewService):
        self.interview_service = interview_service
        self.tools = self._create_tools()

    def _create_tools(self):
        """Creates and returns a list of LangChain tools."""
        return [
            self.document_advancement,
            self.document_challenge,
            self.document_achievement,
            self.document_training_need,
            self.document_action_plan
        ]

    # --- Pydantic BaseModel Refactorings ---
    class DocumentAdvancementArgs(BaseModel):
        """Arguments for documenting a professional advancement."""
        interview_id: int = Field(..., description="The unique ID of the interview.")
        description: str = Field(..., description="A detailed description of the advancement.")

    @tool("document_advancement", args_schema=DocumentAdvancementArgs, description="Documents a significant professional advancement or milestone. Call this tool when the employee describes their progress since the last review.")
    def document_advancement(self, interview_id: int, description: str) -> str:
        """
        Documents an advancement by updating the 'advancements' key of an interview's stage summary.
        """
        result = self.interview_service.update_stage_summary_by_interview_and_name(
            interview_id=interview_id,
            stage_name="advancements",
            summary_text=description,
        )
        if result:
            return json.dumps({"status": "success", "message": "Advancement successfully documented."})
        return json.dumps({"status": "error", "message": "Failed to document advancement."})

    class DocumentChallengeArgs(BaseModel):
        """Arguments for documenting a challenge."""
        interview_id: int = Field(..., description="The unique ID of the interview.")
        description: str = Field(..., description="A detailed description of the challenge.")

    @tool("document_challenge", args_schema=DocumentChallengeArgs, description="Documents a challenge or obstacle the employee has faced.")
    def document_challenge(self, interview_id: int, description: str) -> str:
        """
        Documents a challenge by updating the 'challenges' stage summary.
        """
        result = self.interview_service.update_stage_summary_by_interview_and_name(
            interview_id=interview_id,
            stage_name="challenges",
            summary_text=description,
        )
        if result:
            return json.dumps({"status": "success", "message": "Challenge successfully documented."})
        return json.dumps({"status": "error", "message": "Failed to document challenge."})

    class DocumentAchievementArgs(BaseModel):
        """Arguments for documenting an achievement."""
        interview_id: int = Field(..., description="The unique ID of the interview.")
        description: str = Field(..., description="A detailed description of the achievement.")

    @tool("document_achievement", args_schema=DocumentAchievementArgs, description="Documents a key achievement or success.")
    def document_achievement(self, interview_id: int, description: str) -> str:
        """
        Documents an achievement by updating the 'achievements' stage summary.
        """
        result = self.interview_service.update_stage_summary_by_interview_and_name(
            interview_id=interview_id,
            stage_name="achievements",
            summary_text=description,
        )
        if result:
            return json.dumps({"status": "success", "message": "Achievement successfully documented."})
        return json.dumps({"status": "error", "message": "Failed to document achievement."})

    class DocumentTrainingNeedArgs(BaseModel):
        """Arguments for documenting a training need."""
        interview_id: int = Field(..., description="The unique ID of the interview.")
        training_type: str = Field(..., description="The type of training needed.")
        reason: str = Field(..., description="The reason for the training need.")

    @tool("document_training_need", args_schema=DocumentTrainingNeedArgs, description="Documents a specific training or professional development need.")
    def document_training_need(self, interview_id: int, training_type: str, reason: str) -> str:
        """
        Documents a training need by updating the 'training_needs' stage summary.
        """
        summary = f"Training Type: {training_type}, Reason: {reason}"
        result = self.interview_service.update_stage_summary_by_interview_and_name(
            interview_id=interview_id,
            stage_name="training_needs",
            summary_text=summary,
        )
        if result:
            return json.dumps({"status": "success", "message": "Training need documented."})
        return json.dumps({"status": "error", "message": "Failed to document training need."})

    class DocumentActionPlanArgs(BaseModel):
        """Arguments for documenting an action plan."""
        interview_id: int = Field(..., description="The unique ID of the interview.")
        goal: str = Field(..., description="The goal of the action plan.")
        deadline: str = Field(..., description="The deadline for the goal.")
        next_steps: str = Field(..., description="The next steps to achieve the goal.")

    @tool("document_action_plan", args_schema=DocumentActionPlanArgs, description="Documents a concrete, time-bound action plan for the employee.")
    def document_action_plan(self, interview_id: int, goal: str, deadline: str, next_steps: str) -> str:
        """
        Documents an action plan by updating the 'action_plan' stage summary.
        """
        summary = f"Goal: {goal}, Deadline: {deadline}, Next Steps: {next_steps}"
        result = self.interview_service.update_stage_summary_by_interview_and_name(
            interview_id=interview_id,
            stage_name="action_plan",
            summary_text=summary,
        )
        if result:
            return json.dumps({"status": "success", "message": "Action plan documented."})
        return json.dumps({"status": "error", "message": "Failed to document action plan."})