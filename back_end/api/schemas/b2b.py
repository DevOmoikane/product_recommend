from pydantic import BaseModel
from typing import Optional


class TenantContext(BaseModel):
    tenant_id: Optional[str] = None
    client_id: Optional[str] = None


class TenantContextMixin(BaseModel):
    tenant_id: Optional[str] = None