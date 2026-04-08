from __future__ import annotations
from dataclasses import dataclass


@dataclass
class LyricsResult:
    id: int
    name: str
    track_name: str
    artist_name: str
    album_name: str
    duration: float
    instrumental: bool
    plain_lyrics: str | None = None
    synced_lyrics: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> LyricsResult:
        return cls(
            id=data["id"],
            name=data.get("name", ""),
            track_name=data.get("trackName", ""),
            artist_name=data.get("artistName", ""),
            album_name=data.get("albumName", ""),
            duration=data.get("duration", 0),
            instrumental=data.get("instrumental", False),
            plain_lyrics=data.get("plainLyrics"),
            synced_lyrics=data.get("syncedLyrics"),
        )

    def __str__(self) -> str:
        lines = [
            f"ID:       {self.id}",
            f"Track:    {self.track_name}",
            f"Artist:   {self.artist_name}",
            f"Album:    {self.album_name}",
            f"Duration: {self.duration}s",
        ]
        if self.instrumental:
            lines.append("(Instrumental)")
        return "\n".join(lines)


@dataclass
class Challenge:
    prefix: str
    target: str
