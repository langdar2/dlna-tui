# Graph Report - dlna TerminalClient  (2026-10-09)

## Corpus Check
- 22 files · ~12,288 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 292 nodes · 690 edges · 13 communities
- Extraction: 83% EXTRACTED · 17% INFERRED · 0% AMBIGUOUS · INFERRED: 119 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `6e1bcd98`
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

## God Nodes (most connected - your core abstractions)
1. `DlnaApp` - 64 edges
2. `Track` - 46 edges
3. `Renderer` - 34 edges
4. `Queue` - 33 edges
5. `Store` - 27 edges
6. `ComposeResult` - 23 edges
7. `Container` - 22 edges
8. `MusicServer` - 22 edges
9. `NowPlaying` - 18 edges
10. `radio_tracks()` - 17 edges

## Surprising Connections (you probably didn't know these)
- `DlnaApp` --uses--> `Container`  [INFERRED]
  ui/app.py → dlna/models.py
- `FakeRenderer` --uses--> `Track`  [INFERRED]
  tests/test_playcount.py → dlna/models.py
- `FakeProfile` --uses--> `Track`  [INFERRED]
  tests/test_renderer.py → dlna/models.py
- `DlnaApp` --uses--> `Track`  [INFERRED]
  ui/app.py → dlna/models.py
- `Changed` --uses--> `Queue`  [INFERRED]
  ui/app.py → dlna/models.py

## Import Cycles
- None detected.

## Communities (13 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.13
Nodes (20): _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _is_audio(), _media_info(), Queue, Forget what's queued behind the current track, keeping it playing.         Switc (+12 more)

### Community 1 - "Community 1"
Cohesion: 0.12
Nodes (23): Changed, ComposeResult, Container, Container, Already-parsed didl_lite objects -> our models (Descriptors dropped).      Conta, to_models(), Track, MusicServer (+15 more)

### Community 2 - "Community 2"
Cohesion: 0.07
Nodes (12): App, ListItem, DlnaApp, Count listening time and report a play once it passes the threshold.          Dr, Restart the play timer when the current track changed, and report         the on, The tree node whose children are 'the current folder' for filtering., Move focus from the filter box onto the first result so it's playable., What to base radio on: the cursor track, else what's playing. (+4 more)

### Community 3 - "Community 3"
Cohesion: 0.15
Nodes (6): Track, Renderer, FakeProfile, test_play_sets_uri(), test_safe_call_swallows_errors_and_reports(), test_state_snapshot()

### Community 4 - "Community 4"
Cohesion: 0.14
Nodes (17): RendererState, _app(), FakeRenderer, _listen(), test_moving_on_after_a_full_listen_is_not_a_skip(), test_paused_and_handed_off_playback_does_not_accrue(), test_play_counts_once_past_the_threshold(), test_replaying_the_same_track_counts_again() (+9 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): Architektur, Datenfluss, discovery.py, DLNA TUI — Design, Fehlerbehandlung, Keybindings, Komponenten, models.py (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (13): Bekannte Risiken (am Gerät verifizieren), Dateistruktur, DLNA TUI Implementation Plan, Self-Review (durchgeführt), Task 0: Projekt-Setup, Task 1: Modelle + DIDL-Adapter, Task 2: Queue-Logik (rein), Task 3: Store (Favoriten + Session) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.14
Nodes (33): _basename(), _best_match(), _common_tail(), count_play(), _crate_path_of(), _crate_query(), _match_file(), _media_id() (+25 more)

### Community 12 - "Community 12"
Cohesion: 0.09
Nodes (26): DeviceInfo, Decode an image into a colored Rich renderable.      Each character cell is a '▀, to_ansi(), build_device(), discover(), _discover_kind(), _friendly_name(), _lan_sources() (+18 more)

### Community 13 - "Community 13"
Cohesion: 0.24
Nodes (12): call(), handoff(), media_ids(), pick_renderer(), ClientSession, Talking to VuIO over its MCP endpoint, and handing playback over to it.  VuIO se, Invoke one VuIO MCP tool over HTTP and return its parsed result., Queue as VuIO file ids, or None if any track isn't one of VuIO's.      A DLNA ob (+4 more)

## Knowledge Gaps
- **25 isolated node(s):** `Text`, `Task 0: Projekt-Setup`, `Task 1: Modelle + DIDL-Adapter`, `Task 2: Queue-Logik (rein)`, `Task 3: Store (Favoriten + Session)` (+20 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 12`, `Community 13`?**
  _High betweenness centrality (0.278) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 1` to `Community 0`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 12`?**
  _High betweenness centrality (0.165) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 1`, `Community 2`, `Community 4`, `Community 12`?**
  _High betweenness centrality (0.100) - this node is a cross-community bridge._
- **Are the 9 inferred relationships involving `DlnaApp` (e.g. with `FakeRenderer` and `ComposeResult`) actually correct?**
  _`DlnaApp` has 9 INFERRED edges - model-reasoned connections that need verification._
- **Are the 22 inferred relationships involving `Track` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Track` has 22 INFERRED edges - model-reasoned connections that need verification._
- **Are the 14 inferred relationships involving `Renderer` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Renderer` has 14 INFERRED edges - model-reasoned connections that need verification._
- **Are the 13 inferred relationships involving `Queue` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Queue` has 13 INFERRED edges - model-reasoned connections that need verification._