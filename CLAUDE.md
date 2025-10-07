# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

iPod Organizer is a Python music player and library organizer with three interfaces (CLI, TUI, GUI) and specialized Rockbox device support. The application scans audio files, stores metadata in SQLite, manages playlists, and provides playback capabilities.

## Development Commands

### Setup
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt
```

### Testing
```bash
# Run all tests
pytest

# Run a specific test file
pytest tests/test_library.py

# Run a specific test function
pytest tests/test_library.py::test_add_and_list_tracks

# Run with verbose output
pytest -v
```

### Running the Application
```bash
# Main module entry point
python -m ipod_organizer <command>

# Common commands
python -m ipod_organizer scan /path/to/music
python -m ipod_organizer list-tracks
python -m ipod_organizer tui
python -m ipod_organizer gui

# Get help on all commands
python -m ipod_organizer --help
```

## Architecture

### Core Layer Pattern

The application follows a layered architecture with clear separation of concerns:

1. **Configuration Layer** (`config.py`): Defines application directory (`~/.ipod_organizer/` or `$IPOD_ORGANIZER_HOME`), database location, and log file path.

2. **Data Layer** (`database.py`): Thin SQLite wrapper providing schema management and connection handling. Uses WAL mode for concurrent access. All database operations flow through `LibraryDatabase.connect()` context manager.

3. **Domain Layer** (`library.py`): `MusicLibrary` facade encapsulating all track and playlist operations. Depends on `database.py` for persistence and optionally on `mutagen` for metadata extraction. The `Track` dataclass is the primary domain model.

4. **Playback Layer** (`playback.py`): `MusicPlayer` manages a queue and playback state using a background monitor thread. Abstracts audio backends via `_BaseBackend` interface, with `_PygameBackend` for real audio and `_SilentBackend` as a no-op fallback when pygame is unavailable.

5. **Interface Layers**:
   - **CLI** (`cli.py`): Argument parsing and command dispatch via `argparse` subcommands
   - **TUI** (`cli.py:run_tui`): REPL-based terminal interface using simple input loop
   - **GUI** (`gui.py`): Tkinter-based tabbed interface with threading for long-running operations

6. **Rockbox Integration** (`rockbox.py`): Standalone utilities for M3U playlist generation and file organization (Genre/Artist/Album hierarchy). These functions are independent of the library database.

### Key Architectural Decisions

- **Optional Dependencies**: Both `mutagen` (metadata) and `pygame` (audio) are optional. Code gracefully degrades when they're missing.
- **Threading Model**: GUI uses background threads for I/O operations to keep UI responsive. Playback uses a dedicated monitor thread that polls backend status every 250ms.
- **Database Access**: All database operations auto-commit via context manager. No manual transaction management is exposed.
- **Path Handling**: All file paths are resolved to absolute paths immediately upon entry to prevent working directory issues.

### Data Flow Examples

**Scanning a directory**:
1. CLI parses `scan` command → calls `MusicLibrary.scan_directory()`
2. `scan_directory()` walks filesystem, filters by `SUPPORTED_EXTENSIONS`
3. For each file: `add_track()` → `_extract_metadata()` (via mutagen) → `LibraryDatabase.execute()` INSERT
4. Returns list of `Track` objects

**Playing a track**:
1. User action → `MusicPlayer.play_now(track)`
2. Clears queue, calls `_start_track()` → `_backend.play(track.path)`
3. Monitor thread polls `_backend.is_busy()` every 250ms
4. When playback finishes, monitor dequeues next track or sets status to "stopped"

## File Organization

```
ipod_organizer/
├── __init__.py
├── __main__.py          # Entry point (delegates to cli.main)
├── config.py            # App directory and paths
├── database.py          # SQLite wrapper
├── library.py           # MusicLibrary facade and Track model
├── playback.py          # MusicPlayer with backend abstraction
├── cli.py               # CLI commands and TUI
├── gui.py               # Tkinter GUI
└── rockbox.py           # M3U export and file organization utilities

tests/
├── test_library.py      # Library and playlist tests
└── test_rockbox.py      # Rockbox utility tests
```

## Important Implementation Notes

### Adding New CLI Commands

1. Add subparser in `cli.py:build_parser()`
2. Add command handler in `cli.py:main()` matching the `args.command` value
3. Use existing patterns: parse args, call library methods, print results

### Metadata Extraction

`mutagen` is the sole metadata library. It handles ID3 tags (MP3) and Vorbis comments (FLAC/OGG) via unified interface. The `_extract_metadata()` function in `library.py` maps common tag names (TIT2/title, TPE1/artist, TALB/album, etc.) to a normalized dict.

### Playback Backend

To add a new backend, subclass `_BaseBackend` and implement all abstract methods. Instantiate in `MusicPlayer.__init__()` with try/except fallback pattern.

### GUI Threading

Long-running operations (scan, export, organize) must run in background threads. Results are communicated back to the main thread via `_notify_main_thread()` which uses `root.after(0, callback)` for thread-safe UI updates.

### Database Schema

Current schema version is 1. Schema migrations would increment `SCHEMA_VERSION` and add migration logic in `LibraryDatabase._ensure_schema()`. The schema uses:
- `tracks`: Main track table with path uniqueness constraint
- `playlists`: Named playlists
- `playlist_tracks`: Junction table with position ordering
- `meta`: Key-value store for schema version

## Testing Patterns

Tests use pytest with `tmp_path` fixture for isolated database files. The `make_library()` helper in `test_library.py` creates a `MusicLibrary` with a temporary database. For testing track scanning, create fake files with `.write_bytes()` since mutagen is optional and metadata extraction is not required for core functionality.

## Environment Variables

- `IPOD_ORGANIZER_HOME`: Override default `~/.ipod_organizer/` directory for library database and logs
