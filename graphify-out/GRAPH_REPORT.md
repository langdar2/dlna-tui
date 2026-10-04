# Graph Report - dlna TerminalClient  (2026-10-04)

## Corpus Check
- 20 files · ~9,984 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 245 nodes · 564 edges · 12 communities
- Extraction: 80% EXTRACTED · 20% INFERRED · 0% AMBIGUOUS · INFERRED: 114 edges (avg confidence: 0.5)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `0cc17eb1`
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
1. `DlnaApp` - 54 edges
2. `Track` - 42 edges
3. `Renderer` - 34 edges
4. `Queue` - 29 edges
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
Cohesion: 0.13
Nodes (20): _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _is_audio(), _media_info(), Queue, Forget what's queued behind the current track, keeping it playing.         Switc (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (23): Changed, ComposeResult, Container, Container, Already-parsed didl_lite objects -> our models (Descriptors dropped).      Conta, to_models(), Track, MusicServer (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.08
Nodes (8): App, ListItem, DlnaApp, The tree node whose children are 'the current folder' for filtering., Move focus from the filter box onto the first result so it's playable., What to base radio on: the cursor track, else what's playing., Move the ▶ marker to the playing track. Touches only the two rows         that c, Fetch similar tracks for seed and append to the queue, skipping ones         alr

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (8): Track, Renderer, RendererState, FakeProfile, test_play_sets_uri(), test_safe_call_swallows_errors_and_reports(), test_state_snapshot(), _fmt()

### Community 4 - "Community 4"
Cohesion: 0.11
Nodes (23): DeviceInfo, Decode an image into a colored Rich renderable.      Each character cell is a '▀, to_ansi(), build_device(), discover(), _discover_kind(), _friendly_name(), _lan_sources() (+15 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): Architektur, Datenfluss, discovery.py, DLNA TUI — Design, Fehlerbehandlung, Keybindings, Komponenten, models.py (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (13): Bekannte Risiken (am Gerät verifizieren), Dateistruktur, DLNA TUI Implementation Plan, Self-Review (durchgeführt), Task 0: Projekt-Setup, Task 1: Modelle + DIDL-Adapter, Task 2: Queue-Logik (rein), Task 3: Store (Favoriten + Session) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.15
Nodes (28): ClientSession, _basename(), _best_match(), _common_tail(), _crate_query(), _match_file(), _media_id(), _preview() (+20 more)

### Community 8 - "Community 8"
Cohesion: 0.43
Nodes (5): _app(), A radio fetch takes a second or two. If the user picks a new song while     it r, _recs(), test_radio_results_dropped_when_user_picks_another_track(), test_radio_results_kept_when_queue_untouched()

## Knowledge Gaps
- **25 isolated node(s):** `Text`, `Task 0: Projekt-Setup`, `Task 1: Modelle + DIDL-Adapter`, `Task 2: Queue-Logik (rein)`, `Task 3: Store (Favoriten + Session)` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 8`?**
  _High betweenness centrality (0.256) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`?**
  _High betweenness centrality (0.179) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`?**
  _High betweenness centrality (0.115) - this node is a cross-community bridge._
- **Are the 8 inferred relationships involving `DlnaApp` (e.g. with `ComposeResult` and `Container`) actually correct?**
  _`DlnaApp` has 8 INFERRED edges - model-reasoned connections that need verification._
- **Are the 21 inferred relationships involving `Track` (e.g. with `Changed` and `ClientSession`) actually correct?**
  _`Track` has 21 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Renderer` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Renderer` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 12 inferred relationships involving `Queue` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Queue` has 12 INFERRED edges - model-reasoned connections that need verification._