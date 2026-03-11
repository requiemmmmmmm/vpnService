class VPNServiceError(Exception):
    pass


class DeviceLimitReached(VPNServiceError):
    pass


class IPPoolExhausted(VPNServiceError):
    pass


class WireGuardError(VPNServiceError):
    pass
