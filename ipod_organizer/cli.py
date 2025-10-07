"""Command line interface for the ipod_organizer app."""

from __future__ import annotations

import argparse
import logging
import shlex
import sys
import time
from pathlib import Path
from typing import Iterable

from .config import LOG_FILE, ensure_app_dirs
from .library import MusicLibrary, Track
from .playback import MusicPlayer, PlaybackUnavailableError
from .rockbox import bundle_for_rockbox, export_m3u_playlists, organize_music_collection

LOG_FORMAT = "%(asctime)s %(levelname)s [%(name)s] %(message)s"


def setup_logging(verbose: bool = False) -> None:
    ensure_app_dirs()
    handlers: list[logging.Handler] = [
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(sys.stderr),
    ]
    logging.basicConfig(
        level=logging.DEBUG if verbose else logging.INFO,
        format=LOG_FORMAT,
        handlers=handlers,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    setup_logging(verbose=args.verbose)

    library = MusicLibrary()

    if args.command == "scan":
        directory = Path(args.directory).expanduser()
        if not directory.exists():
            parser.error(f"Directory {directory} does not exist")
        tracks = library.scan_directory(directory)
        print(f"Imported {len(tracks)} tracks from {directory}")
        return 0

    if args.command == "list-tracks":
        tracks = library.list_tracks(args.search)
        if not tracks:
            print("No tracks found.")
            return 0
        for track in tracks:
            print(format_track(track))
        return 0

    if args.command == "list-playlists":
        playlists = library.list_playlists()
        if not playlists:
            print("No playlists defined.")
            return 0
        for name, tracks in playlists:
            print(f"{name} ({len(tracks)} tracks)")
            for track in tracks:
                print(f"  - {track.id}: {track.title} — {track.artist or 'Unknown'}")
        return 0

    if args.command == "create-playlist":
        library.create_playlist(args.name)
        print(f"Playlist '{args.name}' created.")
        return 0

    if args.command == "add-to-playlist":
        library.add_to_playlist(args.name, args.track_id)
        print(f"Added track {args.track_id} to playlist {args.name}.")
        return 0

    if args.command == "remove-track":
        library.remove_track(args.track_id)
        print(f"Removed track {args.track_id}.")
        return 0

    if args.command == "play":
        track = _require_track(library, args.track_id)
        try:
            player = MusicPlayer(on_track_start=lambda t: library.record_play(t.id or 0))
        except PlaybackUnavailableError as exc:
            print(f"Cannot play track: {exc}")
            return 1
        player.play_now(track)
        _wait_for_completion(player)
        return 0

    if args.command == "tui":
        return run_tui(library)

    if args.command == "gui":
        from .gui import run_gui

        run_gui()
        return 0

    if args.command == "export-rockbox":
        extensions = None
        if args.extensions:
            raw_extensions = [piece.strip() for piece in args.extensions.split(",") if piece.strip()]
            extensions = [
                ext if ext.startswith(".") else f".{ext}"
                for ext in raw_extensions
            ]
        results = export_m3u_playlists(
            Path(args.source),
            Path(args.destination) if args.destination else None,
            extensions=extensions,
            recursive=args.recursive,
        )
        if not results:
            print("No playlists generated (no matching tracks).")
            return 0
        for result in results:
            rel = result.playlist_path
            print(f"Created {rel} ({result.track_count} tracks)")
        return 0

    if args.command == "organize-rockbox":
        extensions = None
        if args.extensions:
            raw_extensions = [piece.strip() for piece in args.extensions.split(",") if piece.strip()]
            extensions = [
                ext if ext.startswith(".") else f".{ext}"
                for ext in raw_extensions
            ]
        destination = Path(args.destination)
        destination.mkdir(parents=True, exist_ok=True)
        try:
            results = organize_music_collection(
                Path(args.source),
                destination,
                move=args.move,
                include_genre=args.include_genre,
                extensions=extensions,
                recursive=not args.no_recursive,
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1
        if not results:
            print("No matching audio files found.")
            return 0
        moved = sum(1 for r in results if r.action == "moved")
        copied = sum(1 for r in results if r.action == "copied")
        errors = [r for r in results if r.action == "error"]
        for result in results:
            if result.destination:
                print(f"{result.action.title()}: {result.source} -> {result.destination}")
            else:
                print(f"{result.action.title()}: {result.source} ({result.reason})")
        print(f"Completed: {copied} copied, {moved} moved, {len(errors)} errors.")
        if errors:
            return 1
        return 0

    if args.command == "bundle-rockbox":
        extensions = None
        if args.extensions:
            raw_extensions = [piece.strip() for piece in args.extensions.split(",") if piece.strip()]
            extensions = [
                ext if ext.startswith(".") else f".{ext}"
                for ext in raw_extensions
            ]
        destination = Path(args.destination)
        destination.mkdir(parents=True, exist_ok=True)
        album_dirs = [Path(p) for p in args.albums] if args.albums else None
        playlist_dirs = [Path(p) for p in args.playlists] if args.playlists else None
        try:
            result = bundle_for_rockbox(
                album_dirs,
                playlist_dirs,
                destination,
                include_genre=args.include_genre,
                move_albums=args.move_albums,
                move_playlists=args.move_playlists,
                extensions=extensions,
            )
        except ValueError as exc:
            print(f"Error: {exc}")
            return 1

        if not result.music_results and not result.playlist_results:
            print("No matching audio files found.")
            return 0

        copied = sum(1 for r in result.music_results if r.action == "copied")
        moved = sum(1 for r in result.music_results if r.action == "moved")
        errors = [r for r in result.music_results if r.action == "error"]

        for playlist in result.playlist_results:
            label = playlist.playlist_path
            print(f"Playlist: {label} ({playlist.track_count} tracks)")
            for missing in playlist.missing_sources:
                print(f"  ! Skipped {missing}")

        print(f"Tracks: {copied} copied, {moved} moved, {len(errors)} errors.")
        if errors:
            return 1
        return 0

    parser.print_help()
    return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ipod_organizer")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging.")

    subparsers = parser.add_subparsers(dest="command")

    scan = subparsers.add_parser("scan", help="Import tracks from a directory.")
    scan.add_argument("directory", help="Directory to scan for audio files.")

    list_tracks = subparsers.add_parser("list-tracks", help="List tracks in the library.")
    list_tracks.add_argument("--search", help="Search string for title/artist/album.")

    subparsers.add_parser("list-playlists", help="List playlists.")

    create_playlist = subparsers.add_parser("create-playlist", help="Create a playlist.")
    create_playlist.add_argument("name")

    add_to_playlist = subparsers.add_parser("add-to-playlist", help="Add a track to a playlist.")
    add_to_playlist.add_argument("name")
    add_to_playlist.add_argument("track_id", type=int)

    remove_track = subparsers.add_parser("remove-track", help="Remove a track from the library.")
    remove_track.add_argument("track_id", type=int)

    play = subparsers.add_parser("play", help="Play a track immediately.")
    play.add_argument("track_id", type=int)

    subparsers.add_parser("tui", help="Launch the interactive terminal UI.")
    subparsers.add_parser("gui", help="Launch the graphical interface.")

    rockbox = subparsers.add_parser(
        "export-rockbox",
        help="Write .m3u playlists for a directory tree (Rockbox-friendly).",
    )
    rockbox.add_argument("source", help="Directory containing audio files.")
    rockbox.add_argument(
        "--destination",
        help="Directory to write playlists (defaults to source).",
    )
    rockbox.add_argument(
        "--extensions",
        help="Comma-separated list of file extensions to include (default: supported audio formats).",
    )
    rockbox.add_argument(
        "--recursive",
        action="store_true",
        help="Create playlists for subdirectories recursively.",
    )

    bundle = subparsers.add_parser(
        "bundle-rockbox",
        help="Organize albums and playlist folders into a Rockbox-ready bundle.",
    )
    bundle.add_argument(
        "--albums",
        action="append",
        help="Directory containing albums (repeat to specify multiple roots).",
    )
    bundle.add_argument(
        "--playlists",
        action="append",
        help="Directory containing playlist folders (repeatable).",
    )
    bundle.add_argument(
        "destination",
        help="Root directory where the bundled output should be written.",
    )
    bundle.add_argument(
        "--extensions",
        help="Comma-separated file extensions (default: supported audio formats).",
    )
    bundle.add_argument(
        "--include-genre",
        action="store_true",
        help="Include genre as the top-level folder under Music/.",
    )
    bundle.add_argument(
        "--move-albums",
        action="store_true",
        help="Move album files instead of copying them.",
    )
    bundle.add_argument(
        "--move-playlists",
        action="store_true",
        help="Move playlist files instead of copying them.",
    )

    organize = subparsers.add_parser(
        "organize-rockbox",
        help="Sort audio files into Artist/Album folders for Rockbox.",
    )
    organize.add_argument("source", help="Directory containing unsorted audio files.")
    organize.add_argument("destination", help="Where organized files should be placed.")
    organize.add_argument(
        "--extensions",
        help="Comma-separated file extensions (default: supported audio formats).",
    )
    organize.add_argument(
        "--move",
        action="store_true",
        help="Move files instead of copying them.",
    )
    organize.add_argument(
        "--include-genre",
        action="store_true",
        help="Include genre as the top folder level.",
    )
    organize.add_argument(
        "--no-recursive",
        action="store_true",
        help="Do not walk subdirectories when collecting files.",
    )

    return parser


def format_track(track: Track) -> str:
    artist = track.artist or "Unknown Artist"
    album = track.album or "Unknown Album"
    return f"{track.id}: {artist} — {track.title} [{album}]"


def _require_track(library: MusicLibrary, track_id: int) -> Track:
    track = library.get_track(track_id)
    if not track:
        raise SystemExit(f"Track #{track_id} not found.")
    return track


def _wait_for_completion(player: MusicPlayer) -> None:
    try:
        while player.status in {"playing", "paused"}:
            time.sleep(0.5)
    except KeyboardInterrupt:
        player.stop()
    finally:
        player.shutdown()


def run_tui(library: MusicLibrary) -> int:
    """Simple REPL to manage the library and playback."""
    try:
        player = MusicPlayer(on_track_start=lambda t: library.record_play(t.id or 0))
    except PlaybackUnavailableError as exc:
        print(f"Audio backend not available: {exc}")
        return 1

    print("iPod Organizer TUI. Type 'help' for commands. Ctrl+C to exit.")
    try:
        while True:
            try:
                raw = input("ipod> ").strip()
            except EOFError:
                print()
                break
            if not raw:
                continue
            parts = shlex.split(raw)
            command, *params = parts
            command = command.lower()

            if command in {"quit", "exit"}:
                break
            if command == "help":
                _print_help()
                continue
            if command == "list":
                for track in library.list_tracks(params[0] if params else None):
                    print(format_track(track))
                continue
            if command == "play":
                if not params:
                    print("Usage: play <track_id>")
                    continue
                track = library.get_track(int(params[0]))
                if not track:
                    print(f"Track {params[0]} not found.")
                    continue
                player.play_now(track)
                continue
            if command == "queue":
                if not params:
                    print("Usage: queue <track_id>")
                    continue
                track = library.get_track(int(params[0]))
                if not track:
                    print(f"Track {params[0]} not found.")
                    continue
                player.queue_track(track)
                print(f"Queued {track.title}")
                continue
            if command == "pause":
                player.pause()
                continue
            if command == "resume":
                player.resume()
                continue
            if command in {"skip", "next"}:
                player.skip()
                continue
            if command == "stop":
                player.stop()
                continue
            if command == "now":
                now = player.current_track
                if now:
                    print(f"Playing: {format_track(now)}")
                else:
                    print("Nothing playing.")
                continue
            if command == "rockbox":
                recursive = False
                filtered: list[str] = []
                for param in params:
                    if param == "--recursive":
                        recursive = True
                    else:
                        filtered.append(param)
                if not filtered:
                    print("Usage: rockbox <source_dir> [destination_dir] [--recursive]")
                    continue
                source_dir = Path(filtered[0]).expanduser()
                destination_dir = Path(filtered[1]).expanduser() if len(filtered) > 1 else None
                try:
                    results = export_m3u_playlists(source_dir, destination_dir, recursive=recursive)
                except ValueError as exc:
                    print(str(exc))
                    continue
                for result in results:
                    rel = result.playlist_path
                    print(f"Wrote {rel} ({result.track_count} tracks)")
                if not results:
                    print("No playlists created.")
                continue
            print(f"Unknown command: {command}")
    except KeyboardInterrupt:
        print("\nExiting.")
    finally:
        player.shutdown()
    return 0


def _print_help() -> None:
    print(
        "Commands:\n"
        "  list [query]   - list tracks, optionally filtered\n"
        "  play <id>      - play immediately\n"
        "  queue <id>     - queue track\n"
        "  pause/resume   - control playback\n"
        "  skip|next      - skip current track\n"
        "  stop           - stop playback and clear queue\n"
        "  now            - show current track\n"
        "  rockbox SRC [DEST] [--recursive]\n"
        "  help           - show this message\n"
        "  quit/exit      - exit the interface"
    )


if __name__ == "__main__":
    sys.exit(main())
