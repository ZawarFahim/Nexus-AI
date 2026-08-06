import httpx
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from app.core.config import settings
from app.schemas.n8n import N8nWebhookPayload, N8nExecutionResult

logger = logging.getLogger(__name__)

class N8nClient:
    """
    Client for interacting with the n8n workflow engine.
    Implements robust retry logic for transient network failures.
    """
    def __init__(self):
        # Prefer N8N_WEBHOOK_URL if set to something other than localhost (like in Docker)
        webhook_env = getattr(settings, 'N8N_WEBHOOK_URL', '')
        base_env = getattr(settings, 'N8N_BASE_URL', 'http://localhost:5678')
        
        if webhook_env and 'localhost' not in webhook_env:
            self.base_url = webhook_env.rstrip('/')
        else:
            self.base_url = base_env.rstrip('/')
            
        self.headers = {}
        if settings.N8N_API_KEY:
            self.headers["Authorization"] = f"Bearer {settings.N8N_API_KEY}"

    async def _get_auth_info(self, user):
        from app.db.session import AsyncSessionLocal
        from app.models.settings import Settings
        from sqlalchemy import select
        
        base_url = self.base_url
        headers = self.headers.copy()
        
        if user:
            async with AsyncSessionLocal() as db:
                stmt = select(Settings).where(Settings.user_id == user.id)
                result = await db.execute(stmt)
                user_settings = result.scalars().first()
                if user_settings:
                    if user_settings.n8n_webhook_url:
                        # Assuming the user provides the base URL, we extract just the origin or use as is
                        base_url = user_settings.n8n_webhook_url.rstrip('/')
                    if user_settings.n8n_api_key:
                        headers["Authorization"] = f"Bearer {user_settings.n8n_api_key}"
                        
        return base_url, headers

    def _handle_retry_error(retry_state):
        e = retry_state.outcome.exception()
        logger.error(f"n8n workflow failed after retries: {e}")
        return N8nExecutionResult(success=False, logs=f"Network error after retries: {str(e)}")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        retry_error_callback=_handle_retry_error
    )
    async def trigger_workflow(self, payload: N8nWebhookPayload, user=None) -> N8nExecutionResult:
        """
        Trigger an n8n webhook and wait for the response.
        Automatically retries on network errors or timeouts using exponential backoff.
        """
        base_url, headers = await self._get_auth_info(user)
        # Handle case where user provided full webhook URL vs base URL
        if base_url.endswith(payload.webhook_id):
            url = base_url
        else:
            url = f"{base_url}/webhook/{payload.webhook_id}"
        
        try:
            async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
                logger.info(f"Triggering n8n workflow at {url}")
                response = await client.post(url, json=payload.data)
                
                # Check if it's a valid HTTP response
                response.raise_for_status()
                
                # Assume n8n is configured to return JSON via the 'Webhook Response' node
                try:
                    data = response.json()
                    return N8nExecutionResult(success=True, data=data)
                except ValueError:
                    return N8nExecutionResult(
                        success=True, 
                        data={"raw": response.text}, 
                        logs="Workflow returned non-JSON response."
                    )
                    
        except httpx.HTTPStatusError as e:
            logger.error(f"n8n workflow {payload.webhook_id} failed with status {e.response.status_code}: {e.response.text}")
            return N8nExecutionResult(success=False, logs=f"HTTP {e.response.status_code}: {e.response.text}")
        except (httpx.RequestError, httpx.TimeoutException) as e:
            logger.warning(f"Network error triggering n8n workflow, raising for retry: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error triggering n8n workflow {payload.webhook_id}: {e}")
            return N8nExecutionResult(success=False, logs=str(e))

# Singleton client instance
n8n_client = N8nClient()
