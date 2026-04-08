# lrcget

Python library and CLI for [lrclib.net](https://lrclib.net) — a free, open database of time-synced (LRC) and plain-text lyrics.

## Installation

```bash
pip install git+https://github.com/dobs/lrcget
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add git+https://github.com/dobs/lrcget
```

To run the CLI without installing it into your project, use `uvx`:

```bash
uvx --from git+https://github.com/dobs/lrcget lrcget search "bohemian rhapsody"
```

Or from source:

```bash
git clone https://github.com/dobs/lrcget
cd lrcget

# with uv (recommended)
uv sync
uv run lrcget --help

# with pip
python -m venv .venv && source .venv/bin/activate
pip install -e .
```

Requires Python 3.9+.

---

## CLI

### `search` — search the database

```
lrcget search [QUERY] [-t TRACK] [-a ARTIST] [-A ALBUM] [--synced] [--plain]
```

`QUERY` is a free-text search term. Use the field flags for more targeted results. At least one of `QUERY` or `--track` must be provided.

Adding `--synced` or `--plain` prints the lyrics of the first result immediately instead of showing the results table.

**Examples**

```bash
# Free-text search, shows results table
lrcget search "bohemian rhapsody"

# Field-specific search
lrcget search --artist "Rick Astley" --track "Never Gonna Give You Up"

# Search and immediately print synced lyrics for the top result
lrcget search "never gonna give you up" --synced
```

**Output**

```
ID        Track                           Artist                     Album                      Duration
--------  ------------------------------  -------------------------  -------------------------  --------
4442751   Never Gonna Give You Up         Rick Astley                Never Gonna Give You Up    214s
9627540   Never Gonna Give You Up         Rick Astley                Never Gonna Give You Up    211s
...
```

---

### `get` — fetch lyrics by track metadata

```
lrcget get -t TRACK -a ARTIST -A ALBUM -d DURATION [--synced] [--plain]
```

All four flags are required and must match the entry in lrclib exactly (as returned by `search`).

Without `--synced` or `--plain`, the command prints synced lyrics if available, falling back to plain text.

**Example**

```bash
lrcget get \
  -t "Never Gonna Give You Up" \
  -a "Rick Astley" \
  -A "Never Gonna Give You Up" \
  -d 214 \
  --synced
```

**Output**

```
ID:       4442751
Track:    Never Gonna Give You Up
Artist:   Rick Astley
Album:    Never Gonna Give You Up
Duration: 214.0s

[00:19.67] We're no strangers to love
[00:23.56] You know the rules and so do I (do I)
...
```

---

### `get-id` — fetch lyrics by lrclib ID

```
lrcget get-id ID [--synced] [--plain]
```

Use the numeric ID shown in the `search` results table.

**Example**

```bash
lrcget get-id 4442751 --plain
```

---

### `publish` — contribute lyrics

```
lrcget publish -t TRACK -a ARTIST -A ALBUM -d DURATION \
               [--plain-lyrics FILE] [--synced-lyrics FILE]
```

At least one of `--plain-lyrics` or `--synced-lyrics` must be provided. The command automatically requests and solves the proof-of-work challenge required by lrclib (takes a few seconds).

Synced lyrics must use LRC bracket notation, e.g. `[00:27.93] Lyrics here`.

**Example**

```bash
lrcget publish \
  -t "My Song" \
  -a "My Artist" \
  -A "My Album" \
  -d 240 \
  --synced-lyrics lyrics.lrc
```

---

## Library

```python
from lrcget import LrclibClient

with LrclibClient() as client:

    # Search
    results = client.search("bohemian rhapsody", artist_name="Queen")
    for r in results:
        print(r.id, r.track_name, r.artist_name)

    # Fetch by metadata
    result = client.get(
        track_name="Bohemian Rhapsody",
        artist_name="Queen",
        album_name="A Night at the Opera",
        duration=354,
    )
    print(result.synced_lyrics)

    # Fetch by ID
    result = client.get_by_id(4442751)
    print(result.plain_lyrics)

    # Publish
    client.publish(
        track_name="My Song",
        artist_name="My Artist",
        album_name="My Album",
        duration=240,
        plain_lyrics="Verse one\nVerse two\n",
        synced_lyrics="[00:01.00] Verse one\n[00:05.00] Verse two\n",
    )
```

### `LyricsResult` fields

| Field | Type | Description |
|---|---|---|
| `id` | `int` | lrclib numeric ID |
| `track_name` | `str` | Song title |
| `artist_name` | `str` | Artist name |
| `album_name` | `str` | Album name |
| `duration` | `float` | Duration in seconds |
| `instrumental` | `bool` | True if the track has no lyrics |
| `plain_lyrics` | `str \| None` | Unsynced lyrics text |
| `synced_lyrics` | `str \| None` | LRC time-tagged lyrics |

### Exceptions

| Exception | When raised |
|---|---|
| `LrclibNotFound` | The requested track or ID does not exist (HTTP 404) |
| `LrclibError` | Any other API error; has `.status_code` and a message |

---

## Dependencies

- [httpx](https://www.python-httpx.org/) — HTTP client
- [click](https://click.palletsprojects.com/) — CLI framework
