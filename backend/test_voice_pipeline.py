import asyncio
from fastapi.testclient import TestClient
from app.main import app
import wave
import io
import struct

client = TestClient(app)

def create_dummy_wav():
    buf = io.BytesIO()
    with wave.open(buf, 'wb') as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        # write 1 second of silence
        for _ in range(16000):
            w.writeframes(struct.pack('<h', 0))
    return buf.getvalue()

def test_pipeline():
    print("Testing Pipeline")
    # Get a dummy user token or just mock dependency
    from app.api import deps
    from app.models.user import User
    
    async def mock_get_current_user():
        return User(id="00000000-0000-0000-0000-000000000000", email="test@test.com")
        
    app.dependency_overrides[deps.get_current_user] = mock_get_current_user
    
    # 1. Test STT
    wav_data = create_dummy_wav()
    print("Sending /api/v1/voice/transcribe")
    res = client.post("/api/v1/voice/transcribe", files={"audio": ("test.wav", wav_data, "audio/wav")})
    print(f"Transcribe Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Text: {res.json()}")
    else:
        print(f"Error: {res.text}")
        
    # 2. Test TTS
    print("Sending /api/v1/voice/synthesize")
    res = client.post("/api/v1/voice/synthesize", json={"text": "Hello world, this is a test."})
    print(f"Synthesize Status: {res.status_code}")
    if res.status_code == 200:
        print(f"Audio received: {len(res.content)} bytes")
    else:
        print(f"Error: {res.text}")

if __name__ == "__main__":
    test_pipeline()
