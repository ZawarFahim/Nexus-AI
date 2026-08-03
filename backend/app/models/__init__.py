from app.db.base_class import Base
from app.models.user import User
from app.models.conversation import Conversation, Message
from app.models.memory import Memory, Embedding
from app.models.workflow import Workflow, WorkflowLog
from app.models.task import Task
from app.models.settings import Settings, OAuthAccount, Notification, ActivityLog

# This ensures all models are imported and registered with the Base metadata.
