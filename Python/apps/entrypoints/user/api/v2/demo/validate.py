from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from entrypoints.user.dependencies.auth_context import bind_caller_context
from shared.context import CallerContext, ContextKind

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_demo_uid(context: Annotated[CallerContext, Depends(bind_caller_context)]):
    if context.kind != ContextKind.DEMO:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"status": "OK"}
