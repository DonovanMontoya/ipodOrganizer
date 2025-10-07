from pathlib import Path

from ipod_organizer.database import LibraryDatabase
from ipod_organizer.library import MusicLibrary


def make_library(tmp_path: Path) -> MusicLibrary:
    db_path = tmp_path / "library.db"
    database = LibraryDatabase(db_path=db_path)
    return MusicLibrary(db=database)


def test_add_and_list_tracks(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    track_path = music_dir / "song.mp3"
    track_path.write_bytes(b"fake")

    library = make_library(tmp_path)
    library.scan_directory(music_dir)
    tracks = library.list_tracks()

    assert len(tracks) == 1
    added = tracks[0]
    assert added.title == "song"
    assert added.path == track_path.resolve()


def test_playlist_roundtrip(tmp_path):
    music_dir = tmp_path / "music"
    music_dir.mkdir()
    first = music_dir / "first.mp3"
    first.write_bytes(b"a")
    second = music_dir / "second.mp3"
    second.write_bytes(b"b")

    library = make_library(tmp_path)
    library.scan_directory(music_dir)
    tracks = {t.title: t for t in library.list_tracks()}

    library.create_playlist("Favorites")
    library.add_to_playlist("Favorites", tracks["first"].id)
    library.add_to_playlist("Favorites", tracks["second"].id)

    playlists = dict(library.list_playlists())
    assert "Favorites" in playlists
    assert [t.title for t in playlists["Favorites"]] == ["first", "second"]
