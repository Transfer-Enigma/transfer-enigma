from typing import Annotated

from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import bind_caller_context
from shared.context import CallerContext, ContextKind

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.get("/feature-flags")
async def demo_feature_flags(context: Annotated[CallerContext, Depends(bind_caller_context)]):
    if context.kind == ContextKind.DEMO:
        return {"blurred_fields": context.excluded_fields}
    return {"blurred_fields": []}
