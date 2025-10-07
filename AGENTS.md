# Repository Guidelines

## Project Structure & Module Organization
The core package lives under `ipod_organizer/`. `cli.py` wires the command-line interface, `__main__.py` enables `python -m ipod_organizer`, `library.py` orchestrates track import, `database.py` wraps the SQLite layer, `playback.py` houses the pygame playback loop, `gui.py` provides the Tk UI, and `rockbox.py` handles export helpers. Shared configuration constants sit in `config.py`, including the data directory (`~/.ipod_organizer`). Tests reside in `tests/` with module-focused suites such as `test_library.py` and `test_rockbox.py`.

## Build, Test & Run
Work inside a virtual environment. Install runtime dependencies with `pip install -r requirements.txt`; add dev-only tools with `pip install -r requirements-dev.txt`. Scan music folders via `python -m ipod_organizer scan <path>`, launch the terminal UI with `python -m ipod_organizer tui`, and open the desktop UI using `python -m ipod_organizer gui`. Execute the suite with `pytest`, or narrow the scope (e.g., `pytest tests/test_library.py::test_scan_directory`).

## Coding Style & Naming Conventions
Follow PEP 8 with four-space indentation and descriptive `lower_snake_case` names for functions and variables. Prefer dataclasses and type hints as shown by `library.Track`, and keep filesystem values as `Path` objects. Centralize logging through module-level `logger = logging.getLogger(__name__)`, and keep side effects inside functions or class methods. CLI subcommands read as verbs (`scan`, `tui`, `export-rockbox`); match that pattern when adding new commands.

## Testing Guidelines
Extend pytest coverage by mirroring module names (`tests/test_<module>.py`). New features must include unit coverage, guarding edge cases such as missing metadata or unavailable audio backends. Use fixtures (`tmp_path`, monkeypatching) to model library state without touching real media. Before sharing changes, run `pytest --maxfail=1` to catch regressions quickly.

## Commit & Pull Request Guidelines
Keep commit subjects short, imperative, and capitalized (“Add playlist sorting”); add a concise body explaining motivation when changes are non-trivial. Squash noisy WIP commits before opening a pull request. PRs should describe the feature or fix, reference any issue IDs, summarize test evidence (`pytest` output or manual CLI steps), and include screenshots or terminal captures when UI behavior (`gui` or `tui`) changes.

## Configuration & Safety Tips
The app stores state under `~/.ipod_organizer/` (see `config.APP_DIR`). Avoid checking in personal library paths; rely on fixtures and temporary directories when new tests require sample files. When touching playback or export code, guard optional dependencies (`mutagen`, `pygame`) with graceful fallbacks so headless environments continue to function.
