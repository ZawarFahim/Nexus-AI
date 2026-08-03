from fastapi import APIRouter, Depends, HTTPException, status
from app.api import deps
from app.schemas.planner import PlannerRequest, Plan
from app.services.planner_service import planner_service
from app.models.user import User

router = APIRouter()

@router.post("", response_model=Plan)
async def generate_plan(
    request: PlannerRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Generate a structured JSON execution plan from a natural language request.
    This endpoint requires authentication.
    """
    try:
        plan = await planner_service.generate_plan(request.prompt)
        return plan
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate plan: {e}"
        )
