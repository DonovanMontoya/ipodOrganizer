"""High level library management for tracks and playlists."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

from .database import LibraryDatabase

try:
    from mutagen import File as MutagenFile  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    MutagenFile = None

SUPPORTED_EXTENSIONS = {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"}

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Track:
    """A track in the music library."""

    id: int | None
    path: Path
    title: str
    artist: Optional[str]
    album: Optional[str]
    duration: Optional[float]
    track_number: Optional[str]
    disc_number: Optional[str]


class MusicLibrary:
    """Facade over `LibraryDatabase` for common operations."""

    def __init__(self, db: Optional[LibraryDatabase] = None):
        self.db = db or LibraryDatabase()

    def scan_directory(self, path: Path) -> list[Track]:
        """Add all supported audio files under a directory."""
        logger.info("Scanning directory %s", path)
        added: list[Track] = []
        for file_path in sorted(path.rglob("*")):
            if not file_path.is_file():
                continue
            if file_path.suffix.lower() not in SUPPORTED_EXTENSIONS:
                continue
            track = self.add_track(file_path)
            if track:
                added.append(track)
        logger.info("Added %d tracks from %s", len(added), path)
        return added

    def add_track(self, path: Path) -> Optional[Track]:
        """Insert a new track into the database or return existing one."""
        path = path.resolve()
        metadata = _extract_metadata(path)
        existing = self.db.fetchone("SELECT * FROM tracks WHERE path=?", (str(path),))
        if existing:
            logger.debug("Track already exists: %s", path)
            return self._row_to_track(existing)
        self.db.execute(
            """
            INSERT INTO tracks (path, title, artist, album, duration, track_number, disc_number)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(path),
                metadata.get("title", path.stem),
                metadata.get("artist"),
                metadata.get("album"),
                metadata.get("duration"),
                metadata.get("track_number"),
                metadata.get("disc_number"),
            ),
        )
        row = self.db.fetchone("SELECT * FROM tracks WHERE path=?", (str(path),))
        if row:
            return self._row_to_track(row)
        return None

    def list_tracks(self, search: Optional[str] = None) -> list[Track]:
        sql = "SELECT * FROM tracks"
        params: tuple = ()
        if search:
            sql += " WHERE title LIKE ? OR artist LIKE ? OR album LIKE ?"
            wildcard = f"%{search}%"
            params = (wildcard, wildcard, wildcard)
        sql += " ORDER BY artist, album, track_number, title"
        rows = self.db.fetchall(sql, params)
        return [self._row_to_track(row) for row in rows]

    def get_track(self, track_id: int) -> Optional[Track]:
        row = self.db.fetchone("SELECT * FROM tracks WHERE id=?", (track_id,))
        return self._row_to_track(row) if row else None

    def create_playlist(self, name: str) -> None:
        self.db.execute("INSERT OR IGNORE INTO playlists (name) VALUES (?)", (name,))

    def delete_playlist(self, name: str) -> None:
        playlist = self.db.fetchone("SELECT id FROM playlists WHERE name=?", (name,))
        if playlist:
            self.db.execute("DELETE FROM playlists WHERE id=?", (playlist["id"],))

    def add_to_playlist(self, playlist_name: str, track_id: int) -> None:
        playlist = self.db.fetchone("SELECT id FROM playlists WHERE name=?", (playlist_name,))
        if not playlist:
            raise ValueError(f"Playlist {playlist_name!r} does not exist")
        max_pos_row = self.db.fetchone(
            "SELECT COALESCE(MAX(position), 0) AS pos FROM playlist_tracks WHERE playlist_id=?",
            (playlist["id"],),
        )
        next_pos = (max_pos_row["pos"] or 0) + 1
        self.db.execute(
            """
            INSERT OR REPLACE INTO playlist_tracks (playlist_id, track_id, position)
            VALUES (?, ?, ?)
            """,
            (playlist["id"], track_id, next_pos),
        )

    def list_playlists(self) -> list[tuple[str, list[Track]]]:
        playlists = self.db.fetchall("SELECT id, name FROM playlists ORDER BY name")
        result: list[tuple[str, list[Track]]] = []
        for playlist in playlists:
            tracks = self.db.fetchall(
                """
                SELECT t.*
                FROM playlist_tracks pt
                JOIN tracks t ON t.id = pt.track_id
                WHERE pt.playlist_id=?
                ORDER BY pt.position
                """,
                (playlist["id"],),
            )
            result.append((playlist["name"], [self._row_to_track(row) for row in tracks]))
        return result

    def remove_track(self, track_id: int) -> None:
        self.db.execute("DELETE FROM tracks WHERE id=?", (track_id,))

    def record_play(self, track_id: int) -> None:
        self.db.execute(
            """
            UPDATE tracks
            SET play_count = play_count + 1,
                last_played = CURRENT_TIMESTAMP
            WHERE id=?
            """,
            (track_id,),
        )

    def _row_to_track(self, row) -> Track:
        return Track(
            id=row["id"],
            path=Path(row["path"]),
            title=row["title"],
            artist=row["artist"],
            album=row["album"],
            duration=row["duration"],
            track_number=row["track_number"],
            disc_number=row["disc_number"],
        )


def _extract_metadata(path: Path) -> dict[str, Optional[str | float]]:
    """Fetch metadata via mutagen if available."""
    if not MutagenFile:
        return {}
    try:
        meta = MutagenFile(path)
        if not meta:
            return {}
        tags = meta.tags or {}
        return {
            "title": _first(tags.get("TIT2") or tags.get("title")),
            "artist": _first(tags.get("TPE1") or tags.get("artist")),
            "album": _first(tags.get("TALB") or tags.get("album")),
            "duration": getattr(meta.info, "length", None),
            "track_number": _first(tags.get("TRCK") or tags.get("tracknumber")),
            "disc_number": _first(tags.get("TPOS") or tags.get("discnumber")),
        }
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to read metadata for %s", path)
        return {}


def _first(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        return str(value[0])
    return str(value)
