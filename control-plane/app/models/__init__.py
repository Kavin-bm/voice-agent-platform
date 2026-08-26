"""Import every model module so Base.metadata is complete for Alembic
autogenerate and for create_all in tests."""

from app.models.agent import Agent, AgentVersion  # noqa: F401
from app.models.business import Business  # noqa: F401
from app.models.call import Call, Recording, Transcript  # noqa: F401
from app.models.campaign import Campaign, CampaignLead  # noqa: F401
from app.models.credential import TenantProviderCredential  # noqa: F401
from app.models.knowledge import Document, KnowledgeSource  # noqa: F401
from app.models.phone_number import PhoneNumber  # noqa: F401
from app.models.policy import Policy  # noqa: F401
from app.models.template import AgentTemplate, VerticalPack  # noqa: F401
from app.models.tenant import Tenant  # noqa: F401
from app.models.tool import AgentVersionTool, Tool  # noqa: F401
from app.models.usage_event import UsageEvent  # noqa: F401
from app.models.user import User  # noqa: F401
