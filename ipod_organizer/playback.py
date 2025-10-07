"""Playback controller built on pygame with a silent fallback."""

from __future__ import annotations

import logging
import random
import threading
import time
from collections import deque
from pathlib import Path
from typing import Callable, Deque, Literal, Optional

from .library import Track

try:
    import pygame
except ImportError:  # pragma: no cover - optional dependency
    pygame = None

logger = logging.getLogger(__name__)

RepeatMode = Literal["off", "one", "all"]


class PlaybackUnavailableError(RuntimeError):
    """Raised when no playback backend is available."""


class _BaseBackend:
    def play(self, source: Path) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def stop(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def pause(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def resume(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError

    def is_busy(self) -> bool:  # pragma: no cover - abstract
        raise NotImplementedError

    def get_position(self) -> float:  # pragma: no cover - abstract
        """Get current playback position in seconds."""
        raise NotImplementedError

    def set_volume(self, volume: float) -> None:  # pragma: no cover - abstract
        """Set volume (0.0 to 1.0)."""
        raise NotImplementedError

    def shutdown(self) -> None:  # pragma: no cover - abstract
        raise NotImplementedError


class _SilentBackend(_BaseBackend):
    """No-op backend; useful when pygame is not installed."""

    def play(self, source: Path) -> None:
        logger.warning("Audio backend unavailable. Would play: %s", source)

    def stop(self) -> None:
        logger.warning("Audio backend unavailable. Stop ignored.")

    def pause(self) -> None:
        logger.warning("Audio backend unavailable. Pause ignored.")

    def resume(self) -> None:
        logger.warning("Audio backend unavailable. Resume ignored.")

    def is_busy(self) -> bool:
        return False

    def get_position(self) -> float:
        return 0.0

    def set_volume(self, volume: float) -> None:
        logger.warning("Audio backend unavailable. Volume change ignored.")

    def shutdown(self) -> None:
        logger.info("Audio backend unavailable. Shutdown noop.")


class _PygameBackend(_BaseBackend):
    def __init__(self):
        if not pygame:
            raise PlaybackUnavailableError("pygame is not installed")
        try:
            pygame.mixer.init()
        except Exception as exc:  # pragma: no cover - hardware dependent
            raise PlaybackUnavailableError(str(exc)) from exc

    def play(self, source: Path) -> None:
        pygame.mixer.music.load(str(source))
        pygame.mixer.music.play()

    def stop(self) -> None:
        pygame.mixer.music.stop()

    def pause(self) -> None:
        pygame.mixer.music.pause()

    def resume(self) -> None:
        pygame.mixer.music.unpause()

    def is_busy(self) -> bool:
        return pygame.mixer.music.get_busy()

    def get_position(self) -> float:
        """Return current position in seconds."""
        return pygame.mixer.music.get_pos() / 1000.0

    def set_volume(self, volume: float) -> None:
        """Set volume (0.0 to 1.0)."""
        pygame.mixer.music.set_volume(max(0.0, min(1.0, volume)))

    def shutdown(self) -> None:
        pygame.mixer.music.stop()
        pygame.mixer.quit()


class MusicPlayer:
    """Manage a playback queue with simple controls."""

    def __init__(
        self,
        allow_silent: bool = True,
        on_track_start: Optional[Callable[[Track], None]] = None,
    ):
        self._queue: Deque[Track] = deque()
        self._current: Optional[Track] = None
        self._status: str = "stopped"
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._on_track_start = on_track_start
        self._shuffle: bool = False
        self._repeat: RepeatMode = "off"
        self._volume: float = 0.7

        try:
            self._backend: _BaseBackend = _PygameBackend()
            logger.info("Using pygame backend for audio.")
        except PlaybackUnavailableError as exc:
            if not allow_silent:
                raise
            logger.warning("Falling back to silent backend: %s", exc)
            self._backend = _SilentBackend()

        self._silent_backend = isinstance(self._backend, _SilentBackend)
        self._backend.set_volume(self._volume)
        self._monitor_thread.start()

    @property
    def current_track(self) -> Optional[Track]:
        return self._current

    @property
    def status(self) -> str:
        return self._status

    @property
    def shuffle(self) -> bool:
        return self._shuffle

    @shuffle.setter
    def shuffle(self, value: bool) -> None:
        with self._lock:
            self._shuffle = value

    @property
    def repeat(self) -> RepeatMode:
        return self._repeat

    @repeat.setter
    def repeat(self, mode: RepeatMode) -> None:
        with self._lock:
            self._repeat = mode

    @property
    def volume(self) -> float:
        return self._volume

    @volume.setter
    def volume(self, value: float) -> None:
        with self._lock:
            self._volume = max(0.0, min(1.0, value))
            self._backend.set_volume(self._volume)

    def queue_snapshot(self) -> list[Track]:
        """Return a copy of the pending queue."""
        with self._lock:
            return list(self._queue)

    @property
    def has_audio_output(self) -> bool:
        """True when an audio backend is available."""
        return not self._silent_backend

    def get_playback_position(self) -> float:
        """Get current playback position in seconds."""
        with self._lock:
            if self._current and self._status == "playing":
                return self._backend.get_position()
            return 0.0

    def play_now(self, track: Track) -> None:
        """Play a track immediately, clearing the current queue."""
        with self._lock:
            self._queue.clear()
            self._start_track(track)

    def queue_track(self, track: Track) -> None:
        """Append a track to the playback queue."""
        with self._lock:
            self._queue.append(track)
            logger.debug("Queued %s", track.title)

    def queue_tracks(self, tracks: list[Track]) -> None:
        """Append multiple tracks to the playback queue."""
        with self._lock:
            self._queue.extend(tracks)
            logger.debug("Queued %d tracks", len(tracks))

    def remove_from_queue(self, index: int) -> None:
        """Remove a track from the queue by index."""
        with self._lock:
            if 0 <= index < len(self._queue):
                removed = list(self._queue)[index]
                temp_queue = list(self._queue)
                temp_queue.pop(index)
                self._queue.clear()
                self._queue.extend(temp_queue)
                logger.debug("Removed %s from queue", removed.title)

    def skip(self) -> None:
        """Skip the current track."""
        with self._lock:
            self._backend.stop()
            self._status = "stopped"
            self._current = None

    def pause(self) -> None:
        with self._lock:
            self._backend.pause()
            self._status = "paused"

    def resume(self) -> None:
        with self._lock:
            self._backend.resume()
            self._status = "playing"

    def stop(self) -> None:
        with self._lock:
            self._queue.clear()
            self._backend.stop()
            self._status = "stopped"
            self._current = None

    def shutdown(self) -> None:
        self._stop_event.set()
        self._monitor_thread.join(timeout=1)
        with self._lock:
            self._backend.shutdown()

    def _start_track(self, track: Track) -> None:
        self._current = track
        try:
            self._backend.play(track.path)
            self._status = "playing"
            logger.info("Now playing: %s", track.title)
            if self._on_track_start:
                try:
                    self._on_track_start(track)
                except Exception:  # pragma: no cover - callback safety
                    logger.exception("Track start callback failed.")
        except Exception as exc:  # pragma: no cover - playback errors
            logger.exception("Failed to play %s: %s", track.path, exc)
            self._current = None
            self._status = "error"

    def _monitor_loop(self) -> None:
        while not self._stop_event.is_set():
            with self._lock:
                busy = self._backend.is_busy()
                if not busy:
                    next_track = None

                    # Handle repeat mode
                    if self._current and self._repeat == "one":
                        next_track = self._current
                    elif self._queue:
                        if self._shuffle:
                            # Pick random track from queue
                            queue_list = list(self._queue)
                            next_track = random.choice(queue_list)
                            queue_list.remove(next_track)
                            self._queue.clear()
                            self._queue.extend(queue_list)
                        else:
                            next_track = self._queue.popleft()
                    elif self._current and self._repeat == "all":
                        # No more tracks in queue, but repeat all is on
                        # Just replay the current track (in real app, would need full playlist)
                        next_track = self._current

                    if next_track:
                        self._start_track(next_track)
                    elif self._current is not None:
                        # Playback finished naturally.
                        self._current = None
                        if self._status == "playing":
                            self._status = "stopped"
            time.sleep(0.25)
