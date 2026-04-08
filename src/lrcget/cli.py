"""lrcget – command-line interface for lrclib.net."""
from __future__ import annotations

import sys

import click

from .client import LrclibClient, LrclibError, LrclibNotFound
from .models import LyricsResult


def _make_client() -> LrclibClient:
    return LrclibClient()


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
@click.version_option(package_name="lrcget")
def cli() -> None:
    """Search and retrieve synced lyrics from lrclib.net."""


# ---------------------------------------------------------------------------
# search
# ---------------------------------------------------------------------------

@cli.command("search")
@click.argument("query", required=False)
@click.option("-t", "--track", "track_name", help="Track / song name.")
@click.option("-a", "--artist", "artist_name", help="Artist name.")
@click.option("-A", "--album", "album_name", help="Album name.")
@click.option("--plain", is_flag=True, help="Show plain lyrics for the first result.")
@click.option("--synced", is_flag=True, help="Show synced lyrics for the first result.")
def search_cmd(
    query: str | None,
    track_name: str | None,
    artist_name: str | None,
    album_name: str | None,
    plain: bool,
    synced: bool,
) -> None:
    """Search for lyrics.

    QUERY is a general free-text search term.  Use --track / --artist /
    --album for field-specific searches.

    \b
    Examples:
      lrcget search "never gonna give you up"
      lrcget search --artist "Rick Astley" --track "Never Gonna Give You Up"
      lrcget search "bohemian rhapsody" --synced
    """
    if not query and not track_name:
        raise click.UsageError("Provide QUERY and/or --track.")

    with _make_client() as client:
        try:
            results = client.search(
                query=query,
                track_name=track_name,
                artist_name=artist_name,
                album_name=album_name,
            )
        except LrclibError as exc:
            _die(str(exc))

    if not results:
        click.echo("No results found.")
        return

    if plain or synced:
        _print_lyrics(results[0], plain=plain, synced=synced)
        return

    _print_table(results)


# ---------------------------------------------------------------------------
# get
# ---------------------------------------------------------------------------

@cli.command("get")
@click.option("-t", "--track", "track_name", required=True, help="Track name.")
@click.option("-a", "--artist", "artist_name", required=True, help="Artist name.")
@click.option("-A", "--album", "album_name", required=True, help="Album name.")
@click.option("-d", "--duration", required=True, type=float, help="Duration in seconds.")
@click.option("--plain", is_flag=True, help="Print plain lyrics.")
@click.option("--synced", is_flag=True, help="Print synced (LRC) lyrics.")
def get_cmd(
    track_name: str,
    artist_name: str,
    album_name: str,
    duration: float,
    plain: bool,
    synced: bool,
) -> None:
    """Get lyrics by track metadata.

    \b
    Example:
      lrcget get -t "Never Gonna Give You Up" -a "Rick Astley" \\
                 -A "Whenever You Need Somebody" -d 213 --synced
    """
    with _make_client() as client:
        try:
            result = client.get(track_name, artist_name, album_name, duration)
        except LrclibNotFound:
            _die("No lyrics found for the given track.")
        except LrclibError as exc:
            _die(str(exc))

    _print_lyrics(result, plain=plain, synced=synced, header=True)


# ---------------------------------------------------------------------------
# get-id
# ---------------------------------------------------------------------------

@cli.command("get-id")
@click.argument("lyrics_id", type=int, metavar="ID")
@click.option("--plain", is_flag=True, help="Print plain lyrics.")
@click.option("--synced", is_flag=True, help="Print synced (LRC) lyrics.")
def get_id_cmd(lyrics_id: int, plain: bool, synced: bool) -> None:
    """Get lyrics by lrclib numeric ID.

    \b
    Example:
      lrcget get-id 3396226 --synced
    """
    with _make_client() as client:
        try:
            result = client.get_by_id(lyrics_id)
        except LrclibNotFound:
            _die(f"No lyrics found with ID {lyrics_id}.")
        except LrclibError as exc:
            _die(str(exc))

    _print_lyrics(result, plain=plain, synced=synced, header=True)


# ---------------------------------------------------------------------------
# publish
# ---------------------------------------------------------------------------

@cli.command("publish")
@click.option("-t", "--track", "track_name", required=True, help="Track name.")
@click.option("-a", "--artist", "artist_name", required=True, help="Artist name.")
@click.option("-A", "--album", "album_name", required=True, help="Album name.")
@click.option("-d", "--duration", required=True, type=float, help="Duration in seconds.")
@click.option(
    "--plain-lyrics",
    type=click.Path(exists=True, readable=True),
    default=None,
    help="Path to plain lyrics text file.",
)
@click.option(
    "--synced-lyrics",
    type=click.Path(exists=True, readable=True),
    default=None,
    help="Path to synced lyrics (.lrc) file.",
)
def publish_cmd(
    track_name: str,
    artist_name: str,
    album_name: str,
    duration: float,
    plain_lyrics: str | None,
    synced_lyrics: str | None,
) -> None:
    """Publish lyrics to lrclib.net.

    At least one of --plain-lyrics or --synced-lyrics must be provided.
    The proof-of-work challenge is solved automatically (takes a few seconds).

    \b
    Example:
      lrcget publish -t "My Song" -a "My Artist" -A "My Album" -d 240 \\
                     --synced-lyrics lyrics.lrc
    """
    if not plain_lyrics and not synced_lyrics:
        raise click.UsageError("Provide --plain-lyrics and/or --synced-lyrics.")

    plain_text: str | None = None
    synced_text: str | None = None

    if plain_lyrics:
        with open(plain_lyrics, encoding="utf-8") as fh:
            plain_text = fh.read()
    if synced_lyrics:
        with open(synced_lyrics, encoding="utf-8") as fh:
            synced_text = fh.read()

    click.echo("Solving proof-of-work challenge…", err=True)

    with _make_client() as client:
        try:
            client.publish(
                track_name=track_name,
                artist_name=artist_name,
                album_name=album_name,
                duration=duration,
                plain_lyrics=plain_text,
                synced_lyrics=synced_text,
            )
        except LrclibError as exc:
            _die(str(exc))

    click.echo("Lyrics published successfully.")


# ---------------------------------------------------------------------------
# Output helpers
# ---------------------------------------------------------------------------

_COL_WIDTHS = (8, 30, 25, 25, 8)
_HEADERS = ("ID", "Track", "Artist", "Album", "Duration")


def _print_table(results: list[LyricsResult]) -> None:
    fmt = "  ".join(f"{{:<{w}}}" for w in _COL_WIDTHS)
    click.echo(fmt.format(*_HEADERS))
    click.echo("  ".join("-" * w for w in _COL_WIDTHS))
    for r in results:
        click.echo(
            fmt.format(
                str(r.id),
                _trunc(r.track_name, _COL_WIDTHS[1]),
                _trunc(r.artist_name, _COL_WIDTHS[2]),
                _trunc(r.album_name, _COL_WIDTHS[3]),
                f"{int(r.duration)}s",
            )
        )


def _print_lyrics(
    result: LyricsResult,
    *,
    plain: bool,
    synced: bool,
    header: bool = False,
) -> None:
    if header:
        click.echo(str(result))
        click.echo()

    if not plain and not synced:
        # Default: prefer synced, fall back to plain
        text = result.synced_lyrics or result.plain_lyrics
        if text:
            click.echo(text)
        elif result.instrumental:
            click.echo("(Instrumental – no lyrics)")
        else:
            click.echo("(No lyrics available)")
        return

    if synced:
        if result.synced_lyrics:
            click.echo(result.synced_lyrics)
        else:
            click.echo("(No synced lyrics available)", err=True)

    if plain:
        if result.plain_lyrics:
            click.echo(result.plain_lyrics)
        else:
            click.echo("(No plain lyrics available)", err=True)


def _trunc(s: str, width: int) -> str:
    return s if len(s) <= width else s[: width - 1] + "…"


def _die(msg: str) -> None:
    click.echo(f"Error: {msg}", err=True)
    sys.exit(1)
