from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from starlette import status

from backend_user.dependencies.auth_context import AuthContext, get_auth_context

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.post("/validate", status_code=status.HTTP_200_OK)
async def validate_demo_uid(auth: Annotated[AuthContext, Depends(get_auth_context)]):
    if not auth.is_demo:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return {"status": "OK"}
