from __future__ import annotations

import asyncio

from async_upnp_client.aiohttp import AiohttpRequester
from async_upnp_client.client_factory import UpnpFactory
from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice

from .models import DeviceInfo


async def _discover_kind(profile, kind: str, timeout: float) -> list[DeviceInfo]:
    found: dict[str, DeviceInfo] = {}
    for entry in await profile.async_discover():
        location = entry.get("location")
        udn = entry.get("usn", "").split("::")[0]
        if not location or udn in found:
            continue
        found[udn] = DeviceInfo(udn=udn, name=udn, location=location, kind=kind)
    return list(found.values())


async def discover(timeout: float = 3.0) -> tuple[list[DeviceInfo], list[DeviceInfo]]:
    """SSDP scan. Returns (servers, renderers). Names are filled in on connect."""
    servers, renderers = await asyncio.gather(
        _discover_kind(DmsDevice, "server", timeout),
        _discover_kind(DmrDevice, "renderer", timeout),
    )
    return servers, renderers


async def build_device(info: DeviceInfo):
    """DeviceInfo -> concrete UpnpDevice (for MusicServer/Renderer)."""
    requester = AiohttpRequester()
    factory = UpnpFactory(requester)
    return await factory.async_create_device(info.location)
