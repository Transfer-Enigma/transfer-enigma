from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Query
from fastapi.params import Depends

from data.cache.settings import delete_settings_cache, set_settings_cache
from data.repositories.admin.crud_companies import crud_companies
from data.repositories.admin.crud_containers import crud_containers
from data.repositories.admin.crud_drop_off import crud_drop_off
from data.repositories.admin.crud_points import crud_points
from data.repositories.admin.crud_route_segments import crud_route_segments
from data.repositories.admin.crud_services import crud_services
from data.repositories.admin.crud_settings import crud_settings
from data.repositories.admin.schemas import (
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
    RouteSegmentStatsResponse,
    ServiceCreate,
    ServicePatch,
    ServiceResponse,
    SettingCreate,
    SettingPatch,
    SettingResponse,
)
from entrypoints.admin.dependencies.auth_context import bind_caller_context
from shared.context import CallerContext
from shared.dto.setting import SettingItem

router = APIRouter(prefix="/db", tags=["data-browser"])


# ─── Companies ────────────────────────────────────────────────────────────────


@router.get("/companies", response_model=list[CompanyResponse])
async def list_companies(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    q: str = Query("", description="Search by name"),
):
    return await crud_companies.list(q=q)


@router.get("/companies/{company_id}", response_model=CompanyResponse)
async def get_company(
    company_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_companies.get(company_id)


@router.post("/companies", response_model=CompanyResponse, status_code=201)
async def create_company(
    payload: CompanyCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_companies.create(payload)


@router.put("/companies/{company_id}", response_model=CompanyResponse)
async def update_company(
    company_id: int,
    payload: CompanyCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_companies.update(company_id, payload)


@router.patch("/companies/{company_id}", response_model=CompanyResponse)
async def patch_company(
    company_id: int,
    payload: CompanyPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_companies.patch(company_id, payload)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_companies.delete(company_id)


# ─── Points ────────────────────────────────────────────────────────────────────


@router.get("/points", response_model=list[PointResponse])
async def list_points(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    city: str = Query("", description="Filter by city"),
    country: str = Query("", description="Filter by country"),
):
    return await crud_points.list(city=city, country=country)


@router.get("/points/{point_id}", response_model=PointResponse)
async def get_point(
    point_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_points.get(point_id)


@router.post("/points", response_model=PointResponse, status_code=201)
async def create_point(
    payload: PointCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_points.create(payload)


@router.put("/points/{point_id}", response_model=PointResponse)
async def update_point(
    point_id: int,
    payload: PointCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_points.update(point_id, payload)


@router.patch("/points/{point_id}", response_model=PointResponse)
async def patch_point(
    point_id: int,
    payload: PointPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_points.patch(point_id, payload)


@router.delete("/points/{point_id}", status_code=204)
async def delete_point(
    point_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_points.delete(point_id)


# ─── Containers ────────────────────────────────────────────────────────────────


@router.get("/containers", response_model=list[ContainerResponse])
async def list_containers(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    size: int | None = Query(None, description="Filter by size"),
    type: str | None = Query(None, description="Filter by type (DC/HC)"),  # noqa: A002
    weight_from: float | None = Query(None, description="Min weight"),
    weight_to: float | None = Query(None, description="Max weight"),
):
    return await crud_containers.list(
        size=size, type=type, weight_from=weight_from, weight_to=weight_to
    )


@router.get("/containers/{container_id}", response_model=ContainerResponse)
async def get_container(
    container_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_containers.get(container_id)


@router.post("/containers", response_model=ContainerResponse, status_code=201)
async def create_container(
    payload: ContainerCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_containers.create(payload)


@router.put("/containers/{container_id}", response_model=ContainerResponse)
async def update_container(
    container_id: int,
    payload: ContainerCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_containers.update(container_id, payload)


@router.patch("/containers/{container_id}", response_model=ContainerResponse)
async def patch_container(
    container_id: int,
    payload: ContainerPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_containers.patch(container_id, payload)


@router.delete("/containers/{container_id}", status_code=204)
async def delete_container(
    container_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_containers.delete(container_id)


# ─── Route Segments ─────────────────────────────────────────────────────────────


@router.get("/route-segments", response_model=list[RouteSegmentListResponse])
async def list_route_segments(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    company_id: int | None = Query(None),
    start_point_id: int | None = Query(None),
    end_point_id: int | None = Query(None),
    type: str | None = Query(None),  # noqa: A002
):
    return await crud_route_segments.list(
        company_id=company_id, start_point_id=start_point_id, end_point_id=end_point_id, type=type
    )


@router.get("/route-segments/stats", response_model=RouteSegmentStatsResponse)
async def route_segments_stats(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_route_segments.stats()


@router.get("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def get_route_segment(
    segment_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_route_segments.get(segment_id)


@router.post("/route-segments", response_model=RouteSegmentResponse, status_code=201)
async def create_route_segment(
    payload: RouteSegmentCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_route_segments.create(payload)


@router.put("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def update_route_segment(
    segment_id: int,
    payload: RouteSegmentCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_route_segments.update(segment_id, payload)


@router.patch("/route-segments/{segment_id}", response_model=RouteSegmentResponse)
async def patch_route_segment(
    segment_id: int,
    payload: RouteSegmentPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_route_segments.patch(segment_id, payload)


@router.delete("/route-segments/{segment_id}", status_code=204)
async def delete_route_segment(
    segment_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_route_segments.delete(segment_id)


# ─── Services ──────────────────────────────────────────────────────────────────


@router.get("/services", response_model=list[ServiceResponse])
async def list_services(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    q: str = Query("", description="Search by name or internal_name"),
):
    return await crud_services.list(q=q)


@router.get("/services/{service_id}", response_model=ServiceResponse)
async def get_service(
    service_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_services.get(service_id)


@router.post("/services", response_model=ServiceResponse, status_code=201)
async def create_service(
    payload: ServiceCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_services.create(payload)


@router.put("/services/{service_id}", response_model=ServiceResponse)
async def update_service(
    service_id: int,
    payload: ServiceCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_services.update(service_id, payload)


@router.patch("/services/{service_id}", response_model=ServiceResponse)
async def patch_service(
    service_id: int,
    payload: ServicePatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_services.patch(service_id, payload)


@router.delete("/services/{service_id}", status_code=204)
async def delete_service(
    service_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_services.delete(service_id)


# ─── Drop-off ──────────────────────────────────────────────────────────────────


@router.get("/drop-off", response_model=list[DropOffResponse])
async def list_drop_off(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    company_id: int | None = Query(None),
    container_id: int | None = Query(None),
):
    return await crud_drop_off.list(company_id=company_id, container_id=container_id)


@router.get("/drop-off/{drop_id}", response_model=DropOffResponse)
async def get_drop_off(
    drop_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_drop_off.get(drop_id)


@router.post("/drop-off", response_model=DropOffResponse, status_code=201)
async def create_drop_off(
    payload: DropOffCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_drop_off.create(payload)


@router.put("/drop-off/{drop_id}", response_model=DropOffResponse)
async def update_drop_off(
    drop_id: int,
    payload: DropOffCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_drop_off.update(drop_id, payload)


@router.patch("/drop-off/{drop_id}", response_model=DropOffResponse)
async def patch_drop_off(
    drop_id: int,
    payload: DropOffPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_drop_off.patch(drop_id, payload)


@router.delete("/drop-off/{drop_id}", status_code=204)
async def delete_drop_off(
    drop_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    await crud_drop_off.delete(drop_id)


# ─── Settings ──────────────────────────────────────────────────────────────────


@router.get("/settings", response_model=list[SettingResponse])
async def list_settings(
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    group: str = Query("", description="Filter by group"),
    q: str = Query("", description="Search by name"),
):
    return await crud_settings.list(group=group, q=q)


@router.get("/settings/{setting_id}", response_model=SettingResponse)
async def get_setting(
    setting_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
):
    return await crud_settings.get(setting_id)


@router.post("/settings", response_model=SettingResponse, status_code=201)
async def create_setting(
    payload: SettingCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    background_tasks: BackgroundTasks,
):
    result = await crud_settings.create(payload)
    background_tasks.add_task(set_settings_cache, SettingItem(**result.model_dump()))
    return result


@router.put("/settings/{setting_id}", response_model=SettingResponse)
async def update_setting(
    setting_id: int,
    payload: SettingCreate,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    background_tasks: BackgroundTasks,
):
    old = await crud_settings.get(setting_id)
    result = await crud_settings.update(setting_id, payload)
    background_tasks.add_task(set_settings_cache, SettingItem(**result.model_dump()))
    if old.group != result.group or old.name != result.name:
        background_tasks.add_task(delete_settings_cache, old.group, old.name)
    return result


@router.patch("/settings/{setting_id}", response_model=SettingResponse)
async def patch_setting(
    setting_id: int,
    payload: SettingPatch,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    background_tasks: BackgroundTasks,
):
    old = await crud_settings.get(setting_id)
    result = await crud_settings.patch(setting_id, payload)
    background_tasks.add_task(set_settings_cache, SettingItem(**result.model_dump()))
    if old.group != result.group or old.name != result.name:
        background_tasks.add_task(delete_settings_cache, old.group, old.name)
    return result


@router.delete("/settings/{setting_id}", status_code=204)
async def delete_setting(
    setting_id: int,
    _: Annotated[CallerContext, Depends(bind_caller_context)],
    background_tasks: BackgroundTasks,
):
    result = await crud_settings.delete(setting_id)
    background_tasks.add_task(delete_settings_cache, result.group, result.name)
