from collections.abc import Awaitable, Callable
from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from enum import StrEnum
from functools import wraps
from typing import ParamSpec, TypeVar

from shared.dto.errors import ResourcePermissionError

P = ParamSpec("P")
R = TypeVar("R")


class ContextKind(StrEnum):
    """Who is calling."""

    SYSTEM = "system"
    ADMIN = "admin"
    DEMO = "demo"
    USER = "user"


@dataclass
class CallerContext:
    """The caller of a use case and what they are allowed to see.

    The context is bound once per request by the entrypoint, the services
    read it instead of receiving it in every signature.
    """

    kind: ContextKind
    identity: str | None = None

    # Pricing overrides of a demo guest or of a user.
    sea_profit: float = 0.0
    sea_profit_currency: str = "USD"
    rail_profit: float = 0.0
    rail_profit_currency: str = "USD"

    # The fields the caller must not see.
    excluded_fields: list[str] = field(default_factory=list)

    # The user of a future users and roles system.
    user_id: int | None = None
    permissions: frozenset[str] = frozenset()


_current_context: ContextVar[CallerContext | None] = ContextVar("caller_context", default=None)


def get_context() -> CallerContext:
    """The context of the current call.

    Raises when nothing is bound, so a use case never runs with the
    privileges of nobody by accident.
    """
    context = _current_context.get()
    if context is None:
        raise RuntimeError("No caller context is bound")
    return context


def peek_context() -> CallerContext | None:
    """The context of the current call, or None when nothing is bound."""
    return _current_context.get()


def set_context(context: CallerContext | None) -> Token:
    """Bind the context of the current call, or unbind it when it is None."""
    return _current_context.set(context)


def reset_context(token: Token) -> None:
    """Restore the context that was bound before."""
    _current_context.reset(token)


def permissions(*kinds: ContextKind) -> Callable[[Callable[P, Awaitable[R]]], Callable[P, Awaitable[R]]]:
    """Allow only the given kinds of callers to run the function."""

    def decorator(func: Callable[P, Awaitable[R]]) -> Callable[P, Awaitable[R]]:
        @wraps(func)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            _check_caller(func.__name__, kinds)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _check_caller(name: str, kinds: tuple[ContextKind, ...]) -> None:
    try:
        context = get_context()
    except RuntimeError:
        raise ResourcePermissionError(f"No caller context is bound to call {name}") from None
    if context.kind not in kinds:
        raise ResourcePermissionError(f"{context.kind} is not allowed to call {name}")
