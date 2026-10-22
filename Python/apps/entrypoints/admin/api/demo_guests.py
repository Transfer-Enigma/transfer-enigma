from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.status import HTTP_404_NOT_FOUND

from data.repositories.demo_guests import (
    create_demo_guest,
    delete_demo_guest,
    get_demo_guest_by_uid,
    list_demo_guests,
    update_demo_guest,
)
from entrypoints.admin.dependencies.auth_context import bind_caller_context
from pydantic import BaseModel, Field
from shared.context import CallerContext
from shared.database import Database, get_database
from shared.dto.errors import NotFoundError, ValidationError

router = APIRouter(prefix="/demo-guests", tags=["demo-guests"])


class DemoGuestPayload(BaseModel):
    uid: str = Field(min_length=1, max_length=64)
    sea_profit: Decimal = Field(default=Decimal("0"), ge=0)
    sea_profit_currency: str = Field(default="USD", min_length=3, max_length=3)
    rail_profit: Decimal = Field(default=Decimal("0"), ge=0)
    rail_profit_currency: str = Field(default="USD", min_length=3, max_length=3)


class DemoGuestResponse(BaseModel):
    id: int  # noqa: A003
    uid: str
    sea_profit: Decimal
    sea_profit_currency: str
    rail_profit: Decimal
    rail_profit_currency: str

    @classmethod
    def from_model(cls, guest) -> "DemoGuestResponse":
        return cls(
            id=guest.id,
            uid=guest.uid,
            sea_profit=guest.sea_profit,
            sea_profit_currency=guest.sea_profit_currency,
            rail_profit=guest.rail_profit,
            rail_profit_currency=guest.rail_profit_currency,
        )


@router.get("", response_model=list[DemoGuestResponse])
async def get_demo_guests(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        guests = await list_demo_guests(session)
    return [DemoGuestResponse.from_model(guest) for guest in guests]


@router.post("", response_model=DemoGuestResponse, status_code=201)
async def create_demo_guest(
    payload: DemoGuestPayload,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    db: Annotated[Database, Depends(get_database)],
):
    uid = payload.uid.strip()
    async with db.session_context() as session:
        try:
            guest = await create_demo_guest(
                session,
                uid,
                payload.sea_profit,
                payload.sea_profit_currency,
                payload.rail_profit,
                payload.rail_profit_currency,
            )
        except ValidationError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    return DemoGuestResponse.from_model(guest)


@router.put("/{guest_id}", response_model=DemoGuestResponse)
async def update_demo_guest(
    guest_id: int,
    payload: DemoGuestPayload,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    db: Annotated[Database, Depends(get_database)],
):
    uid = payload.uid.strip()
    async with db.session_context() as session:
        try:
            guest = await update_demo_guest(
                session,
                guest_id,
                uid,
                payload.sea_profit,
                payload.sea_profit_currency,
                payload.rail_profit,
                payload.rail_profit_currency,
            )
        except NotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
        except ValidationError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
    return DemoGuestResponse.from_model(guest)


@router.delete("/{guest_id}", status_code=204)
async def delete_demo_guest(
    guest_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        try:
            await delete_demo_guest(session, guest_id)
        except NotFoundError as exc:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail=str(exc))
