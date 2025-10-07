"""Helpers for exporting playlists compatible with Rockbox."""

from __future__ import annotations

import logging
import os
import re
import shutil
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Optional, Sequence

from .library import SUPPORTED_EXTENSIONS
from .library import MutagenFile  # reuse optional import

# Rockbox happily ingests standard M3U files with LF endings.
PLAYLIST_HEADER = "#EXTM3U\n"
logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExportResult:
    """Result information for a generated playlist."""

    playlist_path: Path
    track_count: int


@dataclass(slots=True)
class OrganizeResult:
    """Record of an individual file operation during organization."""

    source: Path
    destination: Optional[Path]
    action: str
    reason: Optional[str] = None
    components: Optional[dict[str, str]] = None


@dataclass(slots=True)
class PlaylistBuildResult:
    """Summary for a generated playlist during bundling."""

    playlist_path: Path
    track_count: int
    missing_sources: list[Path] = field(default_factory=list)


@dataclass(slots=True)
class BundleResult:
    """Combined output from bundling albums and playlists."""

    music_results: list[OrganizeResult]
    playlist_results: list[PlaylistBuildResult]


def export_m3u_playlists(
    source: Path,
    destination: Path | None = None,
    extensions: Sequence[str] | None = None,
    recursive: bool = False,
) -> list[ExportResult]:
    """
    Generate .m3u playlists from the audio files inside a directory.

    Args:
        source: Directory containing music files.
        destination: Folder where playlists should be written. Defaults to `source`.
        extensions: Explicit extensions (including dot). Defaults to supported audio types.
        recursive: Create a playlist per subdirectory (mirroring structure).

    Returns:
        List of `ExportResult` describing created playlists.
    """

    source = Path(source).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"{source} is not a directory")

    destination = (
        Path(destination).expanduser().resolve() if destination else source
    )
    exts = {ext.lower() for ext in (extensions or SUPPORTED_EXTENSIONS)}

    directories = _collect_directories(source, recursive=recursive)
    results: list[ExportResult] = []

    for directory in directories:
        tracks = _list_tracks(directory, exts)
        if not tracks:
            continue
        playlist_path = _build_playlist_path(source, directory, destination)
        playlist_path.parent.mkdir(parents=True, exist_ok=True)
        with playlist_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(PLAYLIST_HEADER)
            for track in tracks:
                rel_path = _relative_path(track, playlist_path.parent)
                handle.write(rel_path + "\n")
        results.append(ExportResult(playlist_path=playlist_path, track_count=len(tracks)))
    return results


def organize_music_collection(
    source: Path,
    destination: Path,
    *,
    move: bool = False,
    include_genre: bool = False,
    extensions: Sequence[str] | None = None,
    recursive: bool = True,
) -> list[OrganizeResult]:
    """
    Reorganize audio files into a Rockbox-friendly folder layout.

    Args:
        source: Root directory containing audio files.
        destination: Root directory to write organized files.
        move: Move files instead of copying.
        include_genre: Include a genre directory level (`Genre/Artist/Album/...`).
        extensions: Audio file extensions to include. Defaults to supported ones.
        recursive: Whether to walk subdirectories within source.
    """

    source = Path(source).expanduser().resolve()
    destination = Path(destination).expanduser().resolve()
    if not source.is_dir():
        raise ValueError(f"{source} is not a directory")
    if not destination.exists():
        destination.mkdir(parents=True, exist_ok=True)

    exts = {ext.lower() for ext in (extensions or SUPPORTED_EXTENSIONS)}

    results: list[OrganizeResult] = []
    paths: Iterable[Path]
    if recursive:
        paths = sorted(p for p in source.rglob("*") if p.is_file())
    else:
        paths = sorted(p for p in source.iterdir() if p.is_file())

    for file_path in paths:
        if file_path.suffix.lower() not in exts:
            continue
        try:
            tags = _read_tags(file_path)
            components = _derive_components(file_path, tags, include_genre)
            target_path, action = _place_track(
                file_path,
                destination,
                components=components,
                include_genre=include_genre,
                move=move,
            )
            results.append(
                OrganizeResult(
                    source=file_path,
                    destination=target_path,
                    action=action,
                    components=components,
                )
            )
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to organize %s: %s", file_path, exc)
            results.append(
                OrganizeResult(
                    source=file_path,
                    destination=None,
                    action="error",
                    reason=str(exc),
                )
            )
    return results


def bundle_for_rockbox(
    album_dirs: Sequence[Path] | None,
    playlist_dirs: Sequence[Path] | None,
    destination: Path,
    *,
    include_genre: bool = False,
    move_albums: bool = False,
    move_playlists: bool = False,
    extensions: Sequence[str] | None = None,
    progress_callback: Callable[[int, int, str], None] | None = None,
) -> BundleResult:
    """
    Prepare a Rockbox-ready bundle containing organized music and M3U playlists.

    Args:
        album_dirs: Directories containing full album collections.
        playlist_dirs: Directories containing folders of ad-hoc playlist tracks.
        destination: Root directory where `Music/` and `Playlists/` will be created.
        include_genre: Include genre folders in the music hierarchy.
        move_albums: Move album files instead of copying them.
        move_playlists: Move playlist files instead of copying them when missing from albums.
        extensions: Audio file extensions to include.
        progress_callback: Optional callback receiving (completed, total, message).
    """

    album_paths = [Path(p).expanduser().resolve() for p in (album_dirs or [])]
    playlist_paths = [Path(p).expanduser().resolve() for p in (playlist_dirs or [])]
    if not album_paths and not playlist_paths:
        raise ValueError("Provide at least one album directory or playlist directory.")

    dest_root = Path(destination).expanduser().resolve()
    music_root = dest_root / "Music"
    playlists_root = dest_root / "Playlists"
    music_root.mkdir(parents=True, exist_ok=True)
    playlists_root.mkdir(parents=True, exist_ok=True)

    exts = {ext.lower() for ext in (extensions or SUPPORTED_EXTENSIONS)}

    track_index: dict[tuple[str, str, str, str, str], Path] = {}
    music_results: list[OrganizeResult] = []
    playlist_results: list[PlaylistBuildResult] = []

    album_files: list[Path] = []
    for album_path in album_paths:
        if not album_path.is_dir():
            raise ValueError(f"{album_path} is not a directory")
        album_files.extend(
            sorted(
                p
                for p in album_path.rglob("*")
                if p.is_file() and p.suffix.lower() in exts
            )
        )

    playlist_groups: list[tuple[str, list[Path]]] = []
    total_playlist_tracks = 0
    for playlists_path in playlist_paths:
        if not playlists_path.is_dir():
            raise ValueError(f"{playlists_path} is not a directory")
        groups = list(_enumerate_playlist_sources(playlists_path))
        playlist_groups.extend(groups)
        total_playlist_tracks += sum(len(tracks) for _, tracks in groups)

    total_steps = len(album_files) + total_playlist_tracks
    processed_steps = 0

    def report(message: str) -> None:
        if progress_callback and total_steps > 0:
            progress_callback(processed_steps, total_steps, message)

    if total_steps > 0:
        report("Preparing Rockbox bundle...")

    album_total = len(album_files)
    for idx, file_path in enumerate(album_files, start=1):
        try:
            tags = _read_tags(file_path)
            components = _derive_components(file_path, tags, include_genre)
            destination_path, action = _place_track(
                file_path,
                music_root,
                components=components,
                include_genre=include_genre,
                move=move_albums,
            )
            result = OrganizeResult(
                source=file_path,
                destination=destination_path,
                action=action,
                components=components,
            )
            music_results.append(result)
            track_index.setdefault(_track_key(components), destination_path)
        except Exception as exc:  # pragma: no cover - defensive
            logger.exception("Failed to bundle album track %s: %s", file_path, exc)
            music_results.append(
                OrganizeResult(
                    source=file_path,
                    destination=None,
                    action="error",
                    reason=str(exc),
                )
            )

        processed_steps += 1
        report(f"Staging albums... {idx}/{album_total}")

    playlist_processed = 0
    for raw_name, track_files in playlist_groups:
        sanitized_name = _safe_component(raw_name) or "Playlist"
        playlist_path = playlists_root / f"{sanitized_name}.m3u"
        counter = 1
        while playlist_path.exists():
            playlist_path = playlists_root / f"{sanitized_name} ({counter}).m3u"
            counter += 1

        missing: list[Path] = []
        written = 0
        with playlist_path.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(PLAYLIST_HEADER)
            for track_file in track_files:
                playlist_processed += 1
                try:
                    if track_file.suffix.lower() not in exts:
                        missing.append(track_file)
                        continue
                    tags = _read_tags(track_file)
                    components = _derive_components(track_file, tags, include_genre)
                    key = _track_key(components)
                    dest_path = track_index.get(key)
                    if not dest_path:
                        dest_path, action = _place_track(
                            track_file,
                            music_root,
                            components=components,
                            include_genre=include_genre,
                            move=move_playlists,
                        )
                        result = OrganizeResult(
                            source=track_file,
                            destination=dest_path,
                            action=action,
                            components=components,
                        )
                        music_results.append(result)
                        track_index[key] = dest_path
                    rel_path = Path(os.path.relpath(dest_path, playlists_root)).as_posix()
                    handle.write(rel_path + "\n")
                    written += 1
                except Exception as exc:  # pragma: no cover - defensive
                    logger.exception("Failed to bundle %s: %s", track_file, exc)
                    missing.append(track_file)
                finally:
                    processed_steps += 1
                    denominator = max(total_playlist_tracks, playlist_processed, 1)
                    report(
                        f"Bundling playlists... {playlist_processed}/{denominator}"
                    )
        playlist_results.append(
            PlaylistBuildResult(
                playlist_path=playlist_path,
                track_count=written,
                missing_sources=missing,
            )
        )

    if total_steps > 0:
        processed_steps = total_steps
        report("Rockbox bundle complete")

    return BundleResult(music_results=music_results, playlist_results=playlist_results)


def _collect_directories(root: Path, recursive: bool) -> Iterable[Path]:
    if not recursive:
        return [root]
    directories = [root]
    for subdir in sorted(p for p in root.rglob("*") if p.is_dir()):
        directories.append(subdir)
    return directories


def _list_tracks(directory: Path, extensions: set[str]) -> list[Path]:
    files = [
        entry
        for entry in directory.iterdir()
        if entry.is_file() and entry.suffix.lower() in extensions
    ]
    files.sort()
    return files


def _build_playlist_path(source_root: Path, directory: Path, destination_root: Path) -> Path:
    relative = directory.relative_to(source_root)
    target_dir = destination_root / relative
    name = directory.name
    return target_dir / f"{name}.m3u"


def _relative_path(target: Path, base: Path) -> str:
    return Path(os.path.relpath(target, base)).as_posix()


def _read_tags(path: Path) -> dict[str, Optional[str]]:
    if not MutagenFile:
        return {}
    try:
        audio = MutagenFile(path)
        if not audio:
            return {}
        tags = audio.tags or {}
        info = {
            "title": _first(tags.get("TIT2") or tags.get("title")),
            "artist": _first(tags.get("TPE1") or tags.get("artist")),
            "album": _first(tags.get("TALB") or tags.get("album")),
            "track_number": _first(tags.get("TRCK") or tags.get("tracknumber")),
            "genre": _first(tags.get("TCON") or tags.get("genre")),
        }
        return info
    except Exception:  # pragma: no cover - metadata failures
        logger.exception("Failed to read tags for %s", path)
        return {}


def _first(value) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, (list, tuple)):
        if not value:
            return None
        return str(value[0])
    return str(value)


INVALID_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1F]')
MULTI_SPACES = re.compile(r"\s+")


def _safe_component(text: str) -> str:
    stripped = text.strip()
    cleaned = INVALID_CHARS.sub(" ", stripped)
    cleaned = MULTI_SPACES.sub(" ", cleaned)
    cleaned = cleaned.strip(". ")
    cleaned = cleaned.strip()
    return cleaned or "Unknown"


def _format_track_number(value: Optional[str], fallback_stem: Optional[str] = None) -> str:
    if value:
        match = re.match(r"(\d+)", value)
        if match:
            return match.group(1).zfill(2)
    if fallback_stem:
        match = re.match(r"^\s*(\d{1,3})\b", fallback_stem)
        if match:
            return match.group(1).zfill(2)
    return "00"


def _primary_artist(name: str) -> str:
    """Return the primary artist from a potentially multi-artist string."""
    separators = re.compile(r"\s*(?:;|,|/|\\|&| feat\.?| featuring | ft\.?| with | and | x )\s*", re.IGNORECASE)
    primary = separators.split(name, maxsplit=1)[0] if name else name
    return _safe_component(primary or "Unknown Artist")


def _derive_components(
    file_path: Path, tags: dict[str, Optional[str]], include_genre: bool
) -> dict[str, str]:
    artist = _primary_artist(tags.get("artist") or "Unknown Artist")
    album = _safe_component(tags.get("album") or "Unknown Album")
    title = _safe_component(tags.get("title") or file_path.stem)
    track_no = _format_track_number(tags.get("track_number"), file_path.stem)
    raw_genre = tags.get("genre")
    if include_genre:
        genre = _safe_component(raw_genre or "Unknown Genre")
    else:
        genre = _safe_component(raw_genre) if raw_genre else ""
    return {
        "artist": artist,
        "album": album,
        "title": title,
        "track": track_no,
        "genre": genre,
        "suffix": file_path.suffix.lower(),
    }


def _place_track(
    file_path: Path,
    destination_root: Path,
    *,
    components: dict[str, str],
    include_genre: bool,
    move: bool,
) -> tuple[Path, str]:
    parts: list[str] = []
    genre_component = components.get("genre")
    if include_genre and genre_component:
        parts.append(genre_component)
    parts.extend([components["artist"], components["album"]])
    target_dir = destination_root.joinpath(*parts)
    target_dir.mkdir(parents=True, exist_ok=True)

    base_name = f"{components['track']} - {components['title']}{components['suffix']}"
    target_path = target_dir / base_name
    counter = 1
    while target_path.exists():
        target_path = target_dir / f"{components['track']} - {components['title']} ({counter}){components['suffix']}"
        counter += 1

    if move:
        shutil.move(str(file_path), target_path)
        action = "moved"
    else:
        shutil.copy2(file_path, target_path)
        action = "copied"
    return target_path, action


def _track_key(components: dict[str, str]) -> tuple[str, str, str, str, str]:
    return (
        components["artist"],
        components["album"],
        components["title"],
        components["track"],
        components["suffix"],
    )


def _enumerate_playlist_sources(root: Path) -> list[tuple[str, list[Path]]]:
    groups: list[tuple[str, list[Path]]] = []
    root_tracks = sorted(p for p in root.iterdir() if p.is_file())
    if root_tracks:
        groups.append((root.name, root_tracks))
    for subdir in sorted(p for p in root.iterdir() if p.is_dir()):
        tracks = sorted(p for p in subdir.rglob("*") if p.is_file())
        if tracks:
            groups.append((subdir.name, tracks))
    return groups
