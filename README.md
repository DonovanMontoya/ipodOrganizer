# iPod Organizer

A small Python music player and organizer. It scans folders for audio files, keeps a searchable library, builds playlists, and plays songs with a minimal terminal interface.

## Features
- Organize tracks into a lightweight SQLite library with playlists and play counts.
- Import MP3/FLAC/WAV/OGG files from any folder.
- Play music with `pygame` (falls back safely if audio support is missing).
- Terminal user interface for searching the library, queueing songs, and controlling playback.
- Configurable persistent library stored in `~/.ipod_organizer/`.

## Getting Started
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m ipod_organizer scan /path/to/music
python -m ipod_organizer tui
```

## CLI Commands
- `scan`: walk a directory and add audio files to the library.
- `list-tracks`: show tracks with optional filtering.
- `list-playlists`: enumerate playlists and contents.
- `create-playlist`, `add-to-playlist`: manage playlists.
- `play`: play a track directly from the library.
- `tui`: launch the interactive terminal UI for queueing and playback control.
- `gui`: open the desktop interface focused on Rockbox exporting and bundling utilities.
- `export-rockbox`: generate `.m3u` playlists (one per folder) ready for copying onto Rockbox devices.
- `organize-rockbox`: copy or move audio into `Artist/Album` (optionally `Genre/Artist/Album`) folders.
- `bundle-rockbox`: stage albums and playlist downloads into `Music/` + `Playlists/` so you can drag them straight onto a Rockbox device.

Run `python -m ipod_organizer --help` to review all options, or launch the GUI directly:
```bash
python -m ipod_organizer gui
```

### Rockbox Playlist Export
```
python -m ipod_organizer export-rockbox /path/to/flacs --recursive --destination /path/to/playlists
```
- Without `--destination`, playlists are written beside the music.
- Use `--recursive` to mirror subdirectories, producing one playlist per folder.
- Override which files are included with `--extensions .flac,.mp3`.

### Rockbox Library Sorting
```
python -m ipod_organizer organize-rockbox /path/to/flacs /path/to/rockbox/music --include-genre --move
```
- Defaults to copying; pass `--move` to relocate files once sorted.
- Add `--include-genre` for a `Genre/Artist/Album` hierarchy.

### Rockbox Bundling
Use the Rockbox tab in the GUI (Bundle card) or run:
```
python -m ipod_organizer bundle-rockbox --albums /path/to/albums --playlists /path/to/playlists /path/to/output
```
- Produces `Music/` and `Playlists/` folders you can drag directly onto the device.
- Reuses album tracks when playlists reference them, copying only what is missing.
- Add `--move-albums` or `--move-playlists` to relocate files instead of copying.

## Development
```bash
pip install -r requirements-dev.txt
pytest
```

## Notes
- Audio playback relies on `pygame`. Install a backend (e.g., SDL mixer) if required on your platform.
- The library file lives under `~/.ipod_organizer/library.db`. Delete it to start fresh.
- The GUI uses Tk (ships with standard Python). Install the `python3-tk` package on Linux if it's missing.
