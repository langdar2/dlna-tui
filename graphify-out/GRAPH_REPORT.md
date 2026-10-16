# Graph Report - dlna TerminalClient  (2026-10-16)

## Corpus Check
- 26 files · ~14,777 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 362 nodes · 847 edges · 15 communities (14 shown, 1 thin omitted)
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 143 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b29164a2`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- [[_COMMUNITY_Community 0|Community 0]]
- [[_COMMUNITY_Community 1|Community 1]]
- [[_COMMUNITY_Community 2|Community 2]]
- [[_COMMUNITY_Community 3|Community 3]]
- [[_COMMUNITY_Community 4|Community 4]]
- [[_COMMUNITY_Community 5|Community 5]]
- [[_COMMUNITY_Community 6|Community 6]]
- [[_COMMUNITY_Community 7|Community 7]]
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `DlnaApp` - 74 edges
2. `Track` - 58 edges
3. `Queue` - 45 edges
4. `Renderer` - 36 edges
5. `Store` - 29 edges
6. `ComposeResult` - 26 edges
7. `Container` - 24 edges
8. `MusicServer` - 24 edges
9. `NowPlaying` - 20 edges
10. `RendererState` - 17 edges

## Surprising Connections (you probably didn't know these)
- `DlnaApp` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `Changed` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py
- `ComposeResult` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py
- `NodeExpanded` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py
- `NodeSelected` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py

## Import Cycles
- None detected.

## Communities (15 total, 1 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.12
Nodes (22): _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _is_audio(), _media_info(), Queue, Forget what's queued behind the current track, keeping it playing.         Switc (+14 more)

### Community 1 - "Community 1"
Cohesion: 0.08
Nodes (31): Changed, ComposeResult, Container, Container, MusicServer, Track, default_path(), Path (+23 more)

### Community 2 - "Community 2"
Cohesion: 0.06
Nodes (20): build_device(), DeviceInfo -> concrete UpnpDevice (for MusicServer/Renderer).      Pass a shared, ListItem, test_threshold_follows_the_scrobble_rule(), DlnaApp, _hms_seconds(), play_threshold(), Send current playback info to optional pixel display. (+12 more)

### Community 4 - "Community 4"
Cohesion: 0.07
Nodes (35): Track, RendererState, _app(), FakeRenderer, _listen(), test_a_short_interlude_is_neither_a_play_nor_a_skip(), test_long_track_needs_half_its_length(), test_moving_on_after_a_full_listen_is_not_a_skip() (+27 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): Architektur, Datenfluss, discovery.py, DLNA TUI — Design, Fehlerbehandlung, Keybindings, Komponenten, models.py (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (13): Bekannte Risiken (am Gerät verifizieren), Dateistruktur, DLNA TUI Implementation Plan, Self-Review (durchgeführt), Task 0: Projekt-Setup, Task 1: Modelle + DIDL-Adapter, Task 2: Queue-Logik (rein), Task 3: Store (Favoriten + Session) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.13
Nodes (33): _basename(), _best_match(), _common_tail(), count_play(), _crate_path_of(), _crate_query(), _match_file(), _media_id() (+25 more)

### Community 12 - "Community 12"
Cohesion: 0.24
Nodes (12): DeviceInfo, discover(), _discover_kind(), _friendly_name(), _lan_sources(), SSDP source addresses for broadcast-capable IPv4 interfaces.      Excludes loopb, Pull <friendlyName> from the device description XML. None on any failure., SSDP scan. Returns (servers, renderers). Names are filled in on connect. (+4 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (26): Decode an image into a colored Rich renderable.      Each character cell is a '▀, to_ansi(), call(), handoff(), media_ids(), pick_renderer(), ClientSession, Talking to VuIO over its MCP endpoint, and handing playback over to it.  VuIO se (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.33
Nodes (5): dlna-tui, Keys, Notes, Running, Settings

### Community 15 - "Community 15"
Cohesion: 0.14
Nodes (8): get_display(), PixelDisplay, Pixel-Display Integration für dlna-tui.  Unterstützt kleine OLED-Displays (z.B., Ob ein funktionierendes Display zur Verfügung steht., Holt die globale Display-Instanz., Abstraktion für kleines Pixel-Display.          Unterstützt grundlegende Textaus, Zeigt aktuelle Wiedergabe.                  Args:             title: Track-Titel, Zeigt kleines Cover (muss Device-Größe haben).                  Args:

## Knowledge Gaps
- **29 isolated node(s):** `Text`, `Running`, `Keys`, `Settings`, `Notes` (+24 more)
  These have ≤1 connection - possible missing edges or undocumented components.
- **1 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 12`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.263) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 4` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 7`, `Community 13`?**
  _High betweenness centrality (0.156) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 13`?**
  _High betweenness centrality (0.082) - this node is a cross-community bridge._
- **Are the 10 inferred relationships involving `DlnaApp` (e.g. with `FakeRenderer` and `_Renderer`) actually correct?**
  _`DlnaApp` has 10 INFERRED edges - model-reasoned connections that need verification._
- **Are the 26 inferred relationships involving `Track` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Track` has 26 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Queue` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Queue` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Renderer` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Renderer` has 16 INFERRED edges - model-reasoned connections that need verification._