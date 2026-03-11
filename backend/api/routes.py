from fastapi import APIRouter, HTTPException

from backend.api.schemas import CreateDeviceRequest, CreateDeviceResponse, DeviceResponse
from backend.database import async_session_maker
from backend.services import vpn

router = APIRouter(prefix="/api/vpn", tags=["vpn"])


@router.post("/create", response_model=CreateDeviceResponse)
async def create_device(req: CreateDeviceRequest):
    async with async_session_maker() as session:
        async with session.begin():
            device, config = await vpn.create_device(
                session, req.telegram_id, req.device_name
            )
            return CreateDeviceResponse(
                device=DeviceResponse.model_validate(device),
                config=config,
            )


@router.get("/devices/{telegram_id}", response_model=list[DeviceResponse])
async def get_devices(telegram_id: int):
    async with async_session_maker() as session:
        devices = await vpn.list_devices(session, telegram_id)
        return [DeviceResponse.model_validate(d) for d in devices]


@router.delete("/devices/{telegram_id}/{device_id}")
async def delete_device(telegram_id: int, device_id: int):
    async with async_session_maker() as session:
        async with session.begin():
            deleted = await vpn.delete_device(session, telegram_id, device_id)
            if not deleted:
                raise HTTPException(404, "Device not found")
            return {"status": "deleted"}


@router.get("/devices/{telegram_id}/{device_id}/config")
async def get_device_config(telegram_id: int, device_id: int):
    async with async_session_maker() as session:
        config = await vpn.get_device_config(session, telegram_id, device_id)
        if not config:
            raise HTTPException(404, "Device not found")
        return {"config": config}
