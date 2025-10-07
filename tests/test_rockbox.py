from pathlib import Path

from unittest.mock import patch

from ipod_organizer.rockbox import bundle_for_rockbox, export_m3u_playlists, organize_music_collection


def _write_audio(path: Path) -> None:
    path.write_bytes(b"fake audio")


def test_export_single_playlist(tmp_path):
    music_dir = tmp_path / "flacs"
    music_dir.mkdir()
    track_a = music_dir / "01-song.flac"
    track_b = music_dir / "02-song.flac"
    _write_audio(track_a)
    _write_audio(track_b)

    results = export_m3u_playlists(music_dir)

    assert len(results) == 1
    playlist_path = results[0].playlist_path
    content = playlist_path.read_text(encoding="utf-8").splitlines()
    assert content[0] == "#EXTM3U"
    assert content[1:] == ["01-song.flac", "02-song.flac"]


def test_export_recursive_with_destination(tmp_path):
    source = tmp_path / "collection"
    source.mkdir()
    album = source / "Album"
    album.mkdir()
    single = source / "single.flac"
    album_track = album / "track.flac"
    _write_audio(single)
    _write_audio(album_track)

    destination = tmp_path / "playlists"
    results = export_m3u_playlists(source, destination=destination, recursive=True)

    created = {res.playlist_path.relative_to(destination): res.track_count for res in results}
    assert created == {
        Path("collection.m3u"): 1,
        Path("Album/Album.m3u"): 1,
    }

    root_playlist = destination / "collection.m3u"
    root_lines = root_playlist.read_text(encoding="utf-8").splitlines()
    assert root_lines[1] == "../collection/single.flac"

    playlist = destination / "Album" / "Album.m3u"
    paths = playlist.read_text(encoding="utf-8").splitlines()
    assert paths[1] == "../../collection/Album/track.flac"


@patch("ipod_organizer.rockbox._read_tags")
def test_organize_music_copies_files(mock_tags, tmp_path):
    source = tmp_path / "unsorted"
    source.mkdir()
    track = source / "track.flac"
    track.write_bytes(b"audio")

    destination = tmp_path / "sorted"

    mock_tags.return_value = {
        "artist": "AC/DC",
        "album": "Back In Black",
        "title": "Hells Bells",
        "track_number": "1",
        "genre": "Rock",
    }

    results = organize_music_collection(source, destination, include_genre=True, move=False, recursive=False)

    assert len(results) == 1
    result = results[0]
    assert result.destination
    assert result.destination.parent == destination / "Rock" / "AC DC" / "Back In Black"
    assert result.destination.name.startswith("01 - Hells Bells")
    assert track.exists()  # copy keeps original


@patch("ipod_organizer.rockbox._read_tags")
def test_organize_music_moves_and_handles_duplicates(mock_tags, tmp_path):
    source = tmp_path / "unsorted"
    source.mkdir()
    first = source / "track1.flac"
    second = source / "track2.flac"
    first.write_bytes(b"audio1")
    second.write_bytes(b"audio2")

    destination = tmp_path / "sorted"

    def fake_tags(path: Path):
        return {
            "artist": "Miles Davis",
            "album": "Kind of Blue",
            "title": "So What",
            "track_number": "1",
            "genre": "Jazz",
        }

    mock_tags.side_effect = fake_tags

    results = organize_music_collection(source, destination, move=True, include_genre=False)

    assert len(results) == 2
    moved = [r for r in results if r.action == "moved"]
    assert len(moved) == 2
    for r in moved:
        assert r.destination
        assert r.destination.parent == destination / "Miles Davis" / "Kind of Blue"
    names = sorted(p.destination.name for p in moved if p.destination)
    assert names[0] != names[1]
    assert not first.exists()
    assert not second.exists()


@patch("ipod_organizer.rockbox._read_tags")
def test_organize_music_sanitizes_problematic_tags(mock_tags, tmp_path):
    source = tmp_path / "untidy"
    source.mkdir()
    track = source / "track.flac"
    track.write_bytes(b"audio")

    destination = tmp_path / "tidy"

    mock_tags.return_value = {
        "artist": "\x03Taylor Swift",
        "album": "???????",
        "title": "?love?story",
        "track_number": "?",
        "genre": None,
    }

    results = organize_music_collection(source, destination, include_genre=False, move=False, recursive=False)

    assert len(results) == 1
    result = results[0]
    assert result.destination
    assert result.destination.parent == destination / "Taylor Swift" / "Unknown"
    assert result.destination.name.startswith("00 - love story")


@patch("ipod_organizer.rockbox._read_tags")
def test_organize_music_uses_filename_track_number(mock_tags, tmp_path):
    source = tmp_path / "unsorted"
    source.mkdir()
    track = source / "03 - Mystery Song.flac"
    track.write_bytes(b"audio")

    destination = tmp_path / "sorted"

    mock_tags.return_value = {
        "artist": "Unknown Artist",
        "album": "Mysteries",
        "title": "Mystery Song",
        "track_number": None,
        "genre": None,
    }

    results = organize_music_collection(source, destination, include_genre=False, move=False, recursive=False)

    assert len(results) == 1
    result = results[0]
    assert result.destination
    assert result.destination.name.startswith("03 - Mystery Song")


@patch("ipod_organizer.rockbox._read_tags")
def test_organize_music_uses_primary_artist(mock_tags, tmp_path):
    source = tmp_path / "unsorted"
    source.mkdir()
    track = source / "track.flac"
    track.write_bytes(b"audio")

    destination = tmp_path / "sorted"

    mock_tags.return_value = {
        "artist": "Taylor Swift & Ice Spice",
        "album": "Midnights",
        "title": "Karma",
        "track_number": "13",
        "genre": None,
    }

    results = organize_music_collection(source, destination, include_genre=False, move=False, recursive=False)

    assert len(results) == 1
    result = results[0]
    assert result.destination
    assert result.destination.parent == destination / "Taylor Swift" / "Midnights"
    assert result.destination.name.startswith("13 - Karma")


@patch("ipod_organizer.rockbox._read_tags")
def test_bundle_for_rockbox_combines_albums_and_playlists(mock_tags, tmp_path):
    albums_root = tmp_path / "albums"
    albums_root.mkdir()
    album_dir = albums_root / "Midnights"
    album_dir.mkdir()
    album_track = album_dir / "Lavender Haze.flac"
    album_track.write_bytes(b"album")

    playlists_root = tmp_path / "playlists"
    playlists_root.mkdir()
    playlist_dir = playlists_root / "Favorites"
    playlist_dir.mkdir()
    playlist_copy = playlist_dir / "Lavender Haze.flac"
    playlist_copy.write_bytes(b"playlist")
    playlist_single = playlist_dir / "Low.flac"
    playlist_single.write_bytes(b"single")

    dest = tmp_path / "bundle"

    tag_map = {
        album_track: {
            "artist": "Taylor Swift",
            "album": "Midnights",
            "title": "Lavender Haze",
            "track_number": "1",
            "genre": "Pop",
        },
        playlist_copy: {
            "artist": "Taylor Swift",
            "album": "Midnights",
            "title": "Lavender Haze",
            "track_number": "1",
            "genre": "Pop",
        },
        playlist_single: {
            "artist": "SZA",
            "album": "SOS",
            "title": "Low",
            "track_number": None,
            "genre": "R&B",
        },
    }

    def _fake_tags(path: Path):
        return tag_map[path]

    mock_tags.side_effect = _fake_tags

    progress_updates = []

    def _progress(done, total, message):
        progress_updates.append((done, total, message))

    result = bundle_for_rockbox([albums_root], [playlists_root], dest, progress_callback=_progress)

    music_dir = dest / "Music"
    playlists_dir = dest / "Playlists"

    album_dest = music_dir / "Taylor Swift" / "Midnights" / "01 - Lavender Haze.flac"
    assert album_dest.exists()
    # Unique playlist track should also be organized once.
    single_dest = music_dir / "SZA" / "SOS" / "00 - Low.flac"
    assert single_dest.exists()

    playlist_file = playlists_dir / "Favorites.m3u"
    assert playlist_file.exists()
    lines = playlist_file.read_text(encoding="utf-8").splitlines()
    assert lines[0] == "#EXTM3U"
    assert lines[1:] == [
        "../Music/Taylor Swift/Midnights/01 - Lavender Haze.flac",
        "../Music/SZA/SOS/00 - Low.flac",
    ]

    assert result.playlist_results[0].missing_sources == []
    assert progress_updates[0][0] == 0
    assert progress_updates[-1][0] == progress_updates[-1][1]
    assert progress_updates[-1][2] == "Rockbox bundle complete"
