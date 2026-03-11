import asyncio
import base64
import ipaddress
import os
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.database.models import Device
from backend.services.exceptions import IPPoolExhausted, WireGuardError

settings = get_settings()


async def _run_cmd(*args: str, stdin_data: bytes | None = None) -> str:
    proc = await asyncio.create_subprocess_exec(
        *args,
        stdin=asyncio.subprocess.PIPE if stdin_data else None,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=stdin_data)
    if proc.returncode != 0:
        raise WireGuardError(stderr.decode().strip())
    return stdout.decode().strip()


def _mock_key() -> str:
    return base64.b64encode(os.urandom(32)).decode()


async def generate_keypair() -> tuple[str, str]:
    if settings.wg_mock:
        private = _mock_key()
        public = _mock_key()
        return private, public

    private_key = await _run_cmd("wg", "genkey")
    public_key = await _run_cmd("wg", "pubkey", stdin_data=private_key.encode())
    return private_key, public_key


async def generate_preshared_key() -> str:
    if settings.wg_mock:
        return _mock_key()
    return await _run_cmd("wg", "genpsk")


async def allocate_ip(session: AsyncSession) -> str:
    result = await session.execute(select(Device.assigned_ip).with_for_update())
    used = {row[0] for row in result.all()}

    network = ipaddress.IPv4Network(settings.wg_subnet)
    for host in network.hosts():
        ip = str(host)
        if ip == settings.wg_server_ip:
            continue
        if ip not in used:
            return ip

    raise IPPoolExhausted("No available IP addresses in the pool")


async def add_peer(public_key: str, preshared_key: str, assigned_ip: str) -> None:
    if settings.wg_mock:
        return

    with tempfile.NamedTemporaryFile(mode="w", suffix=".key", delete=False) as f:
        f.write(preshared_key)
        psk_path = f.name

    try:
        await _run_cmd(
            "wg", "set", settings.wg_interface,
            "peer", public_key,
            "preshared-key", psk_path,
            "allowed-ips", f"{assigned_ip}/32",
        )
    finally:
        Path(psk_path).unlink(missing_ok=True)


async def remove_peer(public_key: str) -> None:
    if settings.wg_mock:
        return
    await _run_cmd("wg", "set", settings.wg_interface, "peer", public_key, "remove")


def generate_client_config(device: Device) -> str:
    return (
        f"[Interface]\n"
        f"PrivateKey = {device.private_key}\n"
        f"Address = {device.assigned_ip}/24\n"
        f"DNS = {settings.wg_dns}\n"
        f"\n"
        f"[Peer]\n"
        f"PublicKey = {settings.wg_server_public_key}\n"
        f"PresharedKey = {device.preshared_key}\n"
        f"AllowedIPs = 0.0.0.0/0\n"
        f"Endpoint = {settings.wg_server_endpoint}\n"
        f"PersistentKeepalive = 25\n"
    )
