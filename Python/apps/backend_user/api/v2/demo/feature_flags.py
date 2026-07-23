from typing import Annotated

from fastapi import APIRouter, Depends

from backend_user.dependencies.auth_context import AuthContext, get_auth_context
from module_shared.cache_settings import get_setting_cached

router = APIRouter(prefix="/v2/demo", tags=["v2", "demo"])


@router.get("/feature-flags")
async def demo_feature_flags(auth: Annotated[AuthContext, Depends(get_auth_context)]):
    if auth.is_demo:
        setting = await get_setting_cached("feature-flag", "demo-excluded-fields")
        excluded = setting.value if setting else []
        return {"blurred_fields": excluded}
    return {"blurred_fields": []}
