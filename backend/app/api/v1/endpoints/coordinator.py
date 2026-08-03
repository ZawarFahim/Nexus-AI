from fastapi import APIRouter, Depends, HTTPException, status
from app.api import deps
from app.schemas.coordinator import CoordinatorRequest, CoordinatorResponse
from app.services.coordinator_service import coordinator_service
from app.models.user import User

router = APIRouter()

@router.post("/run", response_model=CoordinatorResponse)
async def run_coordinator(
    request: CoordinatorRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Execute a natural language request by coordinating the AI Planner and MCP tools.
    Requires authentication.
    """
    try:
        response = await coordinator_service.execute_request(request.prompt, current_user)
        return response
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Coordinator failed: {e}"
        )
