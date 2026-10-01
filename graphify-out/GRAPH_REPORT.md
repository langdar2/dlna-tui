# Graph Report - dlna TerminalClient  (2026-10-01)

## Corpus Check
- 18 files · ~7,039 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 187 nodes · 429 edges · 12 communities
- Extraction: 74% EXTRACTED · 26% INFERRED · 0% AMBIGUOUS · INFERRED: 112 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `f3230cb1`
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
1. `DlnaApp` - 37 edges
2. `Track` - 34 edges
3. `Renderer` - 34 edges
4. `Queue` - 24 edges
5. `MusicServer` - 24 edges
6. `ComposeResult` - 24 edges
7. `Store` - 23 edges
8. `Container` - 22 edges
9. `NowPlaying` - 18 edges
10. `DeviceScreen` - 16 edges

## Surprising Connections (you probably didn't know these)
- `DeviceScreen` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `DlnaApp` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `SearchScreen` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `TrackInfoScreen` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `FakeProfile` --uses--> `Track`  [INFERRED]
  tests/test_renderer.py → dlna/models.py

## Import Cycles
- None detected.

## Communities (12 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.16
Nodes (15): _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _media_info(), Queue, DIDL-Lite XML -> list of our models (Descriptors dropped)., Summarise the first <res>: file type, sample rate, depth, channels, size. (+7 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (4): ModalScreen, DeviceScreen, SearchScreen, TrackInfoScreen

### Community 2 - "Community 2"
Cohesion: 0.12
Nodes (3): App, ListItem, DlnaApp

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (8): Track, Renderer, RendererState, FakeProfile, test_play_sets_uri(), test_safe_call_swallows_errors_and_reports(), test_state_snapshot(), _fmt()

### Community 4 - "Community 4"
Cohesion: 0.16
Nodes (16): DeviceInfo, Decode an image and render it as greyscale ASCII art.      Height is halved beca, to_ascii(), build_device(), discover(), _discover_kind(), _friendly_name(), _lan_sources() (+8 more)

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
Cohesion: 0.19
Nodes (20): ComposeResult, Container, Container, Already-parsed didl_lite objects -> our models (Descriptors dropped)., to_models(), Track, MusicServer, Track (+12 more)

## Knowledge Gaps
- **24 isolated node(s):** `Task 0: Projekt-Setup`, `Task 1: Modelle + DIDL-Adapter`, `Task 2: Queue-Logik (rein)`, `Task 3: Store (Favoriten + Session)`, `Task 4: Discovery` (+19 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.185) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 8`, `Community 1`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.144) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 8` to `Community 0`, `Community 1`, `Community 2`, `Community 3`, `Community 4`?**
  _High betweenness centrality (0.126) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DlnaApp` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`DlnaApp` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `Track` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`Track` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Renderer` (e.g. with `ComposeResult` and `Track`) actually correct?**
  _`Renderer` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Queue` (e.g. with `ComposeResult` and `NodeExpanded`) actually correct?**
  _`Queue` has 12 INFERRED edges - model-reasoned connections that need verification._