# iPod Organizer

iPod Organizer is a Python music library manager with terminal and desktop interfaces. It scans folders for audio, stores metadata in SQLite, offers quick searching and playback, and exports playlists ready for Rockbox devices.

## Table of Contents
1. [Overview](#overview)
2. [Feature Highlights](#feature-highlights)
3. [Quick Start](#quick-start)
4. [Usage Guide](#usage-guide)
5. [Rockbox Workflows](#rockbox-workflows)
6. [Configuration](#configuration)
7. [Project Structure](#project-structure)
8. [Development](#development)
9. [Troubleshooting](#troubleshooting)

## Overview
- SQLite-backed music library with track metadata, playlists, and play counts.
- Terminal UI (TUI) for fast library searches, queueing, and playback.
- Tk desktop app that focuses on Rockbox export and bundling helpers.
- Uses `pygame` for playback with graceful fallbacks when audio backends are missing.

## Feature Highlights
- Scan folders of MP3, FLAC, WAV, or OGG files into a persistent database under `~/.ipod_organizer/`.
- View and manage playlists, including creation, editing, and track ordering.
- Play tracks directly or through interactive queues in the TUI.
- Export Rockbox-ready playlists and reorganize libraries into device-friendly layouts.
- Bundle albums and playlists so they can be copied straight to a Rockbox device.

## Quick Start
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Import tracks and launch the terminal UI
python -m ipod_organizer scan /path/to/music
python -m ipod_organizer tui
```

Run `python -m ipod_organizer --help` for global options or `python -m ipod_organizer <command> --help` for command-specific flags.

## Usage Guide
### Core CLI Commands
- `scan <path>`: Walk a filesystem path and add audio files to the library.
- `list-tracks`: Show tracks with optional filters (artist, album, playlist).
- `list-playlists`: Display playlists and their contents.
- `create-playlist <name>` / `add-to-playlist <playlist> <track>`: Manage playlists from the CLI.
- `play <track-id or search>`: Play a track immediately via the playback engine.
- `tui`: Launch the interactive terminal interface.
- `gui`: Launch the Tk desktop interface with Rockbox utilities and quick actions.

### Terminal UI (TUI)
The TUI provides fast keyboard-driven access to searching, queue management, and playback control. Launch it with:
```bash
python -m ipod_organizer tui
```

### Desktop UI (GUI)
The GUI focuses on export helpers, bundling albums/playlists, and monitoring queue state. Start it with:
```bash
python -m ipod_organizer gui
```

## Rockbox Workflows
Rockbox helpers live under the `rockbox` CLI namespace and in the GUI Rockbox tab.

### Export Playlists
```bash
python -m ipod_organizer export-rockbox /path/to/music \
    --recursive \
    --destination /path/to/playlists \
    --extensions .flac,.mp3
```
- Writes `.m3u` playlists per folder, mirroring folder structure when `--recursive` is used.
- Omitting `--destination` writes playlists alongside the source audio.

### Organize Library
```bash
python -m ipod_organizer organize-rockbox /source /rockbox/music \
    --include-genre \
    --move
```
- Defaults to copying audio into `Artist/Album` folders; `--include-genre` adds a genre level.
- Pass `--move` to relocate audio instead of copying.

### Bundle Albums & Playlists
```bash
python -m ipod_organizer bundle-rockbox \
    --albums /path/to/albums \
    --playlists /path/to/playlists \
    /path/to/output
```
- Produces `Music/` and `Playlists/` directories ready for drag-and-drop.
- Reuses album tracks referenced by playlists, copying only missing files.
- Add `--move-albums` or `--move-playlists` to relocate instead of copy.

## Configuration
- Application data lives under `~/.ipod_organizer/` (see `ipod_organizer/config.py`).
- Key files: `library.db` (SQLite library), `config.json` (optional overrides), `logs/`.
- Adjust logging by setting the `IPOD_ORGANIZER_LOG_LEVEL` environment variable or editing `config.json`.

## Project Structure
```
ipod_organizer/
├── __main__.py       # Enables `python -m ipod_organizer`
├── cli.py            # Click-based CLI entrypoints
├── config.py         # Application constants and directories
├── database.py       # SQLite wrapper and schema helpers
├── library.py        # Track import, scanning, and playlist orchestration
├── playback.py       # pygame playback loop with fallbacks
├── gui.py            # Tk desktop interface
└── rockbox.py        # Rockbox export and bundling utilities
tests/
└── test_*.py         # Pytest suites mirroring module names
```

## Development
```bash
pip install -r requirements-dev.txt
pytest --maxfail=1
```
- Follow PEP 8 and prefer `lower_snake_case` function/variable names.
- Add type hints and dataclasses where appropriate (see `library.Track`).
- Extend tests under `tests/test_<module>.py`, modeling state with fixtures like `tmp_path`.
- Run `pytest` before submitting changes; include coverage for new code paths.

## Troubleshooting
- Playback requires `pygame` and an audio backend (SDL mixer). Install platform packages if playback is silent.
- On Linux, install `python3-tk` if launching `gui` raises a Tk dependency error.
- Delete `~/.ipod_organizer/library.db` if you need to reset the library (metadata will be rebuilt on the next scan).
- For verbose logging, run commands with `IPOD_ORGANIZER_LOG_LEVEL=DEBUG`.
