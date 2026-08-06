import asyncio
import httpx
from unittest.mock import patch, AsyncMock, MagicMock
from app.services.n8n_client import n8n_client
from app.schemas.n8n import N8nWebhookPayload

async def run_tests():
    print("Testing URL builder fallback...")
    
    # Test 1: Fallback logic
    with patch('app.services.n8n_client.settings') as mock_settings:
        mock_settings.N8N_WEBHOOK_URL = "http://n8n:5678"
        mock_settings.N8N_BASE_URL = "http://localhost:5678"
        mock_settings.N8N_API_KEY = "test_key"
        
        # Need to re-init to pick up mocked settings
        n8n_client.__init__()
        assert n8n_client.base_url == "http://n8n:5678", f"Base URL should be http://n8n:5678, got {n8n_client.base_url}"
        assert n8n_client.headers["Authorization"] == "Bearer test_key"
        print("URL builder passed.")

    # Test 2: Retry logic
    print("Testing retry logic...")
    payload = N8nWebhookPayload(webhook_id="test-webhook", data={"key": "value"})
    
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        # Make it fail twice then succeed
        mock_response = MagicMock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"status": "ok"}
        
        mock_post.side_effect = [
            httpx.ConnectError("Connection refused"),
            httpx.TimeoutException("Timeout"),
            mock_response
        ]
        
        # We need to temporarily speed up wait times for test
        from tenacity import wait_none
        n8n_client.trigger_workflow.retry.wait = wait_none()
        
        result = await n8n_client.trigger_workflow(payload)
        
        assert result.success is True
        assert result.data == {"status": "ok"}
        assert mock_post.call_count == 3, f"Expected 3 calls, got {mock_post.call_count}"
        print("Retry logic passed.")
        
    # Test 3: Total Failure Retry logic
    print("Testing retry failure...")
    with patch('httpx.AsyncClient.post', new_callable=AsyncMock) as mock_post:
        mock_post.side_effect = httpx.ConnectError("Connection refused")
        
        result = await n8n_client.trigger_workflow(payload)
        
        assert result.success is False
        assert "Network error after retries" in result.logs
        assert mock_post.call_count == 3
        print("Retry failure logic passed.")

if __name__ == "__main__":
    asyncio.run(run_tests())
