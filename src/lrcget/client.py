"""lrclib.net API client."""
from __future__ import annotations

import hashlib
from typing import Iterator

import httpx

from .models import Challenge, LyricsResult

BASE_URL = "https://lrclib.net/api"
DEFAULT_USER_AGENT = "lrcget/0.1.0 (https://github.com/dobs/lrcget)"


class LrclibError(Exception):
    """Raised when the API returns an error response."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"HTTP {status_code}: {message}")


class LrclibNotFound(LrclibError):
    """Raised when a lyrics entry is not found (404)."""


class LrclibClient:
    """Synchronous client for the lrclib.net API.

    Usage::

        client = LrclibClient()

        # Search
        results = client.search("never gonna give you up", artist_name="Rick Astley")

        # Get by track details
        result = client.get(
            track_name="Never Gonna Give You Up",
            artist_name="Rick Astley",
            album_name="Whenever You Need Somebody",
            duration=213,
        )

        # Get by ID
        result = client.get_by_id(1)
    """

    def __init__(
        self,
        base_url: str = BASE_URL,
        user_agent: str = DEFAULT_USER_AGENT,
        timeout: float = 30.0,
    ) -> None:
        self._http = httpx.Client(
            base_url=base_url,
            headers={"User-Agent": user_agent},
            timeout=timeout,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> LrclibClient:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def search(
        self,
        query: str | None = None,
        *,
        track_name: str | None = None,
        artist_name: str | None = None,
        album_name: str | None = None,
    ) -> list[LyricsResult]:
        """Search the lrclib database.

        Either *query* or *track_name* must be provided.
        """
        if not query and not track_name:
            raise ValueError("Either 'query' or 'track_name' must be provided.")

        params: dict[str, str] = {}
        if query:
            params["q"] = query
        if track_name:
            params["track_name"] = track_name
        if artist_name:
            params["artist_name"] = artist_name
        if album_name:
            params["album_name"] = album_name

        data = self._get("/search", params=params)
        return [LyricsResult.from_dict(item) for item in data]

    def get(
        self,
        track_name: str,
        artist_name: str,
        album_name: str,
        duration: float,
    ) -> LyricsResult:
        """Fetch lyrics by track metadata."""
        params = {
            "track_name": track_name,
            "artist_name": artist_name,
            "album_name": album_name,
            "duration": str(int(duration)),
        }
        data = self._get("/get", params=params)
        return LyricsResult.from_dict(data)

    def get_by_id(self, lyrics_id: int) -> LyricsResult:
        """Fetch lyrics by lrclib numeric ID."""
        data = self._get(f"/get/{lyrics_id}")
        return LyricsResult.from_dict(data)

    def request_challenge(self) -> Challenge:
        """Request a proof-of-work challenge for publishing."""
        resp = self._http.post("/request-challenge")
        self._raise_for_status(resp)
        data = resp.json()
        return Challenge(prefix=data["prefix"], target=data["target"])

    def publish(
        self,
        track_name: str,
        artist_name: str,
        album_name: str,
        duration: float,
        *,
        plain_lyrics: str | None = None,
        synced_lyrics: str | None = None,
    ) -> None:
        """Publish lyrics to lrclib.

        Automatically solves the proof-of-work challenge.  This may take a
        few seconds while the nonce is computed.
        """
        challenge = self.request_challenge()
        nonce = _solve_challenge(challenge.prefix, challenge.target)

        payload: dict = {
            "trackName": track_name,
            "artistName": artist_name,
            "albumName": album_name,
            "duration": int(duration),
        }
        if plain_lyrics is not None:
            payload["plainLyrics"] = plain_lyrics
        if synced_lyrics is not None:
            payload["syncedLyrics"] = synced_lyrics

        resp = self._http.post(
            "/publish",
            json=payload,
            headers={"X-Publish-Token": nonce},
        )
        self._raise_for_status(resp)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _get(self, path: str, params: dict | None = None):
        resp = self._http.get(path, params=params)
        self._raise_for_status(resp)
        return resp.json()

    @staticmethod
    def _raise_for_status(resp: httpx.Response) -> None:
        if resp.status_code == 404:
            try:
                msg = resp.json().get("message", "Not found")
            except Exception:
                msg = "Not found"
            raise LrclibNotFound(404, msg)
        if resp.status_code >= 400:
            try:
                msg = resp.json().get("message", resp.text)
            except Exception:
                msg = resp.text
            raise LrclibError(resp.status_code, msg)


# ---------------------------------------------------------------------------
# Proof-of-work
# ---------------------------------------------------------------------------

def _nonces() -> Iterator[str]:
    """Yield candidate nonce strings: 0, 1, 2, ..."""
    n = 0
    while True:
        yield str(n)
        n += 1


def _solve_challenge(prefix: str, target: str) -> str:
    """Find a nonce such that SHA256(prefix + nonce) <= target (hex compare)."""
    target_lower = target.lower()
    for nonce in _nonces():
        digest = hashlib.sha256(f"{prefix}{nonce}".encode()).hexdigest()
        if digest <= target_lower:
            return nonce
    # unreachable
    raise RuntimeError("Failed to solve challenge")  # pragma: no cover
