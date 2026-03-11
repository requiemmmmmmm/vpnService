from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import User, Device
from backend.services import wireguard
from backend.services.exceptions import DeviceLimitReached

settings = get_settings()


async def get_or_create_user(
    session: AsyncSession, telegram_id: int, username: str | None = None
) -> User:
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    user = result.scalar_one_or_none()

    if user:
        if username and user.username != username:
            user.username = username
        return user

    user = User(telegram_id=telegram_id, username=username)
    session.add(user)
    await session.flush()
    return user


async def create_device(
    session: AsyncSession, telegram_id: int, device_name: str, username: str | None = None
) -> tuple[Device, str]:
    user = await get_or_create_user(session, telegram_id, username)

    count = await session.scalar(
        select(func.count()).select_from(Device).where(Device.user_id == user.id)
    )
    if count >= settings.device_limit:
        raise DeviceLimitReached(f"Maximum {settings.device_limit} devices allowed")

    private_key, public_key = await wireguard.generate_keypair()
    preshared_key = await wireguard.generate_preshared_key()
    assigned_ip = await wireguard.allocate_ip(session)

    device = Device(
        user_id=user.id,
        name=device_name,
        private_key=private_key,
        public_key=public_key,
        preshared_key=preshared_key,
        assigned_ip=assigned_ip,
    )
    session.add(device)
    await session.flush()

    await wireguard.add_peer(public_key, preshared_key, assigned_ip)

    config = wireguard.generate_client_config(device)
    return device, config


async def list_devices(session: AsyncSession, telegram_id: int) -> list[Device]:
    result = await session.execute(
        select(Device)
        .join(User)
        .where(User.telegram_id == telegram_id)
        .order_by(Device.created_at)
    )
    return list(result.scalars().all())
