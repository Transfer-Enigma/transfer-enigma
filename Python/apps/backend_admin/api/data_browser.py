from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.params import Depends

from backend_admin.dependencies.auth import request_auth
from backend_admin.schemas.data_browser import (
    CompanyCreate,
    CompanyPatch,
    CompanyResponse,
    ContainerCreate,
    ContainerPatch,
    ContainerResponse,
    DropOffCreate,
    DropOffPatch,
    DropOffResponse,
    PointCreate,
    PointPatch,
    PointResponse,
    RouteSegmentCreate,
    RouteSegmentListResponse,
    RouteSegmentPatch,
    RouteSegmentResponse,
    ServiceCreate,
    ServicePatch,
    ServiceResponse,
)
from backend_admin.service.crud_companies import crud_companies
from backend_admin.service.crud_containers import crud_containers
from backend_admin.service.crud_drop_off import crud_drop_off
from backend_admin.service.crud_points import crud_points
from backend_admin.service.crud_route_segments import crud_route_segments
from backend_admin.service.crud_services import crud_services
from module_shared.database import Database, get_database

router = APIRouter(prefix="/db", tags=["data-browser"])


# ─── Companies ────────────────────────────────────────────────────────────────


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    q: str = Query("", description="Search by name"),
):
    async with db.session_context() as session:
        return await crud_companies.list(session, q=q)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_companies.get(session, company_id)


@router.post("/companies", response_model=CompanyResponse, status_code=201)
async def create_company(
    payload: CompanyCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_companies.create(session, payload)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    payload: CompanyCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_companies.update(session, company_id, payload)


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def patch_company(
    company_id: int,
    payload: CompanyPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_companies.patch(session, company_id, payload)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_companies.delete(session, company_id)


# ─── Points ────────────────────────────────────────────────────────────────────


@router.get("/points", response_model=list[PointResponse])
async def list_points(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    city: str = Query("", description="Filter by city"),
    country: str = Query("", description="Filter by country"),
):
    async with db.session_context() as session:
        return await crud_points.list(session, city=city, country=country)


@router.get("/points/{point_id}", response_model=PointResponse)
async def get_point(
    point_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_points.get(session, point_id)


@router.post("/points", response_model=PointResponse, status_code=201)
async def create_point(
    payload: PointCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_points.create(session, payload)


@router.put("/points/{point_id}", response_model=PointResponse)
async def update_point(
    point_id: int,
    payload: PointCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_points.update(session, point_id, payload)


@router.patch("/points/{point_id}", response_model=PointResponse)
async def patch_point(
    point_id: int,
    payload: PointPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_points.patch(session, point_id, payload)


@router.delete("/points/{point_id}", status_code=204)
async def delete_point(
    point_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_points.delete(session, point_id)


# ─── Containers ────────────────────────────────────────────────────────────────


@router.get("/containers", response_model=list[ContainerResponse])
async def list_containers(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    size: int | None = Query(None, description="Filter by size"),
    type: str | None = Query(None, description="Filter by type (DC/HC)"),  # noqa: A002
    weight_from: float | None = Query(None, description="Min weight"),
    weight_to: float | None = Query(None, description="Max weight"),
):
    async with db.session_context() as session:
        return await crud_containers.list(session, size=size, type=type, weight_from=weight_from, weight_to=weight_to)


@router.get("/containers/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_containers.get(session, container_id)


@router.post("/containers", response_model=ContainerResponse, status_code=201)
async def create_container(
    payload: ContainerCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_containers.create(session, payload)


@router.put("/containers/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: int,
    payload: ContainerCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_containers.update(session, container_id, payload)


@router.patch("/containers/{container_id}", response_model=ContainerResponse)
async def patch_container(
    container_id: int,
    payload: ContainerPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_containers.patch(session, container_id, payload)


@router.delete("/containers/{container_id}", status_code=204)
async def delete_container(
    container_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_containers.delete(session, container_id)


# ─── Route Segments ─────────────────────────────────────────────────────────────


@router.get("/route-segments", response_model=list[RouteSegmentListResponse])
async def list_route_segments(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    company_id: int | None = Query(None),
    start_point_id: int | None = Query(None),
    end_point_id: int | None = Query(None),
    type: str | None = Query(None),  # noqa: A002
):
    async with db.session_context() as session:
        return await crud_route_segments.list(
            session, company_id=company_id, start_point_id=start_point_id, end_point_id=end_point_id, type=type
        )


@router.get("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def get_route_segment(
    segment_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_route_segments.get(session, segment_id)


@router.post("/route-segments", response_model=RouteSegmentResponse, status_code=201)
async def create_route_segment(
    payload: RouteSegmentCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_route_segments.create(session, payload)


@router.put("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def update_route_segment(
    segment_id: int,
    payload: RouteSegmentCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_route_segments.update(session, segment_id, payload)


@router.patch("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def patch_route_segment(
    segment_id: int,
    payload: RouteSegmentPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_route_segments.patch(session, segment_id, payload)


@router.delete("/route-segments/{segment_id}", status_code=204)
async def delete_route_segment(
    segment_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_route_segments.delete(session, segment_id)


# ─── Services ──────────────────────────────────────────────────────────────────


@router.get("/services", response_model=list[ServiceResponse])
async def list_services(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    q: str = Query("", description="Search by name or internal_name"),
):
    async with db.session_context() as session:
        return await crud_services.list(session, q=q)


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_services.get(session, service_id)


@router.post("/services", response_model=ServiceResponse, status_code=201)
async def create_service(
    payload: ServiceCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_services.create(session, payload)


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    payload: ServiceCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_services.update(session, service_id, payload)


@router.patch("/services/{service_id}", response_model=ServiceResponse)
async def patch_service(
    service_id: int,
    payload: ServicePatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_services.patch(session, service_id, payload)


@router.delete("/services/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_services.delete(session, service_id)


# ─── Drop-off ──────────────────────────────────────────────────────────────────


@router.get("/drop-off", response_model=list[DropOffResponse])
async def list_drop_off(
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
    company_id: int | None = Query(None),
    container_id: int | None = Query(None),
):
    async with db.session_context() as session:
        return await crud_drop_off.list(session, company_id=company_id, container_id=container_id)


@router.get("/drop-off/{drop_id}", response_model=DropOffResponse)
async def get_drop_off(
    drop_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_drop_off.get(session, drop_id)


@router.post("/drop-off", response_model=DropOffResponse, status_code=201)
async def create_drop_off(
    payload: DropOffCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_drop_off.create(session, payload)


@router.put("/drop-off/{drop_id}", response_model=DropOffResponse)
async def update_drop_off(
    drop_id: int,
    payload: DropOffCreate,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_drop_off.update(session, drop_id, payload)


@router.patch("/drop-off/{drop_id}", response_model=DropOffResponse)
async def patch_drop_off(
    drop_id: int,
    payload: DropOffPatch,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        return await crud_drop_off.patch(session, drop_id, payload)


@router.delete("/drop-off/{drop_id}", status_code=204)
async def delete_drop_off(
    drop_id: int,
    _: Annotated[None, Depends(request_auth)],
    db: Annotated[Database, Depends(get_database)],
):
    async with db.session_context() as session:
        await crud_drop_off.delete(session, drop_id)
