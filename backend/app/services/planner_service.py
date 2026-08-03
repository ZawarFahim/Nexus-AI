import logging
from google import genai
from google.genai import types
from app.core.config import settings
from app.schemas.planner import Plan

logger = logging.getLogger(__name__)

class PlannerService:
    """
    AI Planner Service responsible for interpreting natural language and generating 
    structured JSON execution plans. It does not execute the plan.
    """
    def __init__(self):
        if settings.GEMINI_API_KEY:
            self.client = genai.Client(api_key=settings.GEMINI_API_KEY)
        else:
            self.client = None
            logger.warning("GEMINI_API_KEY is missing. PlannerService will fail on execution.")

    async def generate_plan(self, prompt: str) -> Plan:
        if not self.client:
            raise RuntimeError("Gemini API key is not configured.")

        # System instructions to guide the planner
        system_instruction = (
            "You are the central AI Planner for Nexus OS. Your job is to analyze user requests, "
            "determine the overarching goal, and break it down into a sequential list of concrete tasks. "
            "You must assign each task to exactly ONE specialized agent. "
            "Do NOT execute the tasks. Only generate the plan."
        )

        try:
            # We use the official google-genai structured output feature.
            # Passing the Pydantic model directly to response_schema forces the model to return valid JSON matching it.
            response = self.client.models.generate_content(
                model='gemini-2.5-flash',
                contents=prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    response_schema=Plan,
                    temperature=0.2, # Low temperature for more deterministic planning
                )
            )
            
            # The response.parsed field automatically contains our populated Pydantic model
            if response.parsed:
                return response.parsed
            
            # Fallback if parsed is missing but text exists (unlikely with structured output)
            return Plan.model_validate_json(response.text)
            
        except Exception as e:
            logger.error(f"Failed to generate plan: {e}")
            raise

# Singleton instance
planner_service = PlannerService()
