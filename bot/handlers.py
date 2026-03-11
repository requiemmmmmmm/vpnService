import io

import aiohttp
import qrcode
from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import BufferedInputFile, CallbackQuery, Message
from aiogram.utils.keyboard import InlineKeyboardBuilder

from backend.config import get_settings

settings = get_settings()
router = Router()


async def _api(method: str, path: str, **kwargs) -> dict | list:
    async with aiohttp.ClientSession() as session:
        async with session.request(method, f"{settings.backend_url}{path}", **kwargs) as resp:
            data = await resp.json()
            if resp.status >= 400:
                raise Exception(data.get("detail", "API error"))
            return data


def _make_qr(text: str) -> bytes:
    img = qrcode.make(text, box_size=8, border=2)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "VPN Manager Bot\n\n"
        "/create_vpn - Create a new VPN config\n"
        "/my_devices - List your devices\n"
        "/delete_device - Delete a device"
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
        data = await _api(
            "POST", "/api/vpn/create",
            json={"telegram_id": telegram_id, "device_name": device_name},
        )
    except Exception as e:
        await message.answer(f"Failed to create VPN config: {e}")
        return

    config_text = data["config"]
    config_file = BufferedInputFile(config_text.encode(), filename=f"{device_name}.conf")
    qr_file = BufferedInputFile(_make_qr(config_text), filename=f"{device_name}.png")

    await message.answer_document(
        config_file,
        caption=f"{device_name} | {data['device']['assigned_ip']}",
    )
    await message.answer_photo(qr_file, caption="Scan with WireGuard app")


@router.message(Command("my_devices"))
async def cmd_my_devices(message: Message):
    if not message.from_user:
        return

    try:
        devices = await _api("GET", f"/api/vpn/devices/{message.from_user.id}")
    except Exception as e:
        await message.answer(f"Error: {e}")
        return

    if not devices:
        await message.answer("No devices. Use /create_vpn to create one.")
        return

    lines = []
    for d in devices:
        lines.append(f"• {d['name']} — {d['assigned_ip']} ({d['created_at'][:10]})")

    await message.answer("Your devices:\n\n" + "\n".join(lines))


@router.message(Command("delete_device"))
async def cmd_delete_device(message: Message):
    if not message.from_user:
        return

    try:
        devices = await _api("GET", f"/api/vpn/devices/{message.from_user.id}")
    except Exception as e:
        await message.answer(f"Error: {e}")
        return

    if not devices:
        await message.answer("No devices to delete.")
        return

    kb = InlineKeyboardBuilder()
    for d in devices:
        kb.button(text=f"{d['name']} ({d['assigned_ip']})", callback_data=f"del:{d['id']}")
    kb.adjust(1)

    await message.answer("Select device to delete:", reply_markup=kb.as_markup())


@router.callback_query(lambda c: c.data and c.data.startswith("del:"))
async def cb_delete_device(callback: CallbackQuery):
    if not callback.from_user or not callback.data:
        return

    device_id = int(callback.data.split(":")[1])

    try:
        await _api("DELETE", f"/api/vpn/devices/{callback.from_user.id}/{device_id}")
        await callback.message.edit_text("Device deleted.")
    except Exception as e:
        await callback.message.edit_text(f"Failed to delete: {e}")

    await callback.answer()
