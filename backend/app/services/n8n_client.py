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
        self.base_url = settings.N8N_BASE_URL.rstrip('/')
        self.headers = {}
        if settings.N8N_API_KEY:
            # Depending on how n8n is configured, webhooks might use header auth or query auth
            # Assuming header auth for secure webhooks
            self.headers["Authorization"] = f"Bearer {settings.N8N_API_KEY}"

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.RequestError, httpx.TimeoutException)),
        reraise=True
    )
    async def trigger_workflow(self, payload: N8nWebhookPayload) -> N8nExecutionResult:
        """
        Trigger an n8n webhook and wait for the response.
        Automatically retries on network errors or timeouts using exponential backoff.
        """
        url = f"{self.base_url}/webhook/{payload.webhook_id}"
        
        try:
            async with httpx.AsyncClient(headers=self.headers, timeout=30.0) as client:
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
        except Exception as e:
            logger.error(f"Unexpected error triggering n8n workflow {payload.webhook_id}: {e}")
            return N8nExecutionResult(success=False, logs=str(e))

# Singleton client instance
n8n_client = N8nClient()
