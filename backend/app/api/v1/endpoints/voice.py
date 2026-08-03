from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import AsyncGenerator

from app.api import deps
from app.models.user import User
from app.services.voice_service import voice_service
from app.services.chat_service import chat_service
from app.schemas.chat import ChatMessage

router = APIRouter()

class SynthesizeRequest(BaseModel):
    text: str

@router.post("/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Transcribe an uploaded audio file using Faster Whisper.
    """
    if not audio.filename:
        raise HTTPException(status_code=400, detail="No audio file provided.")
        
    try:
        audio_bytes = await audio.read()
        text = await voice_service.transcribe_audio(audio_bytes)
        return {"text": text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/synthesize")
async def synthesize(
    request: SynthesizeRequest,
    current_user: User = Depends(deps.get_current_user)
):
    """
    Convert text to speech using Piper TTS.
    Returns a streaming WAV file.
    """
    try:
        audio_generator = voice_service.synthesize_speech(request.text)
        return StreamingResponse(audio_generator, media_type="audio/wav")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/chat")
async def voice_chat(
    conversation_id: str = None,
    audio: UploadFile = File(...),
    current_user: User = Depends(deps.get_current_user)
):
    """
    Complete Voice-to-Voice Pipeline:
    1. Transcribe incoming audio.
    2. Send transcribed text to Agent Coordinator.
    3. Synthesize the AI's response text into audio.
    4. Stream audio back.
    """
    try:
        # 1. Transcribe
        audio_bytes = await audio.read()
        user_text = await voice_service.transcribe_audio(audio_bytes)
        
        if not user_text:
            raise HTTPException(status_code=400, detail="Could not understand audio.")
            
        # 2. Get AI Response
        msg_req = ChatMessage(message=user_text, conversation_id=conversation_id)
        
        # We need the full text to synthesize, so we consume the chat stream
        # This adds latency before the first audio byte is sent. 
        # A more advanced implementation would synthesize chunk-by-chunk.
        chat_gen = chat_service.chat_stream(current_user, msg_req)
        
        full_ai_response = ""
        async for chunk in chat_gen:
            if "event" in chunk and chunk["event"] == "chunk" and "data" in chunk:
                # Basic parsing of SSE data payload
                # Note: In a real implementation we would parse the JSON properly.
                import json
                try:
                    data_obj = json.loads(chunk["data"])
                    if "chunk" in data_obj:
                        full_ai_response += data_obj["chunk"]
                except Exception:
                    pass
                    
        # Clean up markdown for TTS (e.g. remove code blocks, formatting)
        # simplified for this demo
        clean_text = full_ai_response.replace("*", "").replace("#", "")
        
        # 3. & 4. Synthesize and Stream
        audio_generator = voice_service.synthesize_speech(clean_text)
        return StreamingResponse(audio_generator, media_type="audio/wav")
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
