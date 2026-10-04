# Graph Report - dlna TerminalClient  (2026-10-04)

## Corpus Check
- 19 files · ~8,890 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 226 nodes · 514 edges · 12 communities
- Extraction: 78% EXTRACTED · 22% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a852ce4c`
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

## God Nodes (most connected - your core abstractions)
1. `DlnaApp` - 49 edges
2. `Track` - 38 edges
3. `Renderer` - 34 edges
4. `Queue` - 24 edges
5. `Store` - 23 edges
6. `ComposeResult` - 23 edges
7. `Container` - 22 edges
8. `MusicServer` - 22 edges
9. `NowPlaying` - 18 edges
10. `DeviceScreen` - 16 edges

## Surprising Connections (you probably didn't know these)
- `DlnaApp` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `FakeProfile` --uses--> `Track`  [INFERRED]
  tests/test_renderer.py → dlna/models.py
- `DlnaApp` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py
- `Changed` --uses--> `Queue`  [INFERRED]
  ui/app.py → dlna/models.py
- `ComposeResult` --uses--> `Queue`  [INFERRED]
  ui/app.py → dlna/models.py

## Import Cycles
- None detected.

## Communities (12 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.15
Nodes (19): _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _is_audio(), _media_info(), Queue, Already-parsed didl_lite objects -> our models (Descriptors dropped).      Conta (+11 more)

### Community 1 - "Community 1"
Cohesion: 0.10
Nodes (26): Changed, ComposeResult, Container, Decode an image into a colored Rich renderable.      Each character cell is a '▀, to_ansi(), Container, Track, RendererState (+18 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (7): App, ListItem, DlnaApp, The tree node whose children are 'the current folder' for filtering., Move focus from the filter box onto the first result so it's playable., What to base radio on: the cursor track, else what's playing., Fetch similar tracks for seed and append to the queue, skipping ones         alr

### Community 3 - "Community 3"
Cohesion: 0.14
Nodes (6): Track, Renderer, FakeProfile, test_play_sets_uri(), test_safe_call_swallows_errors_and_reports(), test_state_snapshot()

### Community 4 - "Community 4"
Cohesion: 0.21
Nodes (14): DeviceInfo, build_device(), discover(), _discover_kind(), _friendly_name(), _lan_sources(), SSDP source addresses for broadcast-capable IPv4 interfaces.      Excludes loopb, Pull <friendlyName> from the device description XML. None on any failure. (+6 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): Architektur, Datenfluss, discovery.py, DLNA TUI — Design, Fehlerbehandlung, Keybindings, Komponenten, models.py (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (13): Bekannte Risiken (am Gerät verifizieren), Dateistruktur, DLNA TUI Implementation Plan, Self-Review (durchgeführt), Task 0: Projekt-Setup, Task 1: Modelle + DIDL-Adapter, Task 2: Queue-Logik (rein), Task 3: Store (Favoriten + Session) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.17
Nodes (24): ClientSession, _basename(), _crate_query(), _match_file(), _media_id(), _preview(), Track, radio_tracks() (+16 more)

### Community 12 - "Community 12"
Cohesion: 0.31
Nodes (6): default_path(), Store, Path, test_corrupt_file_is_ignored(), test_missing_file(), test_roundtrip()

## Knowledge Gaps
- **25 isolated node(s):** `Text`, `Task 0: Projekt-Setup`, `Task 1: Modelle + DIDL-Adapter`, `Task 2: Queue-Logik (rein)`, `Task 3: Store (Favoriten + Session)` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 12`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 7`?**
  _High betweenness centrality (0.170) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 1`, `Community 2`?**
  _High betweenness centrality (0.123) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DlnaApp` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`DlnaApp` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Track` (e.g. with `Changed` and `ClientSession`) actually correct?**
  _`Track` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Renderer` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Renderer` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Queue` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Queue` has 12 INFERRED edges - model-reasoned connections that need verification._