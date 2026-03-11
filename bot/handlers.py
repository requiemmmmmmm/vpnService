import aiohttp
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, Message

from backend.config import get_settings

settings = get_settings()
router = Router()


async def _api_request(method: str, path: str, **kwargs) -> dict | list:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{settings.backend_url}{path}", **kwargs) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise Exception(data.get("detail", "API error"))
            return data


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "VPN Manager Bot\n\n"
        "/create_vpn - Create a new VPN configuration\n"
        "/my_devices - List your devices"
    )


@router.message(Command("create_vpn"))
async def cmd_create_vpn(message: Message):
    if not message.from_user:
        return

    telegram_id = message.from_user.id

    async with aiohttp.ClientSession() as session:
        async with session.get(f"{settings.backend_url}/api/vpn/devices/{telegram_id}") as resp:
            devices = await resp.json()
            device_count = len(devices) if isinstance(devices, list) else 0

    device_name = f"device-{device_count + 1}"

    try:
        data = await _api_request(
            "POST", "/api/vpn/create",
            json={"telegram_id": telegram_id, "device_name": device_name},
        )
    except Exception as e:
        await message.answer(f"Failed to create VPN config: {e}")
        return

    config_bytes = data["config"].encode()
    file = BufferedInputFile(config_bytes, filename=f"{device_name}.conf")
    await message.answer_document(
        file,
        caption=f"Configuration for {device_name}\nIP: {data['device']['assigned_ip']}",
    )


@router.message(Command("my_devices"))
async def cmd_my_devices(message: Message):
    if not message.from_user:
        return

    try:
        devices = await _api_request("GET", f"/api/vpn/devices/{message.from_user.id}")
    except Exception as e:
        await message.answer(f"Error: {e}")
        return

    if not devices:
        await message.answer("You have no devices yet. Use /create_vpn to create one.")
        return

    lines = []
    for d in devices:
        lines.append(f"- {d['name']} | {d['assigned_ip']} | {d['created_at'][:10]}")

    await message.answer(f"Your devices:\n\n" + "\n".join(lines))
