from __future__ import annotations

from typing import Any


def tenant_context(request) -> dict[str, Any]:
    tenant = getattr(request, "tenant", None)
    return {"current_tenant": tenant}
