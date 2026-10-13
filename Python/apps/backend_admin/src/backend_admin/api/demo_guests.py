from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, HTTPException
from fastapi.params import Depends
from starlette.status import HTTP_404_NOT_FOUND

from backend_admin.dependencies.auth import request_auth
from module_shared.database import Database, get_database
from module_shared.repositories.demo_guest import get_demo_guest_by_uid, list_demo_guests
from module_shared.schemas.demo_guest import DemoGuestModel
from pydantic import BaseModel, Field

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
    def from_model(cls, model: DemoGuestModel) -> DemoGuestResponse:
        return cls(
            id=model.id,
            uid=model.uid,
            sea_profit=model.sea_profit,
            sea_profit_currency=model.sea_profit_currency,
            rail_profit=model.rail_profit,
            rail_profit_currency=model.rail_profit_currency,
        )


@router.get("", response_model=list[DemoGuestResponse])
async def get_demo_guests(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        guests = await list_demo_guests(session)
    return [DemoGuestResponse.from_model(guest) for guest in guests]


@router.post("", response_model=DemoGuestResponse, status_code=201)
async def create_demo_guest(
    payload: DemoGuestPayload,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    uid = payload.uid.strip()
    async with db.session_context() as session:
        if await get_demo_guest_by_uid(session, uid):
            raise HTTPException(status_code=409, detail="UID already exists")

        guest = DemoGuestModel(
            uid=uid,
            sea_profit=payload.sea_profit,
            sea_profit_currency=payload.sea_profit_currency,
            rail_profit=payload.rail_profit,
            rail_profit_currency=payload.rail_profit_currency,
        )
        session.add(guest)
        await session.flush()
        await session.refresh(guest)

    return DemoGuestResponse.from_model(guest)


@router.put("/{guest_id}", response_model=DemoGuestResponse)
async def update_demo_guest(
    guest_id: int,
    payload: DemoGuestPayload,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    uid = payload.uid.strip()
    async with db.session_context() as session:
        guest = await session.get(DemoGuestModel, guest_id)
        if not guest:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Demo guest not found")

        existing = await get_demo_guest_by_uid(session, uid)
        if existing and existing.id != guest_id:
            raise HTTPException(status_code=409, detail="UID already exists")

        guest.uid = uid
        guest.sea_profit = payload.sea_profit
        guest.sea_profit_currency = payload.sea_profit_currency
        guest.rail_profit = payload.rail_profit
        guest.rail_profit_currency = payload.rail_profit_currency
        await session.flush()
        await session.refresh(guest)

    return DemoGuestResponse.from_model(guest)


@router.delete("/{guest_id}", status_code=204)
async def delete_demo_guest(
    guest_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        guest = await session.get(DemoGuestModel, guest_id)
        if not guest:
            raise HTTPException(status_code=HTTP_404_NOT_FOUND, detail="Demo guest not found")
        await session.delete(guest)
