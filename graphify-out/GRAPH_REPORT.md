# Graph Report - dlna TerminalClient  (2026-10-01)

## Corpus Check
- 17 files · ~6,375 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 170 nodes · 382 edges · 12 communities
- Extraction: 75% EXTRACTED · 25% INFERRED · 0% AMBIGUOUS · INFERRED: 95 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `a582770e`
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
- [[_COMMUNITY_Community 8|Community 8]]

## God Nodes (most connected - your core abstractions)
1. `DlnaApp` - 35 edges
2. `Track` - 32 edges
3. `Renderer` - 31 edges
4. `Queue` - 22 edges
5. `MusicServer` - 22 edges
6. `Store` - 21 edges
7. `ComposeResult` - 21 edges
8. `Container` - 20 edges
9. `DeviceScreen` - 16 edges
10. `NowPlaying` - 16 edges

## Surprising Connections (you probably didn't know these)
- `ComposeResult` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `NodeExpanded` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `Selected` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `Submitted` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `DeviceItem` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py

## Import Cycles
- None detected.

## Communities (12 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (19): Container, Container, _first_res_duration(), _first_res_uri(), from_didl(), Queue, Already-parsed didl_lite objects -> our models (Descriptors dropped)., DIDL-Lite XML -> list of our models (Descriptors dropped). (+11 more)

### Community 1 - "Community 1"
Cohesion: 0.15
Nodes (10): ComposeResult, RendererState, ModalScreen, Static, Submitted, DeviceItem, DeviceScreen, SearchScreen (+2 more)

### Community 2 - "Community 2"
Cohesion: 0.11
Nodes (5): App, ListItem, NodeExpanded, Selected, DlnaApp

### Community 3 - "Community 3"
Cohesion: 0.15
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
Cohesion: 0.31
Nodes (6): default_path(), Store, Path, test_corrupt_file_is_ignored(), test_missing_file(), test_roundtrip()

### Community 8 - "Community 8"
Cohesion: 0.43
Nodes (4): MusicServer, FakeProfile, test_browse_returns_models(), test_search_returns_models()

## Knowledge Gaps
- **24 isolated node(s):** `Task 0: Projekt-Setup`, `Task 1: Modelle + DIDL-Adapter`, `Task 2: Queue-Logik (rein)`, `Task 3: Store (Favoriten + Session)`, `Task 4: Discovery` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.187) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`?**
  _High betweenness centrality (0.143) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 0` to `Community 8`, `Community 1`, `Community 2`, `Community 3`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DlnaApp` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`DlnaApp` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 17 inferred relationships involving `Track` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`Track` has 17 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Renderer` (e.g. with `ComposeResult` and `Track`) actually correct?**
  _`Renderer` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 10 inferred relationships involving `Queue` (e.g. with `ComposeResult` and `NodeExpanded`) actually correct?**
  _`Queue` has 10 INFERRED edges - model-reasoned connections that need verification._