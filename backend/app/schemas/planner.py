from pydantic import BaseModel, Field
from typing import List

class PlannerRequest(BaseModel):
    prompt: str = Field(..., description="The natural language request from the user.")

class Task(BaseModel):
    target_agent: str = Field(..., description="The name of the specialized agent that should handle this task (e.g., 'Calendar Agent', 'Gmail Agent').")
    action: str = Field(..., description="A short verb-phrase describing the action to take.")
    description: str = Field(..., description="Detailed instructions for the agent.")

class Plan(BaseModel):
    goal: str = Field(..., description="The overall extracted goal of the user's request.")
    tasks: List[Task] = Field(..., description="A sequential list of tasks to accomplish the goal.")
