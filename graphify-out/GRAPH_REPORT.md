# Graph Report - dlna TerminalClient  (2026-10-16)

## Corpus Check
- 30 files · ~17,897 words
- Verdict: corpus is large enough that graph structure adds value.

## Summary
- 440 nodes · 1029 edges · 16 communities
- Extraction: 85% EXTRACTED · 15% INFERRED · 0% AMBIGUOUS · INFERRED: 151 edges (avg confidence: 0.51)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `4ed317b3`
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
- [[_COMMUNITY_Community 12|Community 12]]
- [[_COMMUNITY_Community 13|Community 13]]
- [[_COMMUNITY_Community 14|Community 14]]
- [[_COMMUNITY_Community 15|Community 15]]

## God Nodes (most connected - your core abstractions)
1. `DlnaApp` - 81 edges
2. `Track` - 65 edges
3. `Queue` - 52 edges
4. `Renderer` - 36 edges
5. `Store` - 29 edges
6. `ComposeResult` - 26 edges
7. `Container` - 24 edges
8. `MusicServer` - 24 edges
9. `RendererState` - 21 edges
10. `NowPlaying` - 20 edges

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

## Communities (16 total, 0 thin omitted)

### Community 0 - "Community 0"
Cohesion: 0.07
Nodes (43): Container, _first_res(), _first_res_duration(), _first_res_uri(), from_didl(), _is_audio(), _media_info(), Queue (+35 more)

### Community 1 - "Community 1"
Cohesion: 0.09
Nodes (29): Changed, ComposeResult, Container, MusicServer, default_path(), Path, Store, ModalScreen (+21 more)

### Community 2 - "Community 2"
Cohesion: 0.05
Nodes (21): App, ListItem, test_threshold_follows_the_scrobble_rule(), DlnaApp, _hms_seconds(), play_threshold(), Hand the playing track to the LED display without waiting for it.          Bluet, Count listening time and report a play once it passes the threshold.          Dr (+13 more)

### Community 3 - "Community 3"
Cohesion: 0.12
Nodes (8): Track, Renderer, RendererState, FakeProfile, test_play_sets_uri(), test_safe_call_swallows_errors_and_reports(), test_state_snapshot(), _fmt()

### Community 4 - "Community 4"
Cohesion: 0.35
Nodes (10): _app(), FakeRenderer, _listen(), test_a_short_interlude_is_neither_a_play_nor_a_skip(), test_long_track_needs_half_its_length(), test_moving_on_after_a_full_listen_is_not_a_skip(), test_paused_and_handed_off_playback_does_not_accrue(), test_play_counts_once_past_the_threshold() (+2 more)

### Community 5 - "Community 5"
Cohesion: 0.12
Nodes (15): Architektur, Datenfluss, discovery.py, DLNA TUI — Design, Fehlerbehandlung, Keybindings, Komponenten, models.py (+7 more)

### Community 6 - "Community 6"
Cohesion: 0.14
Nodes (13): Bekannte Risiken (am Gerät verifizieren), Dateistruktur, DLNA TUI Implementation Plan, Self-Review (durchgeführt), Task 0: Projekt-Setup, Task 1: Modelle + DIDL-Adapter, Task 2: Queue-Logik (rein), Task 3: Store (Favoriten + Session) (+5 more)

### Community 7 - "Community 7"
Cohesion: 0.09
Nodes (44): _basename(), _best_match(), _common_tail(), count_play(), _crate_path_of(), _crate_query(), _match_file(), _media_id() (+36 more)

### Community 8 - "Community 8"
Cohesion: 0.19
Nodes (14): _App, _box(), _flac_moov(), _mvhd(), _R, The point of the lookup: the threshold stops falling back to 30 s., The real case: mvhd is 0 because the file is fragmented, but the FLAC     STREAM, test_a_failed_lookup_is_not_retried_every_second() (+6 more)

### Community 12 - "Community 12"
Cohesion: 0.21
Nodes (14): DeviceInfo, build_device(), discover(), _discover_kind(), _friendly_name(), _lan_sources(), SSDP source addresses for broadcast-capable IPv4 interfaces.      Excludes loopb, Pull <friendlyName> from the device description XML. None on any failure. (+6 more)

### Community 13 - "Community 13"
Cohesion: 0.09
Nodes (26): Decode an image into a colored Rich renderable.      Each character cell is a '▀, to_ansi(), _flac_seconds(), _header_time(), mp4_seconds(), _range(), Track length read from the file itself, for when the server does not know it.  V, (type, offset, size) of the MP4 boxes at the start of `buf`. (+18 more)

### Community 14 - "Community 14"
Cohesion: 0.29
Nodes (6): dlna-tui, Keys, LED display (optional), Notes, Running, Settings

### Community 15 - "Community 15"
Cohesion: 0.07
Nodes (40): cover_frame(), DisplayState, _font(), get_display(), import_idotmatrix(), PixelDisplay, progress_columns(), iDotMatrix 32x32 LED display: cover art, progress bar, scrolling title.  Optiona (+32 more)

## Knowledge Gaps
- **31 isolated node(s):** `Text`, `ImageFont`, `Running`, `Keys`, `Settings` (+26 more)
  These have ≤1 connection - possible missing edges or undocumented components.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `DlnaApp` connect `Community 2` to `Community 0`, `Community 1`, `Community 3`, `Community 4`, `Community 8`, `Community 12`, `Community 13`, `Community 15`?**
  _High betweenness centrality (0.245) - this node is a cross-community bridge._
- **Why does `Track` connect `Community 0` to `Community 1`, `Community 2`, `Community 3`, `Community 4`, `Community 7`, `Community 8`, `Community 13`?**
  _High betweenness centrality (0.140) - this node is a cross-community bridge._
- **Why does `Renderer` connect `Community 3` to `Community 0`, `Community 1`, `Community 2`, `Community 13`?**
  _High betweenness centrality (0.069) - this node is a cross-community bridge._
- **Are the 12 inferred relationships involving `DlnaApp` (e.g. with `_App` and `_R`) actually correct?**
  _`DlnaApp` has 12 INFERRED edges - model-reasoned connections that need verification._
- **Are the 28 inferred relationships involving `Track` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Track` has 28 INFERRED edges - model-reasoned connections that need verification._
- **Are the 19 inferred relationships involving `Queue` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Queue` has 19 INFERRED edges - model-reasoned connections that need verification._
- **Are the 16 inferred relationships involving `Renderer` (e.g. with `Changed` and `ComposeResult`) actually correct?**
  _`Renderer` has 16 INFERRED edges - model-reasoned connections that need verification._