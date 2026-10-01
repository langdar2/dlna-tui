# DLNA TUI — Design

Datum: 2026-10-01

Terminal-Vollbild-Anwendung (TUI) zum Durchsuchen von Musik auf einem DLNA/UPnP-Medienserver (DMS) und Abspielen auf einem DLNA-Renderer (DMR).

## Ziel & Umfang

Voller Funktionsumfang:
- Server (DMS) und Renderer (DMR) per SSDP automatisch finden, Auswahl + Wechsel zur Laufzeit.
- ContentDirectory durchsuchen (lazy pro Ordner) und serverseitig suchen.
- Abspielen auf dem Renderer: Play/Pause/Stop/Next/Prev, Seek, Lautstärke.
- Warteschlange (Queue) mit automatischem Weiterschalten.
- Live-Status (Zustand, Position, Lautstärke) über UPnP-Events.
- Favoriten und letzte Session persistent speichern.

Nicht im Umfang: Transcoding, lokale Dateiwiedergabe, Gapless-Garantie, Multiroom-Sync, Video.

## Stack

- **Python 3.13**, async.
- **`async-upnp-client`** für SSDP-Discovery und die DLNA-Profile `DmsDevice` (ContentDirectory) und `DmrDevice` (AVTransport/RenderingControl inkl. GENA-Event-Abo). Begründung: fertige DLNA-Profile, Async, dieselbe Lib wie Home Assistant.
- **`textual`** für die TUI.

Verworfen: `upnpclient` (sync, kein DLNA-Profil, kein Event-Abo); UPnP/SOAP selbst implementieren (gelöstes Problem).

## Architektur

```
dlna-tui/
  dlna/
    discovery.py   # SSDP: DMS + DMR finden
    server.py      # DMS: browse/search ContentDirectory -> Track/Container
    renderer.py    # DMR: play/pause/stop/seek/volume + Event-Abo
    models.py      # Track, Container, DeviceInfo (dataclasses), DIDL-Parsing
    store.py       # Favoriten + letzte Session -> JSON in ~/.config/dlna-tui/
  ui/
    app.py         # Textual App, Screens, Keybindings
    widgets.py     # Browser-Tree, Queue-Liste, Now-Playing-Bar
  __main__.py      # Einstieg: discovery -> UI starten
```

Grenzen: `dlna/` hat keine Textual-Abhängigkeit (pur testbar). `ui/` kennt kein SOAP. Austausch nur über die dataclasses aus `models.py`.

## Komponenten

### models.py
- `DeviceInfo(udn, name, location, kind)` — kind ∈ {server, renderer}.
- `Container(id, title, child_count)` — Ordner im ContentDirectory.
- `Track(id, title, artist, album, duration, media_url, didl)` — `didl` ist das rohe DIDL-Lite-XML-Fragment (wird dem Renderer bei `SetAVTransportURI` mitgegeben).
- DIDL-Parsing: XML (`xml.etree.ElementTree`) -> `Track`/`Container`.

### discovery.py
- `async discover() -> tuple[list[DeviceInfo], list[DeviceInfo]]` — SSDP-Scan (~3s Timeout), getrennt nach DMS und DMR.
- Rescan auf Abruf.

### server.py
- `DmsDevice` um `DeviceInfo` herum.
- `async browse(object_id="0") -> list[Container | Track]` — ein Ordner, lazy.
- `async search(query) -> list[Track]` — `ContentDirectory.Search`; Fallback auf Browse+lokaler Filter, wenn der Server Search nicht unterstützt.

### renderer.py
- `DmrDevice` um `DeviceInfo` herum.
- Steuerung: `play(track)`, `pause()`, `stop()`, `seek(pos)`, `set_volume(v)`.
- Queue im App-State (nicht hier); `renderer.py` meldet nur `TransportState`.
- Event-Abo (GENA) -> Callback mit Zustand/Position/Lautstärke; Position-Polling 1×/s als Fallback.
- Zentraler Wrapper um alle DMR-Calls fängt `UpnpError`/Timeout und meldet an die UI statt zu crashen.

### store.py
- Eine JSON-Datei in `~/.config/dlna-tui/store.json`.
- Favoriten (Track-/Container-Referenzen) + letzte Session (gewählte Geräte-UDNs + Queue).
- Korrupte Datei -> ignorieren und neu anlegen.

### ui/
- `app.py`: Textual-App mit Panels Browser / Queue / Now-Playing-Bar; Geräteauswahl-Screen; Such-Eingabe; Toast-Meldungen.
- `widgets.py`: Tree für Browser, ListView für Queue, Statusleiste.

## Datenfluss

1. Start -> `discover()` -> Geräte. Zuletzt genutzte aus `store` vorausgewählt, sonst Auswahl-Screen.
2. Browser zeigt `browse("0")`; Enter auf Container -> erneut `browse(child)`; Enter auf Track -> abspielen; `a` -> an Queue anhängen.
3. Abspielen: `SetAVTransportURI(media_url, didl)` -> `Play`.
4. Queue-Advance: bei Event `TransportState == STOPPED` nächsten Track setzen.
   - ponytail: STOPPED-basiertes Advance; Upgrade auf `SetNextAVTransportURI`, falls der Renderer das meldet.
5. Live-Status: Events pushen die Now-Playing-Bar; Position-Polling als Fallback.
6. Beim Beenden: Session in `store` schreiben.

## Fehlerbehandlung

- Discovery leer -> Hinweis + `r` zum Rescan, kein Crash.
- SOAP-Call scheitert -> Toast, Aktion abgebrochen, App läuft weiter.
- Gerät verschwindet (Abo bricht) -> Status "getrennt" + Angebot neu zu verbinden.
- Korrupte `store.json` -> ignorieren + neu anlegen.

## Tests

Eine laufende Prüfung pro nicht-trivialer Logik, kein Framework-Overkill:
- `models.py`: DIDL-XML -> Track (echtes DIDL-Sample als Fixture).
- `server.py`: Browse-Response-Parsing (gemockte SOAP-Antwort).
- `renderer.py`: Queue-Advance-Logik bei STOPPED-Event.
- `store.py`: Round-trip speichern/laden + korrupte Datei.
- UI: manuell (Textual-TUI), nicht automatisiert.

## Keybindings

`↑↓/jk` navigieren · `Enter` öffnen/abspielen · `a` Queue · `Space` Play/Pause · `n/p` next/prev · `←→` seek · `+/-` Lautstärke · `f` Favorit · `d` Geräte · `/` Suche · `r` rescan · `q` beenden.
