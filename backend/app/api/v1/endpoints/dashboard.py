from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import List, Any
import logging

from app.api import deps
from app.models.user import User
from app.models.workflow import Workflow
from app.models.task import Task
from app.models.file import FileMetadata
from app.db.session import AsyncSessionLocal
from app.services.mcp.gmail_tool import GmailMCPTool
from app.services.mcp.github_tool import GitHubMCPTool

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/workflows")
async def get_dashboard_workflows(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """Fetch latest workflows for the dashboard."""
    stmt = select(Workflow).where(Workflow.user_id == current_user.id).order_by(Workflow.started_at.desc()).limit(5)
    result = await db.execute(stmt)
    workflows = result.scalars().all()
    
    return [{"id": str(w.id), "name": w.workflow_name, "status": w.status, "time": str(w.started_at)} for w in workflows]

@router.get("/tasks")
async def get_dashboard_tasks(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """Fetch latest pending tasks for the dashboard."""
    stmt = select(Task).where(Task.user_id == current_user.id, Task.status != "Completed").order_by(Task.due_date.asc()).limit(5)
    result = await db.execute(stmt)
    tasks = result.scalars().all()
    
    return [{"id": str(t.id), "title": t.title, "priority": t.priority, "status": t.status} for t in tasks]

@router.get("/files")
async def get_dashboard_files(
    current_user: User = Depends(deps.get_current_user),
    db: AsyncSession = Depends(deps.get_db)
):
    """Fetch recently uploaded files for the dashboard."""
    stmt = select(FileMetadata).where(FileMetadata.user_id == current_user.id).order_by(FileMetadata.created_at.desc()).limit(5)
    result = await db.execute(stmt)
    files = result.scalars().all()
    
    return [{"id": str(f.id), "filename": f.filename, "type": f.file_type, "size": f.size_bytes, "created_at": str(f.created_at)} for f in files]

@router.get("/emails")
async def get_dashboard_emails(current_user: User = Depends(deps.get_current_user)):
    """Fetch recent emails using the Gmail MCP Tool."""
    try:
        gmail_tool = GmailMCPTool()
        result = await gmail_tool.execute("gmail.read_inbox", {"max_results": 5}, current_user)
        # Parse result to return simplified email data
        emails = []
        if "messages" in result:
            for msg in result.get("messages", []):
                emails.append({"id": msg.get("id"), "snippet": msg.get("snippet", "No preview available")})
        return emails
    except Exception as e:
        logger.error(f"Error fetching dashboard emails: {e}")
        return []

@router.get("/github")
async def get_dashboard_github(current_user: User = Depends(deps.get_current_user)):
    """Fetch recent GitHub activity using the GitHub MCP Tool."""
    try:
        github_tool = GitHubMCPTool()
        result = await github_tool.execute("github.list_repositories", {}, current_user)
        return result
    except Exception as e:
        logger.error(f"Error fetching dashboard github: {e}")
        return []

@router.get("/calendar")
async def get_dashboard_calendar(current_user: User = Depends(deps.get_current_user)):
    """Fetch today's calendar events using the Calendar MCP Tool."""
    try:
        from app.services.mcp.calendar_tool import CalendarMCPTool
        calendar_tool = CalendarMCPTool()
        result = await calendar_tool.execute("calendar.list_events", {"max_results": 5}, current_user)
        events = []
        if "items" in result:
            for item in result.get("items", []):
                start = item.get("start", {}).get("dateTime") or item.get("start", {}).get("date")
                events.append({
                    "id": item.get("id"),
                    "title": item.get("summary", "Busy"),
                    "time": start,
                    "type": "video" if "hangoutLink" in item else "focus"
                })
        return events
    except Exception as e:
        logger.error(f"Error fetching dashboard calendar: {e}")
        return []
