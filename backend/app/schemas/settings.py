from pydantic import BaseModel, ConfigDict, UUID4
import uuid
from typing import Optional

class SettingsBase(BaseModel):
    theme: Optional[str] = None
    language: Optional[str] = None
    voice_enabled: Optional[bool] = None
    default_llm: Optional[str] = None
    notifications_enabled: Optional[bool] = None
    github_pat: Optional[str] = None
    n8n_webhook_url: Optional[str] = None
    n8n_api_key: Optional[str] = None

class SettingsUpdate(SettingsBase):
    pass

class SettingsInDB(SettingsBase):
    id: str
    user_id: str

    model_config = ConfigDict(from_attributes=True)

class SettingsResponse(SettingsInDB):
    google_connected: bool = False
    google_email: Optional[str] = None
    github_connected: bool = False
    github_username: Optional[str] = None
