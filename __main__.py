from __future__ import annotations

import asyncio
import sys

from async_upnp_client.aiohttp import AiohttpNotifyServer, AiohttpRequester
from async_upnp_client.event_handler import UpnpEventHandler

from dlna.discovery import discover
from dlna.store import Store
from ui.app import DlnaApp


def _auto(devices, preferred_udn):
    """Initial pick: last-used device if still present, else the first found."""
    if not devices:
        return None
    for d in devices:
        if d.udn == preferred_udn:
            return d
    return devices[0]


async def main() -> None:
    store = Store()
    print("Suche Geräte…")
    servers, renderers = await discover()
    if not servers and not renderers:
        print("Keine Geräte gefunden.")
        sys.exit(1)

    # v0.46.2 API: UpnpEventHandler takes a UpnpNotifyServer (not a callback URL string).
    # AiohttpNotifyServer binds a local HTTP server for GENA event callbacks;
    # source ("0.0.0.0", 0) lets the OS pick a free port. One shared requester
    # serves discovery, both devices, and events so we leak no extra sessions.
    requester = AiohttpRequester()
    notify_server = AiohttpNotifyServer(requester, ("0.0.0.0", 0))
    await notify_server.async_start_server()
    event_handler = UpnpEventHandler(notify_server, requester)

    try:
        app = DlnaApp(
            store, requester, event_handler,
            srv_info=_auto(servers, store.last_server),
            rnd_info=_auto(renderers, store.last_renderer),
        )
        await app.run_async()
    finally:
        await notify_server.async_stop_server()


if __name__ == "__main__":
    asyncio.run(main())
