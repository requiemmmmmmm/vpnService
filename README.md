# VPN Service

Self-hosted VPN management service built with WireGuard. Manages users, devices, key generation and config distribution through a REST API and Telegram bot.

## Stack

- **FastAPI** — async REST API
- **WireGuard** — VPN backend
- **PostgreSQL** + async SQLAlchemy — storage
- **Aiogram 3** — Telegram bot
- **Docker Compose** — deployment

## Project structure

```
├── backend/
│   ├── api/
│   │   ├── routes.py          # REST endpoints
│   │   └── schemas.py         # request/response models
│   ├── database/
│   │   ├── models.py          # User, Device tables
│   │   └── session.py         # async session factory
│   ├── services/
│   │   ├── vpn.py             # core business logic
│   │   ├── wireguard.py       # wg key generation, peer management
│   │   └── exceptions.py
│   ├── config.py
│   └── main.py
├── bot/
│   ├── handlers.py            # /create_vpn, /my_devices
│   └── main.py
├── alembic/
├── docker-compose.yml
├── Dockerfile
└── requirements.txt
```

## What it does

- Generates WireGuard key pairs (private, public, preshared)
- Assigns IP addresses from a configurable subnet
- Adds peers to the WireGuard interface via `wg set`
- Produces ready-to-import `.conf` files for WireGuard clients
- Enforces a per-user device limit
- Exposes everything through REST and a Telegram bot

## Setup

### Prerequisites

A Linux VPS with root access. Ubuntu 22+ recommended.

### 1. Install WireGuard

```bash
apt update && apt install -y wireguard
wg genkey | tee /etc/wireguard/server_private.key | wg pubkey > /etc/wireguard/server_public.key
```

Create `/etc/wireguard/wg0.conf`:

```ini
[Interface]
PrivateKey = <contents of server_private.key>
Address = 10.8.0.1/24
ListenPort = 51820
PostUp = iptables -A FORWARD -i wg0 -j ACCEPT; iptables -t nat -A POSTROUTING -o ens3 -j MASQUERADE
PostDown = iptables -D FORWARD -i wg0 -j ACCEPT; iptables -t nat -D POSTROUTING -o ens3 -j MASQUERADE
```

> Replace `ens3` with your actual network interface (`ip route | grep default`).

```bash
echo "net.ipv4.ip_forward=1" >> /etc/sysctl.conf && sysctl -p
wg-quick up wg0
systemctl enable wg-quick@wg0
```

Open the port if you have a firewall:

```bash
ufw allow 51820/udp
```

### 2. Install Docker

```bash
curl -fsSL https://get.docker.com | sh
```

### 3. Clone and configure

```bash
git clone <repo-url> /root/vpn && cd /root/vpn
cp .env.example .env
```

Edit `.env`:

- `BOT_TOKEN` — get from [@BotFather](https://t.me/BotFather)
- `WG_SERVER_PUBLIC_KEY` — `cat /etc/wireguard/server_public.key`
- `WG_SERVER_ENDPOINT` — your server's public IP + `:51820`

### 4. Run

```bash
docker compose up --build -d
docker compose exec backend alembic revision --autogenerate -m "initial"
docker compose exec backend alembic upgrade head
```

### 5. Use

Open your bot in Telegram:

- `/start` — show available commands
- `/create_vpn` — generate a new device config (sends a `.conf` file)
- `/my_devices` — list your devices

Import the `.conf` file into any WireGuard client (iOS, Android, Windows, macOS, Linux).

## API

`POST /api/vpn/create`

```json
{
  "telegram_id": 123456,
  "device_name": "phone"
}
```

Returns the device info and a WireGuard config string.

`GET /api/vpn/devices/{telegram_id}`

Returns a list of devices for the given user.

## Local development

Set `WG_MOCK=true` in `.env` to skip actual WireGuard commands. Everything else works the same — key generation, IP allocation, config output, database, bot.

## License

MIT
