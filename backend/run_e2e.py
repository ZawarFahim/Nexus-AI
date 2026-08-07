import asyncio
import os
import sys
from unittest.mock import patch

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory:"
os.environ["SECRET_KEY"] = "test-secret"
os.environ["OAUTH_GOOGLE_CLIENT_ID"] = "mock"
os.environ["OAUTH_GOOGLE_CLIENT_SECRET"] = "mock"
os.environ["OAUTH_GITHUB_CLIENT_ID"] = "mock"
os.environ["OAUTH_GITHUB_CLIENT_SECRET"] = "mock"
os.environ["N8N_WEBHOOK_URL"] = "http://mock"
os.environ["OPENAI_API_KEY"] = "mock"

patcher_redis = patch('app.core.redis.RedisManager.connect')
patcher_qdrant = patch('app.core.qdrant.QdrantManager.connect')
patcher_redis.start()
patcher_qdrant.start()

from fastapi.testclient import TestClient
from app.main import app
from app.db.session import engine, Base

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

asyncio.run(init_db())

client = TestClient(app)

def run_tests():
    print("Running Scenario 1: Register -> Login -> Dashboard -> Logout")
    res = client.post("/api/v1/auth/register", json={"email": "test@example.com", "password": "password", "full_name": "Test User"})
    if res.status_code != 200:
        print(f"Register Failed: {res.json()}")
        return False
        
    res = client.post("/api/v1/auth/token", data={"username": "test@example.com", "password": "password"})
    if res.status_code != 200:
        print(f"Login Failed: {res.json()}")
        return False
    
    token = res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    res = client.get("/api/v1/dashboard/tasks", headers=headers)
    if res.status_code != 200:
        print(f"Dashboard Failed: {res.json()}")
        return False

    print("Scenario 1 Passed.")
    return True

if __name__ == "__main__":
    success = run_tests()
    if not success:
        sys.exit(1)
    sys.exit(0)
