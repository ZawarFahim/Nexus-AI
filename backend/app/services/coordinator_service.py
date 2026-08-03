import logging
import json
from typing import List, Dict, Any, Optional
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

from app.core.config import settings
from app.models.user import User
from app.schemas.mcp import ToolExecuteRequest
from app.schemas.coordinator import CoordinatorResponse, ExecutionLog
from app.schemas.planner import Plan, Task
from app.services.planner_service import planner_service
from app.services.mcp_registry import mcp_registry

logger = logging.getLogger(__name__)

class ToolSelectionResponse(BaseModel):
    tool_name: Optional[str] = Field(None, description="The precise name of the tool to execute, or null if no tool is appropriate.")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="The arguments to pass to the tool.")

class CoordinatorService:
    """
    Agent Coordinator.
    Responsible for fetching the Plan, discovering tools, orchestrating sequential execution,
    and synthesizing the final user response using Gemini.
    """
    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None

    async def execute_request(self, prompt: str, user: User) -> CoordinatorResponse:
        if not self.client:
            raise RuntimeError("Gemini API key is not configured.")

        # 1. Generate the Plan
        logger.info(f"Coordinator requesting plan for prompt: '{prompt}'")
        plan: Plan = await planner_service.generate_plan(prompt)
        logger.info(f"Plan generated with goal: '{plan.goal}' and {len(plan.tasks)} tasks.")

        execution_logs: List[ExecutionLog] = []
        execution_context: List[Dict[str, Any]] = []

        # 2. Execute tasks sequentially
        for task in plan.tasks:
            log = await self._execute_single_task(task, execution_context, user)
            execution_logs.append(log)
            
            # Add result to context for subsequent tasks
            execution_context.append({
                "task": task.description,
                "tool_executed": log.tool_executed,
                "success": log.success,
                "result": log.result
            })

        # 3. Synthesize the final response
        final_response = await self._synthesize_response(prompt, plan, execution_context)

        return CoordinatorResponse(
            final_response=final_response,
            execution_logs=execution_logs
        )

    async def _execute_single_task(self, task: Task, context: List[Dict[str, Any]], user: User) -> ExecutionLog:
        """Use Gemini to map a Task to a specific MCP Tool execute request, then execute it."""
        
        available_tools = mcp_registry.get_all_tools()
        tools_schema = [t.model_dump() for t in available_tools]
        
        system_instruction = (
            "You are the Agent Coordinator. Your job is to select the exact MCP tool required to fulfill a task.\n"
            "Analyze the task description and the available tools schema.\n"
            "Return the exact tool_name and the required arguments as JSON.\n"
            "If no tool matches, return null for tool_name."
        )
        
        user_prompt = (
            f"Target Agent: {task.target_agent}\n"
            f"Action: {task.action}\n"
            f"Task Description: {task.description}\n\n"
            f"Available Tools Schema:\n{json.dumps(tools_schema, indent=2)}\n\n"
            f"Previous Execution Context:\n{json.dumps(context, indent=2)}\n\n"
            "Determine the tool_name and arguments."
        )
        
        try:
            # 1. Ask Gemini which tool to run and with what arguments
            selection = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=ToolSelectionResponse,
                    temperature=0.1,
                )
            )
            
            if not selection.parsed:
                return ExecutionLog(task=task.description, success=False, result="Failed to parse LLM tool selection.")
                
            selection_data: ToolSelectionResponse = selection.parsed
            
            if not selection_data.tool_name:
                return ExecutionLog(task=task.description, success=False, result="No suitable tool found by the coordinator.")

            # 2. Execute the chosen tool
            logger.info(f"Coordinator executing tool: {selection_data.tool_name} with args: {selection_data.arguments}")
            execute_req = ToolExecuteRequest(
                tool_name=selection_data.tool_name,
                arguments=selection_data.arguments
            )
            
            tool_res = await mcp_registry.execute_tool(execute_req, current_user=user)
            
            return ExecutionLog(
                task=task.description,
                tool_executed=selection_data.tool_name,
                success=tool_res.success,
                result=tool_res.result if tool_res.success else tool_res.error
            )
            
        except Exception as e:
            logger.error(f"Coordinator task execution failed: {e}")
            return ExecutionLog(task=task.description, success=False, result=f"Exception: {e}")

    async def _synthesize_response(self, original_prompt: str, plan: Plan, context: List[Dict[str, Any]]) -> str:
        """Feed the raw results back to Gemini to create a final natural language response."""
        system_instruction = (
            "You are the Nexus AI Assistant. Your job is to synthesize the results of several background tasks "
            "into a single, clean, human-readable response for the user.\n"
            "Do NOT expose the raw JSON or mention the internal 'tools' or 'agents'. Just answer the user's prompt directly based on the results."
        )
        
        user_prompt = (
            f"User Prompt: {original_prompt}\n"
            f"AI Goal: {plan.goal}\n"
            f"Execution Results:\n{json.dumps(context, indent=2)}\n\n"
            "Generate the final response."
        )
        
        try:
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    temperature=0.4,
                )
            )
            return response.text or "I completed the tasks, but couldn't generate a summary."
        except Exception as e:
            logger.error(f"Failed to synthesize final response: {e}")
            return "I completed the tasks, but encountered an error while synthesizing the final response."

# Singleton instance
coordinator_service = CoordinatorService()
