from __future__ import annotations

import asyncio
import sys

from async_upnp_client.aiohttp import AiohttpNotifyServer, AiohttpRequester
from async_upnp_client.event_handler import UpnpEventHandler
from async_upnp_client.profiles.dlna import DmrDevice, DmsDevice

from dlna.discovery import build_device, discover
from dlna.renderer import Renderer
from dlna.server import MusicServer
from dlna.store import Store
from ui.app import DlnaApp


def _pick(devices, label, preferred_udn):
    if not devices:
        print(f"Kein {label} gefunden.")
        sys.exit(1)
    for d in devices:
        if d.udn == preferred_udn:
            return d
    if len(devices) == 1:
        return devices[0]
    for i, d in enumerate(devices):
        print(f"[{i}] {label}: {d.name} ({d.location})")
    return devices[int(input(f"{label} wählen: "))]


async def main() -> None:
    store = Store()
    print("Suche Geräte…")
    servers, renderers = await discover()
    srv_info = _pick(servers, "Server", store.last_server)
    rnd_info = _pick(renderers, "Renderer", store.last_renderer)

    srv_dev = await build_device(srv_info)
    rnd_dev = await build_device(rnd_info)

    # v0.46.2 API: UpnpEventHandler takes a UpnpNotifyServer (not a callback URL string).
    # AiohttpNotifyServer binds a local HTTP server for GENA event callbacks;
    # source ("0.0.0.0", 0) lets the OS pick a free port.
    requester = AiohttpRequester()
    notify_server = AiohttpNotifyServer(requester, ("0.0.0.0", 0))
    await notify_server.async_start_server()
    event_handler = UpnpEventHandler(notify_server, requester)

    # DmsDevice / DmrDevice accept event_handler as a positional arg (not keyword).
    server = MusicServer(DmsDevice(srv_dev, event_handler))
    renderer = Renderer(DmrDevice(rnd_dev, event_handler))

    store.last_server = srv_info.udn
    store.last_renderer = rnd_info.udn
    store.save()

    await DlnaApp(server, renderer, store).run_async()


if __name__ == "__main__":
    asyncio.run(main())
