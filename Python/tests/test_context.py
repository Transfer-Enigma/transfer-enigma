import pytest
from shared.context import (
    CallerContext,
    ContextKind,
    get_context,
    permissions,
    reset_context,
    set_context,
)
from shared.dto.errors import ResourcePermissionError


def test_get_context_raises_when_unbound():
    reset_context(set_context(None))
    with pytest.raises(RuntimeError):
        get_context()


def test_context_roundtrip():
    ctx = CallerContext(kind=ContextKind.ADMIN)
    token = set_context(ctx)
    try:
        assert get_context() is ctx
    finally:
        reset_context(token)
    with pytest.raises(RuntimeError):
        get_context()


@pytest.mark.asyncio
async def test_permissions_allows_admin():
    @permissions(ContextKind.ADMIN)
    async def fn():
        return "ok"

    ctx = CallerContext(kind=ContextKind.ADMIN)
    token = set_context(ctx)
    try:
        assert await fn() == "ok"
    finally:
        reset_context(token)


@pytest.mark.asyncio
async def test_permissions_rejects_non_admin():
    @permissions(ContextKind.ADMIN)
    async def fn():
        return "ok"

    ctx = CallerContext(kind=ContextKind.DEMO)
    token = set_context(ctx)
    try:
        with pytest.raises(ResourcePermissionError):
            await fn()
    finally:
        reset_context(token)
