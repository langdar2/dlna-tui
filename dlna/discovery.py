from __future__ import annotations

import asyncio
import re
import subprocess

from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.const import HttpRequest
from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice

from .models import DeviceInfo


def _lan_sources() -> list[tuple[str, int]]:
    """SSDP source addresses for broadcast-capable IPv4 interfaces.

    Excludes loopback and point-to-point VPN tunnels (utun/ppp), which have no
    broadcast address — binding there sends the multicast out the wrong link and
    finds nothing. Empty list -> caller falls back to the default route.
    """
    # ponytail: macOS/BSD ifconfig; on Linux switch to `ip -4 -o addr`.
    try:
        out = subprocess.run(["ifconfig"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.SubprocessError):
        return []
    return [(m, 0) for m in re.findall(r"inet (\d+\.\d+\.\d+\.\d+) netmask \S+ broadcast", out)]


async def _friendly_name(location: str, requester) -> str | None:
    """Pull <friendlyName> from the device description XML. None on any failure."""
    try:
        resp = await requester.async_http_request(
            HttpRequest("GET", location, {}, None))
        if resp.status_code != 200 or not resp.body:
            return None
        m = re.search(r"<friendlyName>(.*?)</friendlyName>", resp.body, re.S)
        return m.group(1).strip() if m else None
    except Exception:
        return None


async def _discover_kind(profile, kind: str, timeout: float) -> list[DeviceInfo]:
    found: dict[str, DeviceInfo] = {}
    sources = _lan_sources() or [None]
    for src in sources:
        for entry in await profile.async_search(source=src, timeout=int(timeout)):
            location = entry.get("location")
            udn = entry.get("usn", "").split("::")[0]
            if not location or udn in found:
                continue
            found[udn] = DeviceInfo(udn=udn, name=udn, location=location, kind=kind)

    requester = AiohttpRequester()
    names = await asyncio.gather(
        *(_friendly_name(d.location, requester) for d in found.values()))
    for d, name in zip(found.values(), names):
        d.name = name or d.udn
    return list(found.values())


async def discover(timeout: float = 3.0) -> tuple[list[DeviceInfo], list[DeviceInfo]]:
    """SSDP scan. Returns (servers, renderers). Names are filled in on connect."""
    servers, renderers = await asyncio.gather(
        _discover_kind(DmsDevice, "server", timeout),
        _discover_kind(DmrDevice, "renderer", timeout),
    )
    return servers, renderers


async def build_device(info: DeviceInfo, requester=None):
    """DeviceInfo -> concrete UpnpDevice (for MusicServer/Renderer).

    Pass a shared requester to avoid leaking an aiohttp session per device.
    """
    factory = UpnpFactory(requester or AiohttpRequester())
    return await factory.async_create_device(info.location)
