from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateDeviceRequest(BaseModel):
    telegram_id: int
    device_name: str


class DeviceResponse(BaseModel):
    id: int
    name: str
    assigned_ip: str
    public_key: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class CreateDeviceResponse(BaseModel):
    device: DeviceResponse
    config: str
