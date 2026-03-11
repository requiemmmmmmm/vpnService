from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from backend.api.routes import router
from backend.services.exceptions import DeviceLimitReached, IPPoolExhausted, WireGuardError

app = FastAPI(title="VPN Service")
app.include_router(router)


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.exception_handler(DeviceLimitReached)
async def device_limit_handler(request: Request, exc: DeviceLimitReached):
    return JSONResponse(status_code=409, content={"detail": str(exc)})


@app.exception_handler(IPPoolExhausted)
async def ip_pool_handler(request: Request, exc: IPPoolExhausted):
    return JSONResponse(status_code=503, content={"detail": str(exc)})


@app.exception_handler(WireGuardError)
async def wireguard_handler(request: Request, exc: WireGuardError):
    return JSONResponse(status_code=500, content={"detail": str(exc)})
