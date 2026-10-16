# dlna-tui

Full-screen terminal player for the music on a DLNA server, with
recommendations from CrateMind2.

## Running

```bash
pip install -r requirements.txt
python3 .
```

It picks up the server and renderer used last time (remembered in
`~/.config/dlna-tui/store.json`); press `d` to choose others.

## Keys

| Key | What it does |
|-----|--------------|
| `space` | Play / pause |
| `n` / `p` | Next / previous track |
| `←` / `→` | Seek back / forward |
| `+` / `-` | Volume |
| `a` | Add the selected track to the queue |
| `/` | Filter the tree |
| `c` | Radio: replace the rest of the queue with tracks CrateMind finds similar, and keep going when it runs out |
| `f` | Favourite ★ (press again to clear) |
| `b` | Never play ✗ (press again to clear) |
| `x` | Hand the queue to VuIO, so it keeps playing after you quit |
| `i` | Track info |
| `d` | Pick server / renderer |
| `?` | Help: every key with an explanation |
| `q` | Quit |

Ratings and plays go to CrateMind, where they steer how playlists are built:
a favourite ranks like the best-liked music in the library, a thumbs-down is
dropped from playlists entirely (but can still seed radio). A track counts as
played after 30 seconds; leaving earlier counts as a skip. Nothing is recorded
while CrateMind is unreachable, and nothing breaks either.

## Settings

All optional. The defaults point at the host these services run on;
set them if yours live elsewhere.

| Variable | Default | Meaning |
|----------|---------|---------|
| `CRATE_URL` | `http://minime-3.local:8008` | CrateMind2 |
| `VUIO_URL` | `http://minime-3.local:8080` | VuIO media server |
| `RADIO_LIMIT` | `10` | Tracks fetched per radio batch |
| `RADIO_FRESH_SHARE` | `0.15` | Share of a radio batch reserved for recently imported music |

## Notes

- `x` hands off over Chromecast when the renderer offers it, because VuIO
  plays a DLNA playlist out of order (measured: a five-track list played
  0,4,3,4,2,3,4). Casting the same playlist to the same device over
  Chromecast plays it in order.
- Tests: `python3 -m pytest`
