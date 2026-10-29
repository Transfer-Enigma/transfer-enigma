from fastapi import APIRouter, Depends

from entrypoints.user.dependencies.auth_context import AuthContext, get_auth_context

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.get("/feature-flags")
async def get_feature_flags(
    auth: AuthContext = Depends(get_auth_context),
):
    return {"blurred_fields": ["company"] if auth.is_demo else []}
