from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from entrypoints.user.dependencies.auth_context import AuthContext, get_auth_context

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.post("/validate")
async def validate_demo(
    uid: str,
    auth: Annotated[AuthContext, Depends(get_auth_context)],
):
    if not auth.is_demo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo access required",
        )
    return {"valid": True}
