import io

import aiohttp
import qrcode
from aiogram import F, Router
from aiogram.filters import CommandStart
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


def _main_menu():
    kb = InlineKeyboardBuilder()
    kb.button(text="🔑 Create VPN", callback_data="action:create")
    kb.button(text="📱 My Devices", callback_data="action:devices")
    kb.button(text="🗑 Delete Device", callback_data="action:delete")
    kb.adjust(1)
    return kb.as_markup()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer("VPN Manager", reply_markup=_main_menu())


@router.callback_query(F.data == "action:menu")
async def cb_menu(callback: CallbackQuery):
    await callback.message.edit_text("VPN Manager", reply_markup=_main_menu())
    await callback.answer()


def _back_button():
    kb = InlineKeyboardBuilder()
    kb.button(text="← Back", callback_data="action:menu")
    return kb.as_markup()


@router.callback_query(F.data == "action:create")
async def cb_create(callback: CallbackQuery):
    if not callback.from_user:
        return

    telegram_id = callback.from_user.id

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
        await callback.message.edit_text(f"Failed: {e}", reply_markup=_back_button())
        await callback.answer()
        return

    config_text = data["config"]
    config_file = BufferedInputFile(config_text.encode(), filename=f"{device_name}.conf")
    qr_file = BufferedInputFile(_make_qr(config_text), filename=f"{device_name}.png")

    await callback.message.edit_text(
        f"✅ {device_name} | {data['device']['assigned_ip']}",
        reply_markup=_back_button(),
    )
    await callback.message.answer_document(config_file)
    await callback.message.answer_photo(qr_file, caption="Scan with WireGuard app")
    await callback.answer()


@router.callback_query(F.data == "action:devices")
async def cb_devices(callback: CallbackQuery):
    if not callback.from_user:
        return

    try:
        devices = await _api("GET", f"/api/vpn/devices/{callback.from_user.id}")
    except Exception as e:
        await callback.message.edit_text(f"Error: {e}", reply_markup=_back_button())
        await callback.answer()
        return

    if not devices:
        await callback.message.edit_text("No devices yet.", reply_markup=_back_button())
        await callback.answer()
        return

    lines = []
    for d in devices:
        lines.append(f"• {d['name']} — {d['assigned_ip']} ({d['created_at'][:10]})")

    await callback.message.edit_text(
        "Your devices:\n\n" + "\n".join(lines),
        reply_markup=_back_button(),
    )
    await callback.answer()


@router.callback_query(F.data == "action:delete")
async def cb_delete_list(callback: CallbackQuery):
    if not callback.from_user:
        return

    try:
        devices = await _api("GET", f"/api/vpn/devices/{callback.from_user.id}")
    except Exception as e:
        await callback.message.edit_text(f"Error: {e}", reply_markup=_back_button())
        await callback.answer()
        return

    if not devices:
        await callback.message.edit_text("No devices to delete.", reply_markup=_back_button())
        await callback.answer()
        return

    kb = InlineKeyboardBuilder()
    for d in devices:
        kb.button(text=f"❌ {d['name']} ({d['assigned_ip']})", callback_data=f"del:{d['id']}")
    kb.button(text="← Back", callback_data="action:menu")
    kb.adjust(1)

    await callback.message.edit_text("Select device to delete:", reply_markup=kb.as_markup())
    await callback.answer()


@router.callback_query(F.data.startswith("del:"))
async def cb_delete_device(callback: CallbackQuery):
    if not callback.from_user or not callback.data:
        return

    device_id = int(callback.data.split(":")[1])

    try:
        await _api("DELETE", f"/api/vpn/devices/{callback.from_user.id}/{device_id}")
        await callback.message.edit_text("Device deleted.", reply_markup=_back_button())
    except Exception as e:
        await callback.message.edit_text(f"Failed: {e}", reply_markup=_back_button())

    await callback.answer()
