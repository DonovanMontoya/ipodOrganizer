"""Modern PyQt6-based GUI for iPod Organizer with Apple-inspired design."""

from __future__ import annotations

import threading
from pathlib import Path
from typing import Optional

try:
    from PyQt6.QtWidgets import (
        QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
        QLabel, QPushButton, QLineEdit, QListWidget, QTreeWidget, QTreeWidgetItem,
        QSlider, QProgressBar, QCheckBox, QTabWidget, QFileDialog,
        QMessageBox, QInputDialog, QMenu, QSplitter, QTextEdit, QFrame,
        QScrollArea, QSizePolicy, QGraphicsOpacityEffect
    )
    from PyQt6.QtCore import (
        Qt, QTimer, QPropertyAnimation, QEasingCurve, pyqtSignal,
        QSize, QPoint, QRect, pyqtProperty, QParallelAnimationGroup, QSequentialAnimationGroup
    )
    from PyQt6.QtGui import QFont, QIcon, QPalette, QColor, QCursor, QAction
except ImportError as exc:  # pragma: no cover
    raise RuntimeError("PyQt6 is required for the GUI but not available. Install with: pip install PyQt6") from exc

from .library import MusicLibrary, Track
from .rockbox import ExportResult, export_m3u_playlists, organize_music_collection


# Apple-inspired color palette
class Colors:
    """macOS-inspired color scheme with light and dark mode support."""
    # Light mode (default)
    BACKGROUND = "#FFFFFF"
    SURFACE = "#F5F5F7"
    SURFACE_ELEVATED = "#FBFBFD"
    BORDER = "#D2D2D7"
    TEXT_PRIMARY = "#1D1D1F"
    TEXT_SECONDARY = "#6E6E73"
    TEXT_TERTIARY = "#86868B"
    ACCENT = "#007AFF"  # Apple Blue
    ACCENT_HOVER = "#0051D5"
    SUCCESS = "#34C759"
    WARNING = "#FF9500"
    ERROR = "#FF3B30"
    SEPARATOR = "#E5E5E5"

    # Dark mode colors (will be used based on system preference)
    DARK_BACKGROUND = "#000000"
    DARK_SURFACE = "#1C1C1E"
    DARK_SURFACE_ELEVATED = "#2C2C2E"
    DARK_BORDER = "#38383A"
    DARK_TEXT_PRIMARY = "#FFFFFF"
    DARK_TEXT_SECONDARY = "#98989D"
    DARK_TEXT_TERTIARY = "#636366"


# Global stylesheet with Apple-inspired design
STYLESHEET = f"""
QMainWindow {{
    background-color: {Colors.BACKGROUND};
}}

QWidget {{
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "SF Pro Text", sans-serif;
    font-size: 13px;
    color: {Colors.TEXT_PRIMARY};
}}

/* Cards and surfaces */
.Card {{
    background-color: {Colors.SURFACE};
    border-radius: 12px;
    padding: 16px;
}}

.CardElevated {{
    background-color: {Colors.SURFACE_ELEVATED};
    border-radius: 12px;
    border: 1px solid {Colors.BORDER};
}}

/* Buttons */
QPushButton {{
    background-color: {Colors.SURFACE};
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 16px;
    color: {Colors.TEXT_PRIMARY};
    font-weight: 500;
}}

QPushButton:hover {{
    background-color: {Colors.SURFACE_ELEVATED};
    border-color: {Colors.TEXT_TERTIARY};
}}

QPushButton:pressed {{
    background-color: {Colors.BORDER};
}}

QPushButton[primary="true"] {{
    background-color: {Colors.ACCENT};
    color: white;
    border: none;
}}

QPushButton[primary="true"]:hover {{
    background-color: {Colors.ACCENT_HOVER};
}}

QPushButton[primary="true"]:pressed {{
    background-color: #003D99;
}}

/* Line edits */
QLineEdit {{
    background-color: white;
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 8px 12px;
    color: {Colors.TEXT_PRIMARY};
}}

QLineEdit:focus {{
    border-color: {Colors.ACCENT};
    border-width: 2px;
}}

/* List widgets */
QListWidget {{
    background-color: white;
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
    outline: none;
    color: {Colors.TEXT_PRIMARY};
}}

QListWidget::item {{
    border-radius: 6px;
    padding: 10px;
    margin: 2px 0px;
    color: {Colors.TEXT_PRIMARY};
}}

QListWidget::item:selected {{
    background-color: {Colors.ACCENT};
    color: white;
}}

QListWidget::item:hover {{
    background-color: {Colors.SURFACE};
}}

/* Tree widget */
QTreeWidget {{
    background-color: white;
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    outline: none;
    alternate-background-color: {Colors.SURFACE};
    color: {Colors.TEXT_PRIMARY};
}}

QTreeWidget::item {{
    padding: 8px;
    border-radius: 4px;
    color: {Colors.TEXT_PRIMARY};
}}

QTreeWidget::item:selected {{
    background-color: {Colors.ACCENT};
    color: white;
}}

QTreeWidget::item:hover {{
    background-color: {Colors.SURFACE};
}}

QHeaderView::section {{
    background-color: {Colors.SURFACE};
    color: {Colors.TEXT_PRIMARY};
    padding: 8px;
    border: none;
    border-bottom: 2px solid {Colors.BORDER};
    font-weight: 600;
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}}

/* Sliders */
QSlider::groove:horizontal {{
    border: none;
    height: 4px;
    background: {Colors.BORDER};
    border-radius: 2px;
}}

QSlider::handle:horizontal {{
    background: white;
    border: 1px solid {Colors.BORDER};
    width: 16px;
    height: 16px;
    margin: -7px 0;
    border-radius: 8px;
}}

QSlider::handle:horizontal:hover {{
    background: {Colors.SURFACE_ELEVATED};
    border-width: 2px;
}}

QSlider::sub-page:horizontal {{
    background: {Colors.ACCENT};
    border-radius: 2px;
}}

/* Progress bar */
QProgressBar {{
    border: none;
    border-radius: 3px;
    background-color: {Colors.BORDER};
    height: 6px;
    text-align: center;
}}

QProgressBar::chunk {{
    background-color: {Colors.ACCENT};
    border-radius: 3px;
}}

/* Checkboxes */
QCheckBox {{
    spacing: 8px;
    color: {Colors.TEXT_PRIMARY};
    font-size: 13px;
}}

QCheckBox::indicator {{
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 2px solid {Colors.BORDER};
    background-color: white;
}}

QCheckBox::indicator:hover {{
    border-color: {Colors.ACCENT};
}}

QCheckBox::indicator:checked {{
    background-color: {Colors.ACCENT};
    border-color: {Colors.ACCENT};
    image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
}}

/* Tab widget */
QTabWidget::pane {{
    border: none;
    background-color: transparent;
}}

QTabBar::tab {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY};
    padding: 10px 20px;
    margin-right: 4px;
    border: none;
    border-bottom: 2px solid transparent;
    font-weight: 500;
}}

QTabBar::tab:selected {{
    color: {Colors.TEXT_PRIMARY};
    border-bottom-color: {Colors.ACCENT};
}}

QTabBar::tab:hover {{
    color: {Colors.TEXT_PRIMARY};
}}

/* Text edit */
QTextEdit {{
    background-color: white;
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 12px;
    color: {Colors.TEXT_PRIMARY};
}}

/* Scrollbars */
QScrollBar:vertical {{
    border: none;
    background: transparent;
    width: 10px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background: {Colors.BORDER};
    min-height: 30px;
    border-radius: 5px;
}}

QScrollBar::handle:vertical:hover {{
    background: {Colors.TEXT_TERTIARY};
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    border: none;
    background: none;
}}

QScrollBar:horizontal {{
    border: none;
    background: transparent;
    height: 10px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background: {Colors.BORDER};
    min-width: 30px;
    border-radius: 5px;
}}

QScrollBar::handle:horizontal:hover {{
    background: {Colors.TEXT_TERTIARY};
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    border: none;
    background: none;
}}

/* Menu */
QMenu {{
    background-color: white;
    border: 1px solid {Colors.BORDER};
    border-radius: 8px;
    padding: 4px;
    color: {Colors.TEXT_PRIMARY};
}}

QMenu::item {{
    padding: 8px 24px 8px 12px;
    border-radius: 4px;
    color: {Colors.TEXT_PRIMARY};
}}

QMenu::item:selected {{
    background-color: {Colors.ACCENT};
    color: white;
}}

QMenu::separator {{
    height: 1px;
    background: {Colors.SEPARATOR};
    margin: 4px 8px;
}}

/* Splitter */
QSplitter::handle {{
    background-color: {Colors.SEPARATOR};
}}

QSplitter::handle:horizontal {{
    width: 1px;
}}

QSplitter::handle:vertical {{
    height: 1px;
}}
"""


class Toast(QFrame):
    """Beautiful toast notification with smooth animations."""

    def __init__(self, message: str, toast_type: str = "info", parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool | Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Style based on type
        colors = {
            "success": (Colors.SUCCESS, "white"),
            "error": (Colors.ERROR, "white"),
            "warning": (Colors.WARNING, "white"),
            "info": (Colors.ACCENT, "white"),
        }
        bg_color, text_color = colors.get(toast_type, colors["info"])

        icons = {
            "success": "✓",
            "error": "✗",
            "warning": "⚠",
            "info": "ⓘ",
        }
        icon = icons.get(toast_type, icons["info"])

        self.setStyleSheet(f"""
            Toast {{
                background-color: {bg_color};
                border-radius: 12px;
                padding: 16px 24px;
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 12, 20, 12)
        layout.setSpacing(12)

        # Icon
        icon_label = QLabel(icon)
        icon_label.setStyleSheet(f"color: {text_color}; font-size: 18px; font-weight: bold;")

        # Message
        message_label = QLabel(message)
        message_label.setStyleSheet(f"color: {text_color}; font-size: 14px; font-weight: 500;")
        message_label.setWordWrap(False)

        layout.addWidget(icon_label)
        layout.addWidget(message_label)

        # Setup animations
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        # Slide in animation
        self.slide_anim = QPropertyAnimation(self, b"pos")
        self.slide_anim.setDuration(300)
        self.slide_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        # Fade in animation
        self.fade_in_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in_anim.setDuration(300)
        self.fade_in_anim.setStartValue(0.0)
        self.fade_in_anim.setEndValue(1.0)

        # Fade out animation
        self.fade_out_anim = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out_anim.setDuration(300)
        self.fade_out_anim.setStartValue(1.0)
        self.fade_out_anim.setEndValue(0.0)
        self.fade_out_anim.finished.connect(self.close)

        # Auto-dismiss timer
        self.dismiss_timer = QTimer(self)
        self.dismiss_timer.timeout.connect(self.dismiss)
        self.dismiss_timer.setSingleShot(True)

    def show_toast(self, parent_widget: QWidget, duration: int = 3000):
        """Show the toast notification."""
        self.setParent(parent_widget)

        # Calculate position (top center)
        parent_rect = parent_widget.rect()
        self.adjustSize()
        start_x = (parent_rect.width() - self.width()) // 2
        start_y = -self.height()
        end_y = 20

        self.move(start_x, start_y)
        self.show()

        # Animate slide in
        self.slide_anim.setStartValue(QPoint(start_x, start_y))
        self.slide_anim.setEndValue(QPoint(start_x, end_y))

        # Start animations
        self.fade_in_anim.start()
        self.slide_anim.start()

        # Auto dismiss
        self.dismiss_timer.start(duration)

    def dismiss(self):
        """Dismiss the toast with animation."""
        self.fade_out_anim.start()


class LoadingOverlay(QWidget):
    """Loading overlay with spinner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
        self.setStyleSheet(f"""
            LoadingOverlay {{
                background-color: rgba(0, 0, 0, 0.5);
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Spinner container
        spinner_container = QFrame()
        spinner_container.setMinimumSize(200, 120)
        spinner_container.setStyleSheet(f"""
            QFrame {{
                background-color: white;
                border-radius: 16px;
                padding: 20px;
            }}
        """)

        spinner_layout = QVBoxLayout(spinner_container)
        spinner_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        spinner_layout.setSpacing(12)

        # Progress indicator
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)  # Indeterminate
        self.progress.setTextVisible(False)
        self.progress.setFixedWidth(150)
        self.progress.setFixedHeight(6)

        self.label = QLabel("Loading...")
        self.label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY}; font-weight: 500; font-size: 14px;")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.label.setWordWrap(True)

        spinner_layout.addWidget(self.progress)
        spinner_layout.addWidget(self.label)

        layout.addWidget(spinner_container)

        # Fade animation
        self.opacity_effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.opacity_effect)

        self.fade_in = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_in.setDuration(200)
        self.fade_in.setStartValue(0.0)
        self.fade_in.setEndValue(1.0)

        self.fade_out = QPropertyAnimation(self.opacity_effect, b"opacity")
        self.fade_out.setDuration(200)
        self.fade_out.setStartValue(1.0)
        self.fade_out.setEndValue(0.0)
        self.fade_out.finished.connect(self.hide)

        self.hide()

    def show_loading(self, message: str = "Loading...", determinate: bool = False):
        """Show the loading overlay."""
        self.label.setText(message)

        # Set progress bar mode
        if determinate:
            self.progress.setRange(0, 100)
            self.progress.setValue(0)
            self.progress.setTextVisible(True)
            self.progress.setFormat("%p%")
        else:
            self.progress.setRange(0, 0)  # Indeterminate
            self.progress.setTextVisible(False)

        self.setGeometry(self.parent().rect())
        self.show()
        self.fade_in.start()

    def update_progress(self, value: int, message: str = None):
        """Update the progress value (0-100) and optionally the message."""
        self.progress.setValue(value)
        if message:
            self.label.setText(message)

    def hide_loading(self):
        """Hide the loading overlay."""
        self.fade_out.start()


class AnimatedButton(QPushButton):
    """Button with press animation."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._original_size = None

    def mousePressEvent(self, event):
        """Add press animation."""
        if not self._original_size:
            self._original_size = self.size()

        # Scale down animation
        self.anim = QPropertyAnimation(self, b"size")
        self.anim.setDuration(100)
        self.anim.setStartValue(self._original_size)
        self.anim.setEndValue(QSize(
            int(self._original_size.width() * 0.95),
            int(self._original_size.height() * 0.95)
        ))
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        """Return to normal size."""
        if self._original_size:
            # Scale up animation
            self.anim = QPropertyAnimation(self, b"size")
            self.anim.setDuration(100)
            self.anim.setStartValue(self.size())
            self.anim.setEndValue(self._original_size)
            self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.anim.start()

        super().mouseReleaseEvent(event)


class NowPlayingBar(QWidget):
    """Beautiful now-playing bar with album art, controls, and progress."""

    def __init__(self, player: MusicPlayer, library: MusicLibrary, parent=None):
        super().__init__(parent)
        self.player = player
        self.library = library
        self._setup_ui()

    def _setup_ui(self):
        """Setup the now playing bar UI."""
        self.setFixedHeight(100)
        self.setStyleSheet(f"""
            NowPlayingBar {{
                background-color: {Colors.SURFACE_ELEVATED};
                border-top: 1px solid {Colors.BORDER};
            }}
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)
        layout.setSpacing(20)

        # Track info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(4)

        self.title_label = QLabel("No track playing")
        self.title_label.setFont(QFont("-apple-system", 14, QFont.Weight.DemiBold))

        self.artist_label = QLabel("")
        self.artist_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")

        info_layout.addWidget(self.title_label)
        info_layout.addWidget(self.artist_label)
        info_layout.addStretch()

        layout.addLayout(info_layout, 2)

        # Center controls
        controls_layout = QVBoxLayout()
        controls_layout.setSpacing(8)

        # Playback buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.prev_btn = self._create_icon_button("⏮")
        self.play_pause_btn = self._create_icon_button("▶", primary=True)
        self.next_btn = self._create_icon_button("⏭")

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.prev_btn)
        buttons_layout.addWidget(self.play_pause_btn)
        buttons_layout.addWidget(self.next_btn)
        buttons_layout.addStretch()

        # Progress bar with time labels
        progress_layout = QHBoxLayout()
        progress_layout.setSpacing(8)

        self.time_current = QLabel("0:00")
        self.time_current.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        self.time_current.setFixedWidth(40)

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)

        self.time_total = QLabel("0:00")
        self.time_total.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 11px;")
        self.time_total.setFixedWidth(40)
        self.time_total.setAlignment(Qt.AlignmentFlag.AlignRight)

        progress_layout.addWidget(self.time_current)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.time_total)

        controls_layout.addLayout(buttons_layout)
        controls_layout.addLayout(progress_layout)

        layout.addLayout(controls_layout, 2)

        # Right side controls
        right_layout = QHBoxLayout()
        right_layout.setSpacing(12)

        # Shuffle and repeat
        self.shuffle_btn = self._create_icon_button("🔀", checkable=True)
        self.repeat_btn = self._create_icon_button("🔁", checkable=True)

        # Volume control
        volume_layout = QVBoxLayout()
        volume_layout.setSpacing(4)

        volume_label = QLabel("🔊")
        volume_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(int(self.player.volume * 100))
        self.volume_slider.setFixedWidth(100)

        volume_layout.addWidget(volume_label)
        volume_layout.addWidget(self.volume_slider)

        right_layout.addWidget(self.shuffle_btn)
        right_layout.addWidget(self.repeat_btn)
        right_layout.addLayout(volume_layout)

        layout.addLayout(right_layout, 1)

        # Connect signals
        self.play_pause_btn.clicked.connect(self._toggle_playback)
        self.next_btn.clicked.connect(self.player.skip)
        self.shuffle_btn.clicked.connect(self._toggle_shuffle)
        self.repeat_btn.clicked.connect(self._cycle_repeat)
        self.volume_slider.valueChanged.connect(self._on_volume_change)

    def _create_icon_button(self, icon: str, primary: bool = False, checkable: bool = False) -> QPushButton:
        """Create a styled icon button."""
        btn = QPushButton(icon)
        btn.setFixedSize(40, 40)
        btn.setCheckable(checkable)
        if primary:
            btn.setProperty("primary", True)
        btn.setStyleSheet(btn.styleSheet())  # Force style update
        return btn

    def _toggle_playback(self):
        """Toggle between play and pause."""
        if self.player.status == "playing":
            self.player.pause()
            self.play_pause_btn.setText("▶")
        elif self.player.status == "paused":
            self.player.resume()
            self.play_pause_btn.setText("⏸")
        else:
            # Trigger play from parent
            pass

    def _toggle_shuffle(self):
        """Toggle shuffle mode."""
        self.player.shuffle = self.shuffle_btn.isChecked()

    def _cycle_repeat(self):
        """Cycle through repeat modes."""
        current = self.player.repeat
        if current == "off":
            self.player.repeat = "all"
            self.repeat_btn.setText("🔁")
        elif current == "all":
            self.player.repeat = "one"
            self.repeat_btn.setText("🔂")
        else:
            self.player.repeat = "off"
            self.repeat_btn.setText("🔁")
            self.repeat_btn.setChecked(False)

    def _on_volume_change(self, value: int):
        """Handle volume change."""
        self.player.volume = value / 100.0

    def update_display(self):
        """Update the now playing display."""
        current = self.player.current_track
        if current:
            self.title_label.setText(current.title)
            artist = current.artist or "Unknown Artist"
            album = current.album or "Unknown Album"
            self.artist_label.setText(f"{artist} • {album}")

            # Update play/pause button
            if self.player.status == "playing":
                self.play_pause_btn.setText("⏸")
            else:
                self.play_pause_btn.setText("▶")

            # Update progress
            if current.duration:
                position = self.player.get_playback_position()
                progress = int((position / current.duration) * 100)
                self.progress_bar.setValue(progress)
                self.time_current.setText(self._format_time(position))
                self.time_total.setText(self._format_time(current.duration))
        else:
            self.title_label.setText("No track playing")
            self.artist_label.setText("")
            self.play_pause_btn.setText("▶")
            self.progress_bar.setValue(0)
            self.time_current.setText("0:00")
            self.time_total.setText("0:00")

    def _format_time(self, seconds: float) -> str:
        """Format seconds to MM:SS."""
        total = int(round(seconds))
        minutes, secs = divmod(total, 60)
        return f"{minutes}:{secs:02d}"


class LibraryTab(QWidget):
    """Library tab with playlists and tracks."""

    play_track = pyqtSignal(Track)
    queue_tracks = pyqtSignal(list)
    scan_progress = pyqtSignal(int, str)
    scan_finished = pyqtSignal(int, object)

    def __init__(self, library: MusicLibrary, main_window=None, parent=None):
        super().__init__(parent)
        self.library = library
        self.main_window = main_window
        self.tracks_by_id = {}
        self.scan_progress.connect(self._handle_scan_progress)
        self.scan_finished.connect(self._handle_scan_finished)
        self._setup_ui()
        self.load_playlists()
        self.refresh_tracks()

    def _setup_ui(self):
        """Setup the library tab UI."""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Splitter for playlist and tracks
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: Playlists
        playlist_widget = self._create_playlist_panel()
        splitter.addWidget(playlist_widget)

        # Right: Tracks
        tracks_widget = self._create_tracks_panel()
        splitter.addWidget(tracks_widget)

        splitter.setSizes([250, 750])
        layout.addWidget(splitter)

    def _create_playlist_panel(self) -> QWidget:
        """Create the playlist sidebar."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 8, 16)
        layout.setSpacing(12)

        # Header
        header_layout = QHBoxLayout()
        header_label = QLabel("Playlists")
        header_label.setFont(QFont("-apple-system", 16, QFont.Weight.Bold))
        header_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        add_btn = QPushButton("+")
        add_btn.setFixedSize(28, 28)
        add_btn.setStyleSheet(f"font-size: 18px; color: {Colors.TEXT_PRIMARY};")
        add_btn.clicked.connect(self._create_playlist)

        header_layout.addWidget(header_label)
        header_layout.addStretch()
        header_layout.addWidget(add_btn)

        # Playlist list
        self.playlist_list = QListWidget()
        self.playlist_list.currentRowChanged.connect(self._on_playlist_selected)
        self.playlist_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.playlist_list.customContextMenuRequested.connect(self._show_playlist_context_menu)

        layout.addLayout(header_layout)
        layout.addWidget(self.playlist_list)

        return container

    def _create_tracks_panel(self) -> QWidget:
        """Create the tracks panel."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(8, 16, 16, 16)
        layout.setSpacing(12)

        # Search bar
        search_layout = QHBoxLayout()
        search_layout.setSpacing(12)

        search_label = QLabel("🔍")
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search tracks...")
        self.search_input.textChanged.connect(self.refresh_tracks)

        scan_btn = QPushButton("Scan Folder")
        scan_btn.setProperty("primary", True)
        scan_btn.setStyleSheet(scan_btn.styleSheet())
        scan_btn.clicked.connect(self._scan_folder)

        search_layout.addWidget(search_label)
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(scan_btn)

        # Tracks tree
        self.tracks_tree = QTreeWidget()
        self.tracks_tree.setHeaderLabels(["#", "Title", "Artist", "Album", "Duration"])
        self.tracks_tree.setColumnWidth(0, 40)
        self.tracks_tree.setColumnWidth(1, 300)
        self.tracks_tree.setColumnWidth(2, 200)
        self.tracks_tree.setColumnWidth(3, 200)
        self.tracks_tree.setColumnWidth(4, 80)
        self.tracks_tree.setSelectionMode(QTreeWidget.SelectionMode.ExtendedSelection)
        self.tracks_tree.setAlternatingRowColors(True)
        self.tracks_tree.itemDoubleClicked.connect(self._on_track_double_click)
        self.tracks_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tracks_tree.customContextMenuRequested.connect(self._show_track_context_menu)
        self.tracks_tree.header().setSectionsClickable(True)
        self.tracks_tree.header().sectionClicked.connect(self._sort_by_column)

        # Action buttons
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(8)

        play_btn = QPushButton("▶ Play")
        play_btn.setProperty("primary", True)
        play_btn.setStyleSheet(play_btn.styleSheet())
        play_btn.clicked.connect(self._play_selected)

        queue_btn = QPushButton("+ Queue")
        queue_btn.clicked.connect(self._queue_selected)

        playlist_btn = QPushButton("+ Add to Playlist")
        playlist_btn.clicked.connect(self._add_to_playlist)

        buttons_layout.addWidget(play_btn)
        buttons_layout.addWidget(queue_btn)
        buttons_layout.addWidget(playlist_btn)
        buttons_layout.addStretch()

        layout.addLayout(search_layout)
        layout.addWidget(self.tracks_tree)
        layout.addLayout(buttons_layout)

        return container

    def load_playlists(self):
        """Load playlists from library."""
        self.playlist_list.clear()
        self.playlist_list.addItem("📁 All Tracks")

        playlists = self.library.list_playlists()
        for name, _ in playlists:
            self.playlist_list.addItem(f"🎵 {name}")

    def refresh_tracks(self):
        """Refresh the track list."""
        search = self.search_input.text().strip() or None
        tracks = self.library.list_tracks(search)
        self._display_tracks(tracks)

    def _display_tracks(self, tracks: list[Track]):
        """Display tracks in the tree."""
        self.tracks_tree.clear()
        self.tracks_by_id.clear()

        for track in tracks:
            track_id = str(track.id or "")
            self.tracks_by_id[track_id] = track

            # Format track number (remove leading zeros, show empty if none)
            track_num = ""
            if track.track_number:
                try:
                    # Remove leading zeros and format nicely
                    track_num = str(int(track.track_number))
                except (ValueError, TypeError):
                    track_num = str(track.track_number)

            item = QTreeWidgetItem([
                track_num,
                track.title,
                track.artist or "Unknown Artist",
                track.album or "Unknown Album",
                self._format_duration(track.duration)
            ])
            item.setData(0, Qt.ItemDataRole.UserRole, track_id)
            self.tracks_tree.addTopLevelItem(item)

    def _format_duration(self, seconds: Optional[float]) -> str:
        """Format duration."""
        if not seconds:
            return ""
        total = int(round(seconds))
        minutes, secs = divmod(total, 60)
        return f"{minutes}:{secs:02d}"

    def _on_playlist_selected(self, index: int):
        """Handle playlist selection."""
        item = self.playlist_list.item(index) if index >= 0 else None
        if index <= 0 or item is None:
            self.refresh_tracks()
            return

        item_text = item.text()
        playlist_name = item_text.replace("🎵 ", "")
        self._load_playlist_tracks(playlist_name)

    def _load_playlist_tracks(self, name: str):
        """Load tracks from a playlist."""
        playlists = dict(self.library.list_playlists())
        if name in playlists:
            self._display_tracks(playlists[name])

    def _create_playlist(self):
        """Create a new playlist."""
        name, ok = QInputDialog.getText(self, "Create Playlist", "Playlist name:")
        if ok and name:
            self.library.create_playlist(name)
            self.load_playlists()
            if self.main_window:
                self.main_window.show_toast(f"Created playlist '{name}'", "success")

    def _on_track_double_click(self, item, column):
        """Handle track double click."""
        self._play_selected()

    def _play_selected(self):
        """Play selected tracks."""
        tracks = self._get_selected_tracks()
        if tracks:
            self.play_track.emit(tracks[0])
            if len(tracks) > 1:
                self.queue_tracks.emit(tracks[1:])
                if self.main_window:
                    self.main_window.show_toast(f"Playing {tracks[0].title} (+{len(tracks)-1} queued)", "success")
            else:
                if self.main_window:
                    self.main_window.show_toast(f"Playing {tracks[0].title}", "success")

    def _queue_selected(self):
        """Queue selected tracks."""
        tracks = self._get_selected_tracks()
        if tracks:
            self.queue_tracks.emit(tracks)
            if self.main_window:
                count = len(tracks)
                self.main_window.show_toast(f"Queued {count} track{'s' if count != 1 else ''}", "success")

    def _get_selected_tracks(self) -> list[Track]:
        """Get selected tracks."""
        tracks = []
        for item in self.tracks_tree.selectedItems():
            track_id = item.data(0, Qt.ItemDataRole.UserRole)
            if track_id in self.tracks_by_id:
                tracks.append(self.tracks_by_id[track_id])
        return tracks

    def _add_to_playlist(self):
        """Add selected tracks to a playlist."""
        tracks = self._get_selected_tracks()
        if not tracks:
            return

        playlists = [name for name, _ in self.library.list_playlists()]
        if not playlists:
            if self.main_window:
                self.main_window.show_toast("Create a playlist first", "warning")
            return

        name, ok = QInputDialog.getItem(self, "Add to Playlist", "Select playlist:", playlists, 0, False)
        if ok and name:
            for track in tracks:
                self.library.add_to_playlist(name, track.id)
            if self.main_window:
                count = len(tracks)
                self.main_window.show_toast(f"Added {count} track{'s' if count != 1 else ''} to '{name}'", "success")

    def _scan_folder(self):
        """Scan a folder for music."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            if self.main_window:
                self.main_window.show_loading("Scanning library...", determinate=True)
                self.main_window.update_progress(0, "Counting files...")

            # Run in separate thread to avoid blocking UI
            def scan():
                try:
                    folder_path = Path(folder)

                    # First, count total files
                    total_files = 0
                    for file_path in folder_path.rglob("*"):
                        if file_path.is_file() and file_path.suffix.lower() in {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"}:
                            total_files += 1

                    if total_files == 0:
                        self.scan_finished.emit(0, ("warning", "No audio files found"))
                        return

                    # Now scan with progress
                    processed = 0
                    added_tracks = []
                    last_update = 0

                    for file_path in sorted(folder_path.rglob("*")):
                        if not file_path.is_file():
                            continue
                        if file_path.suffix.lower() not in {".mp3", ".flac", ".wav", ".ogg", ".m4a", ".aac"}:
                            continue

                        # Add the track
                        track = self.library.add_track(file_path)
                        if track:
                            added_tracks.append(track)

                        processed += 1
                        progress = int((processed / total_files) * 100)

                        if progress != last_update or processed == total_files:
                            last_update = progress
                            self.scan_progress.emit(progress, f"Scanning... {processed}/{total_files}")

                    count = len(added_tracks)

                    self.scan_finished.emit(count, None)
                except Exception as e:
                    error_msg = str(e)
                    self.scan_finished.emit(0, ("error", error_msg))

            thread = threading.Thread(target=scan, daemon=True)
            thread.start()

    def _handle_scan_progress(self, percent: int, message: str) -> None:
        """Update scan progress."""
        if self.main_window:
            self.main_window.update_progress(percent, message)

    def _handle_scan_finished(self, count: int, outcome) -> None:
        """Finalize scan overlay and toast."""
        severity = None
        message = None
        if isinstance(outcome, tuple):
            severity, message = outcome
        elif outcome:
            severity = "error"
            message = str(outcome)

        if self.main_window:
            if severity == "error":
                self.main_window.update_progress(0, "Scan failed")
            elif severity == "warning":
                self.main_window.update_progress(0, message or "No audio files found")
            else:
                self.main_window.update_progress(100, "Scan complete")
            self.main_window.hide_loading()

        if severity:
            if self.main_window and message:
                level = "warning" if severity == "warning" else "error"
                self.main_window.show_toast(message, level, 5000 if severity == "error" else 4000)
        else:
            self._after_scan(count)

    def _after_scan(self, count: int):
        """Called after scan completes."""
        self.load_playlists()
        self.refresh_tracks()
        if self.main_window:
            self.main_window.show_toast(f"Imported {count} track{'s' if count != 1 else ''}", "success", 4000)

    def _sort_by_column(self, column: int):
        """Sort tracks by column."""
        # For track number column (0), sort numerically
        if column == 0:
            items = []
            for i in range(self.tracks_tree.topLevelItemCount()):
                item = self.tracks_tree.topLevelItem(i)
                track_num_str = item.text(0)
                # Convert to int for sorting, use 999999 for empty
                try:
                    track_num = int(track_num_str) if track_num_str else 999999
                except ValueError:
                    track_num = 999999
                items.append((track_num, item))

            # Sort by track number
            items.sort(key=lambda x: x[0])

            # Reorder in tree
            self.tracks_tree.clear()
            for _, item in items:
                self.tracks_tree.addTopLevelItem(item)
        else:
            # Default Qt sorting for other columns
            self.tracks_tree.sortItems(column, Qt.SortOrder.AscendingOrder)

    def _show_track_context_menu(self, position):
        """Show context menu for tracks."""
        menu = QMenu(self)

        play_action = QAction("▶ Play", self)
        play_action.triggered.connect(self._play_selected)

        queue_action = QAction("+ Queue", self)
        queue_action.triggered.connect(self._queue_selected)

        playlist_action = QAction("+ Add to Playlist", self)
        playlist_action.triggered.connect(self._add_to_playlist)

        menu.addAction(play_action)
        menu.addAction(queue_action)
        menu.addSeparator()
        menu.addAction(playlist_action)

        menu.exec(self.tracks_tree.viewport().mapToGlobal(position))

    def _show_playlist_context_menu(self, position):
        """Show context menu for playlists."""
        index = self.playlist_list.currentRow()
        if index <= 0:
            return

        menu = QMenu(self)

        delete_action = QAction("🗑 Delete Playlist", self)
        delete_action.triggered.connect(self._delete_playlist)

        menu.addAction(delete_action)
        menu.exec(self.playlist_list.viewport().mapToGlobal(position))

    def _delete_playlist(self):
        """Delete selected playlist."""
        index = self.playlist_list.currentRow()
        if index <= 0:
            return

        item_text = self.playlist_list.item(index).text()
        name = item_text.replace("🎵 ", "")

        reply = QMessageBox.question(self, "Delete Playlist",
                                     f"Delete playlist '{name}'?",
                                     QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)

        if reply == QMessageBox.StandardButton.Yes:
            self.library.delete_playlist(name)
            self.load_playlists()
            self.playlist_list.setCurrentRow(0)
            if self.main_window:
                self.main_window.show_toast(f"Deleted playlist '{name}'", "success")


class QueueTab(QWidget):
    """Queue management tab."""

    def __init__(self, player: MusicPlayer, main_window=None, parent=None):
        super().__init__(parent)
        self.player = player
        self.main_window = main_window
        self._setup_ui()

    def _setup_ui(self):
        """Setup the queue tab UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        # Header
        header = QLabel("Playback Queue")
        header.setFont(QFont("-apple-system", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        # Queue list
        self.queue_list = QListWidget()
        self.queue_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.queue_list.customContextMenuRequested.connect(self._show_context_menu)

        # Buttons
        buttons_layout = QHBoxLayout()

        remove_btn = QPushButton("Remove Selected")
        remove_btn.clicked.connect(self._remove_selected)

        clear_btn = QPushButton("Clear Queue")
        clear_btn.clicked.connect(self.player.stop)

        buttons_layout.addWidget(remove_btn)
        buttons_layout.addWidget(clear_btn)
        buttons_layout.addStretch()

        layout.addWidget(header)
        layout.addWidget(self.queue_list)
        layout.addLayout(buttons_layout)

    def update_queue(self):
        """Update the queue display."""
        self.queue_list.clear()
        queue = self.player.queue_snapshot()
        for i, track in enumerate(queue):
            self.queue_list.addItem(f"{i+1}. {track.title} — {track.artist or 'Unknown Artist'}")

    def _remove_selected(self):
        """Remove selected items from queue."""
        count = len(self.queue_list.selectedItems())
        for item in self.queue_list.selectedItems():
            index = self.queue_list.row(item)
            self.player.remove_from_queue(index)
        self.update_queue()
        if self.main_window and count > 0:
            self.main_window.show_toast(f"Removed {count} track{'s' if count != 1 else ''} from queue", "success")

    def _show_context_menu(self, position):
        """Show context menu."""
        menu = QMenu(self)

        remove_action = QAction("Remove", self)
        remove_action.triggered.connect(self._remove_selected)

        clear_action = QAction("Clear All", self)
        clear_action.triggered.connect(self.player.stop)

        menu.addAction(remove_action)
        menu.addAction(clear_action)

        menu.exec(self.queue_list.viewport().mapToGlobal(position))


class RockboxTab(QWidget):
    """Rockbox export and organization tab."""

    bundle_progress = pyqtSignal(int, str)
    bundle_finished = pyqtSignal(object, object, object)
    export_progress = pyqtSignal(int, str)
    export_finished = pyqtSignal(object, object)
    organize_progress = pyqtSignal(int, str)
    organize_finished = pyqtSignal(object, object)

    def __init__(self, main_window=None, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.bundle_progress.connect(self._handle_bundle_progress)
        self.bundle_finished.connect(self._after_bundle)
        self.export_progress.connect(self._handle_export_progress)
        self.export_finished.connect(self._handle_export_finished)
        self.organize_progress.connect(self._handle_organize_progress)
        self.organize_finished.connect(self._handle_organize_finished)
        self._setup_ui()

    def _setup_ui(self):
        """Setup the Rockbox tab UI."""
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(24)

        # Header
        header = QLabel("Rockbox Toolkit")
        header.setFont(QFont("-apple-system", 20, QFont.Weight.Bold))
        header.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        layout.addWidget(header)

        content_layout = QHBoxLayout()
        content_layout.setSpacing(16)

        primary_column = QVBoxLayout()
        primary_column.setSpacing(16)
        secondary_column = QVBoxLayout()
        secondary_column.setSpacing(16)

        primary_column.addWidget(self._create_bundle_section())
        primary_column.addWidget(self._create_organize_section())
        primary_column.addStretch()

        secondary_column.addWidget(self._create_export_section())
        secondary_column.addWidget(self._create_activity_log())
        secondary_column.addStretch()

        content_layout.addLayout(primary_column, 2)
        content_layout.addLayout(secondary_column, 1)

        layout.addLayout(content_layout)

        scroll.setWidget(container)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(scroll)

    def _create_export_section(self) -> QWidget:
        """Create the export playlist section."""
        card = QFrame()
        card.setObjectName("exportCard")
        card.setStyleSheet(f"""
            #exportCard {{
                background-color: {Colors.SURFACE};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Generate M3U Playlists")
        title.setFont(QFont("-apple-system", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        # Source folder
        source_layout = QHBoxLayout()
        source_label = QLabel("Source:")
        source_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        source_layout.addWidget(source_label)
        self.export_source_input = QLineEdit()
        source_browse = QPushButton("Browse")
        source_browse.clicked.connect(lambda: self._browse_folder(self.export_source_input))
        source_layout.addWidget(self.export_source_input, 1)
        source_layout.addWidget(source_browse)

        # Destination
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Destination:")
        dest_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        dest_layout.addWidget(dest_label)
        self.export_dest_input = QLineEdit()
        dest_browse = QPushButton("Browse")
        dest_browse.clicked.connect(lambda: self._browse_folder(self.export_dest_input))
        dest_layout.addWidget(self.export_dest_input, 1)
        dest_layout.addWidget(dest_browse)

        # Options
        self.export_recursive = QCheckBox("Process subfolders recursively")
        self.export_recursive.setChecked(True)

        # Button
        export_btn = QPushButton("Generate Playlists")
        export_btn.setProperty("primary", True)
        export_btn.setStyleSheet(export_btn.styleSheet())
        export_btn.clicked.connect(self._export_playlists)

        layout.addWidget(title)
        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(self.export_recursive)
        layout.addWidget(export_btn)

        return card

    def _create_bundle_section(self) -> QWidget:
        """Create the bundle section."""
        card = QFrame()
        card.setObjectName("bundleCard")
        card.setStyleSheet(f"""
            #bundleCard {{
                background-color: {Colors.SURFACE};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Bundle Albums & Playlists")
        title.setFont(QFont("-apple-system", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        subtitle = QLabel("Stage a drag-and-drop Rockbox bundle with Music/ and Playlists/ folders.")
        subtitle.setStyleSheet(f"color: {Colors.TEXT_SECONDARY};")
        subtitle.setWordWrap(True)

        # Albums root
        albums_layout = QHBoxLayout()
        albums_label = QLabel("Albums root:")
        albums_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        albums_layout.addWidget(albums_label)
        self.bundle_albums_input = QLineEdit()
        self.bundle_albums_input.setPlaceholderText("Optional - full albums directory")
        albums_browse = QPushButton("Browse")
        albums_browse.clicked.connect(lambda: self._browse_folder(self.bundle_albums_input))
        albums_layout.addWidget(self.bundle_albums_input, 1)
        albums_layout.addWidget(albums_browse)

        # Playlists root
        playlists_layout = QHBoxLayout()
        playlists_label = QLabel("Playlists root:")
        playlists_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        playlists_layout.addWidget(playlists_label)
        self.bundle_playlists_input = QLineEdit()
        self.bundle_playlists_input.setPlaceholderText("Optional - downloaded playlists directory")
        playlists_browse = QPushButton("Browse")
        playlists_browse.clicked.connect(lambda: self._browse_folder(self.bundle_playlists_input))
        playlists_layout.addWidget(self.bundle_playlists_input, 1)
        playlists_layout.addWidget(playlists_browse)

        # Destination root
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Bundle destination:")
        dest_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        dest_layout.addWidget(dest_label)
        self.bundle_dest_input = QLineEdit()
        self.bundle_dest_input.setPlaceholderText("Required - e.g. /Volumes/IPOD")
        dest_browse = QPushButton("Browse")
        dest_browse.clicked.connect(lambda: self._browse_folder(self.bundle_dest_input))
        dest_layout.addWidget(self.bundle_dest_input, 1)
        dest_layout.addWidget(dest_browse)

        # Options
        self.bundle_include_genre = QCheckBox("Include genre as the top folder level")
        self.bundle_move_albums = QCheckBox("Move album files instead of copying")
        self.bundle_move_playlists = QCheckBox("Move playlist files when copying into Music/")

        # Button
        bundle_btn = QPushButton("Create Rockbox Bundle")
        bundle_btn.setProperty("primary", True)
        bundle_btn.setStyleSheet(bundle_btn.styleSheet())
        bundle_btn.clicked.connect(self._bundle_collection)

        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(albums_layout)
        layout.addLayout(playlists_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(self.bundle_include_genre)
        layout.addWidget(self.bundle_move_albums)
        layout.addWidget(self.bundle_move_playlists)
        layout.addWidget(bundle_btn)

        return card

    def _create_organize_section(self) -> QWidget:
        """Create the organize section."""
        card = QFrame()
        card.setObjectName("organizeCard")
        card.setStyleSheet(f"""
            #organizeCard {{
                background-color: {Colors.SURFACE};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Organize Music Collection")
        title.setFont(QFont("-apple-system", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        # Source
        source_layout = QHBoxLayout()
        source_label = QLabel("Unsorted:")
        source_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        source_layout.addWidget(source_label)
        self.org_source_input = QLineEdit()
        source_browse = QPushButton("Browse")
        source_browse.clicked.connect(lambda: self._browse_folder(self.org_source_input))
        source_layout.addWidget(self.org_source_input, 1)
        source_layout.addWidget(source_browse)

        # Destination
        dest_layout = QHBoxLayout()
        dest_label = QLabel("Destination:")
        dest_label.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")
        dest_layout.addWidget(dest_label)
        self.org_dest_input = QLineEdit()
        dest_browse = QPushButton("Browse")
        dest_browse.clicked.connect(lambda: self._browse_folder(self.org_dest_input))
        dest_layout.addWidget(self.org_dest_input, 1)
        dest_layout.addWidget(dest_browse)

        # Options
        self.org_move = QCheckBox("Move files (instead of copy)")
        self.org_genre = QCheckBox("Include genre folder")

        # Button
        organize_btn = QPushButton("Organize Collection")
        organize_btn.setProperty("primary", True)
        organize_btn.setStyleSheet(organize_btn.styleSheet())
        organize_btn.clicked.connect(self._organize_collection)

        layout.addWidget(title)
        layout.addLayout(source_layout)
        layout.addLayout(dest_layout)
        layout.addWidget(self.org_move)
        layout.addWidget(self.org_genre)
        layout.addWidget(organize_btn)

        return card

    def _create_activity_log(self) -> QWidget:
        """Create logging panel."""
        card = QFrame()
        card.setObjectName("logCard")
        card.setStyleSheet(f"""
            #logCard {{
                background-color: {Colors.SURFACE};
                border-radius: 12px;
                padding: 20px;
            }}
        """)

        layout = QVBoxLayout(card)
        layout.setSpacing(12)

        title = QLabel("Activity Log")
        title.setFont(QFont("-apple-system", 16, QFont.Weight.DemiBold))
        title.setStyleSheet(f"color: {Colors.TEXT_PRIMARY};")

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        self.log_output.setMinimumHeight(220)

        layout.addWidget(title)
        layout.addWidget(self.log_output)

        return card

    def _bundle_collection(self):
        """Bundle albums and playlists for Rockbox."""
        album_root = self.bundle_albums_input.text().strip()
        playlist_root = self.bundle_playlists_input.text().strip()
        dest_root = self.bundle_dest_input.text().strip()

        if not album_root and not playlist_root:
            if self.main_window:
                self.main_window.show_toast("Select at least an albums or playlists folder", "warning")
            return

        if not dest_root:
            if self.main_window:
                self.main_window.show_toast("Select a destination for the bundle", "warning")
            return

        include_genre = self.bundle_include_genre.isChecked()
        move_albums = self.bundle_move_albums.isChecked()
        move_playlists = self.bundle_move_playlists.isChecked()

        if self.main_window:
            self.main_window.show_loading("Bundling for Rockbox...", determinate=True)
            self.main_window.update_progress(0, "Preparing Rockbox bundle...")

        dest_path = Path(dest_root).expanduser().resolve()

        def bundle():
            try:
                from .rockbox import bundle_for_rockbox

                album_dirs = [Path(album_root).expanduser()] if album_root else None
                playlist_dirs = [Path(playlist_root).expanduser()] if playlist_root else None

                def emit_progress(done: int, total: int, message: str) -> None:
                    if total:
                        percent = int((done / total) * 100)
                        if done >= total:
                            percent = 100
                        elif done > 0 and percent == 0:
                            percent = 1
                    else:
                        percent = 0

                    self.bundle_progress.emit(percent, message)

                result = bundle_for_rockbox(
                    album_dirs,
                    playlist_dirs,
                    dest_path,
                    include_genre=include_genre,
                    move_albums=move_albums,
                    move_playlists=move_playlists,
                    progress_callback=emit_progress,
                )

                self.bundle_finished.emit(result, None, dest_path)
            except Exception as exc:  # pragma: no cover - defensive
                logger.exception("Failed to bundle for Rockbox: %s", exc)

                self.bundle_finished.emit(None, str(exc), dest_path)

        thread = threading.Thread(target=bundle, daemon=True)
        thread.start()

    def _handle_bundle_progress(self, percent: int, message: str) -> None:
        """Update progress bar safely on the UI thread."""
        if self.main_window:
            self.main_window.update_progress(percent, message)

    def _handle_export_progress(self, percent: int, message: str) -> None:
        """Update export progress."""
        if self.main_window:
            self.main_window.update_progress(percent, message)

    def _handle_export_finished(self, results, error) -> None:
        """Hide overlay and defer to logger for export results."""
        if self.main_window:
            if error:
                self.main_window.update_progress(0, "Playlist export failed")
            else:
                self.main_window.update_progress(100, "Playlists ready")
            self.main_window.hide_loading()
        self._after_export(results, error)

    def _after_bundle(self, result, error, dest_path: Optional[Path]):
        """Handle bundle completion."""
        if self.main_window:
            self.main_window.update_progress(100 if not error else 0, "Rockbox bundle ready" if not error else "Bundle failed")
            self.main_window.hide_loading()

        if error:
            if self.main_window:
                self.main_window.show_toast(f"Bundle failed: {error}", "error", 5000)
            self.log_output.append(f"✗ Bundle error: {error}")
            return

        if not result:
            self.log_output.append("No bundle results.")
            return

        staged = {res.destination for res in result.music_results if res.destination}
        copied = sum(1 for r in result.music_results if r.action == "copied")
        moved = sum(1 for r in result.music_results if r.action == "moved")
        errors = [r for r in result.music_results if r.action == "error"]
        playlist_count = len(result.playlist_results)

        bundle_root = dest_path if dest_path else None
        bundle_text = bundle_root.as_posix() if bundle_root else "destination"

        self.log_output.append(
            f"✓ Bundle ready at {bundle_text}: {len(staged)} tracks staged "
            f"({copied} copied, {moved} moved) across {playlist_count} playlist(s)"
        )

        for playlist in result.playlist_results[:5]:
            missing = len(playlist.missing_sources)
            summary = f"  • {playlist.playlist_path.name}: {playlist.track_count} tracks"
            if missing:
                summary += f" ({missing} missing)"
            self.log_output.append(summary)
            if missing:
                for skipped in playlist.missing_sources[:3]:
                    self.log_output.append(f"      ! Skipped {skipped.name}")
                if missing > 3:
                    self.log_output.append(f"      ... {missing - 3} more skipped")

        if playlist_count > 5:
            self.log_output.append(f"  ... plus {playlist_count - 5} more playlists")

        if errors:
            self.log_output.append(f"⚠ Encountered {len(errors)} errors while staging tracks.")
            if self.main_window:
                self.main_window.show_toast(f"Bundle completed with {len(errors)} errors", "warning", 5000)
        else:
            if self.main_window:
                self.main_window.show_toast("Rockbox bundle ready to copy", "success", 4000)

    def _handle_organize_progress(self, percent: int, message: str) -> None:
        """Update organize progress."""
        if self.main_window:
            self.main_window.update_progress(percent, message)

    def _handle_organize_finished(self, results, error) -> None:
        """Hide overlay and log organize outcome."""
        if self.main_window:
            if error:
                self.main_window.update_progress(0, "Organize failed")
            else:
                self.main_window.update_progress(100, "Library organized")
            self.main_window.hide_loading()
        self._after_organize(results, error)

    def _browse_folder(self, line_edit: QLineEdit):
        """Browse for a folder."""
        folder = QFileDialog.getExistingDirectory(self, "Select Folder")
        if folder:
            line_edit.setText(folder)

    def _export_playlists(self):
        """Export M3U playlists."""
        source = self.export_source_input.text()
        if not source:
            if self.main_window:
                self.main_window.show_toast("Please select a source folder", "warning")
            return

        dest = self.export_dest_input.text() or None
        recursive = self.export_recursive.isChecked()

        if self.main_window:
            self.main_window.show_loading("Generating playlists...", determinate=True)
            self.main_window.update_progress(0, "Preparing playlist export...")

        def export():
            try:
                from .rockbox import (
                    ExportResult, _collect_directories, _list_tracks,
                    _build_playlist_path, _relative_path, PLAYLIST_HEADER,
                    SUPPORTED_EXTENSIONS
                )

                source_path = Path(source).expanduser().resolve()
                if not source_path.is_dir():
                    raise ValueError(f"{source_path} is not a directory")

                destination_path = (
                    Path(dest).expanduser().resolve() if dest else source_path
                )
                exts = {ext.lower() for ext in SUPPORTED_EXTENSIONS}

                # Collect directories to process
                directories = _collect_directories(source_path, recursive=recursive)
                total_dirs = len(directories)

                if total_dirs == 0:
                    self.export_finished.emit(None, "No directories found")
                    return

                # Process each directory with progress
                results = []
                processed = 0
                last_update = 0

                for directory in directories:
                    tracks = _list_tracks(directory, exts)
                    if tracks:
                        playlist_path = _build_playlist_path(source_path, directory, destination_path)
                        playlist_path.parent.mkdir(parents=True, exist_ok=True)
                        with playlist_path.open("w", encoding="utf-8", newline="\n") as handle:
                            handle.write(PLAYLIST_HEADER)
                            for track in tracks:
                                rel_path = _relative_path(track, playlist_path.parent)
                                handle.write(rel_path + "\n")
                        results.append(ExportResult(playlist_path=playlist_path, track_count=len(tracks)))

                    processed += 1
                    progress = int((processed / total_dirs) * 100)

                    if progress != last_update or processed == total_dirs:
                        last_update = progress
                        self.export_progress.emit(progress, f"Exporting playlists... {processed}/{total_dirs}")

                self.export_finished.emit(results, None)
            except Exception as e:
                self.export_finished.emit(None, str(e))

        thread = threading.Thread(target=export, daemon=True)
        thread.start()

    def _after_export(self, results, error):
        """Called after export completes."""
        if error:
            if self.main_window:
                self.main_window.show_toast(f"Export failed: {error}", "error", 5000)
            self.log_output.append(f"✗ Error: {error}")
        elif results:
            self.log_output.append(f"✓ Generated {len(results)} playlist(s)")
            for result in results:
                self.log_output.append(f"  • {result.playlist_path} ({result.track_count} tracks)")
            if self.main_window:
                self.main_window.show_toast(f"Generated {len(results)} playlist(s)", "success", 4000)

    def _organize_collection(self):
        """Organize music collection."""
        source = self.org_source_input.text()
        dest = self.org_dest_input.text()

        if not source or not dest:
            if self.main_window:
                self.main_window.show_toast("Please select both source and destination", "warning")
            return

        move = self.org_move.isChecked()
        genre = self.org_genre.isChecked()

        if self.main_window:
            self.main_window.show_loading("Organizing collection...", determinate=True)
            self.main_window.update_progress(0, "Scanning files...")

        def organize():
            try:
                from .rockbox import (
                    OrganizeResult, _read_tags, _safe_component,
                    _format_track_number, SUPPORTED_EXTENSIONS
                )
                import shutil

                source_path = Path(source).expanduser().resolve()
                dest_path = Path(dest).expanduser().resolve()

                if not source_path.is_dir():
                    raise ValueError(f"{source_path} is not a directory")
                if not dest_path.exists():
                    dest_path.mkdir(parents=True, exist_ok=True)

                exts = {ext.lower() for ext in SUPPORTED_EXTENSIONS}

                # First, count total audio files
                all_files = sorted(p for p in source_path.rglob("*") if p.is_file())
                audio_files = [f for f in all_files if f.suffix.lower() in exts]
                total_files = len(audio_files)

                if total_files == 0:
                    self.organize_finished.emit([], "No audio files found")
                    return

                # Now organize with progress
                results = []
                processed = 0

                for file_path in audio_files:
                    try:
                        tags = _read_tags(file_path)
                        artist = _safe_component(tags.get("artist") or "Unknown Artist")
                        album = _safe_component(tags.get("album") or "Unknown Album")
                        title = _safe_component(tags.get("title") or file_path.stem)
                        genre_tag = _safe_component(tags.get("genre") or "Unknown Genre") if genre else None
                        track_no = _format_track_number(tags.get("track_number"), file_path.stem)

                        rel_parts = [artist, album]
                        if genre and genre_tag:
                            rel_parts.insert(0, genre_tag)

                        target_dir = dest_path.joinpath(*rel_parts)
                        target_dir.mkdir(parents=True, exist_ok=True)

                        base_name = f"{track_no} - {title}{file_path.suffix.lower()}"
                        target_path = target_dir / base_name
                        counter = 1
                        while target_path.exists():
                            target_path = target_dir / f"{track_no} - {title} ({counter}){file_path.suffix.lower()}"
                            counter += 1

                        if move:
                            shutil.move(str(file_path), target_path)
                            action = "moved"
                        else:
                            shutil.copy2(file_path, target_path)
                            action = "copied"
                        results.append(OrganizeResult(source=file_path, destination=target_path, action=action))
                    except Exception as exc:
                        logger.exception("Failed to organize %s: %s", file_path, exc)
                        results.append(
                            OrganizeResult(
                                source=file_path,
                                destination=None,
                                action="error",
                                reason=str(exc),
                            )
                        )

                    processed += 1
                    progress = int((processed / total_files) * 100)

                    self.organize_progress.emit(progress, f"Organizing... {processed}/{total_files}")

                self.organize_finished.emit(results, None)
            except Exception as e:
                self.organize_finished.emit(None, str(e))

        thread = threading.Thread(target=organize, daemon=True)
        thread.start()

    def _after_organize(self, results, error):
        """Called after organize completes."""
        if error:
            if self.main_window:
                self.main_window.show_toast(f"Organize failed: {error}", "error", 5000)
            self.log_output.append(f"✗ Error: {error}")
        elif results:
            copied = sum(1 for r in results if r.action == "copied")
            moved = sum(1 for r in results if r.action == "moved")
            errors = sum(1 for r in results if r.action == "error")

            self.log_output.append(f"✓ Organized: {copied} copied, {moved} moved, {errors} errors")

            for result in results[:20]:
                if result.destination:
                    self.log_output.append(f"  • {result.source.name} → {result.destination.name}")

            if len(results) > 20:
                self.log_output.append(f"  ... and {len(results) - 20} more")

            if self.main_window:
                if errors > 0:
                    self.main_window.show_toast(f"Organized with {errors} error(s)", "warning", 5000)
                else:
                    self.main_window.show_toast(f"Successfully organized {copied + moved} files", "success", 4000)


class MainWindow(QMainWindow):
    """Main application window with Apple-inspired design."""

    def __init__(self, library: MusicLibrary):
        super().__init__()
        self.library = library

        self.setWindowTitle("iPod Organizer")
        self.setMinimumSize(1200, 800)

        self._setup_ui()

        # Loading overlay
        self.loading_overlay = LoadingOverlay(self)

    def _setup_ui(self):
        """Setup the main UI."""
        # Central widget
        central = QWidget()
        self.setCentralWidget(central)

        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        # Rockbox tab
        self.rockbox_tab = RockboxTab(self)

        self.tabs.addTab(self.rockbox_tab, "Rockbox")

        layout.addWidget(self.tabs)

    def show_toast(self, message: str, toast_type: str = "info", duration: int = 3000):
        """Show a toast notification."""
        toast = Toast(message, toast_type)
        toast.show_toast(self, duration)

    def show_loading(self, message: str = "Loading...", determinate: bool = False):
        """Show loading overlay."""
        self.loading_overlay.show_loading(message, determinate)

    def update_progress(self, value: int, message: str = None):
        """Update loading progress."""
        self.loading_overlay.update_progress(value, message)

    def hide_loading(self):
        """Hide loading overlay."""
        self.loading_overlay.hide_loading()


def run_gui() -> None:
    """Launch the PyQt6 GUI application."""
    import sys

    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(STYLESHEET)

    # Set application font
    font = QFont("-apple-system, BlinkMacSystemFont, Segoe UI", 13)
    app.setFont(font)

    library = MusicLibrary()
    window = MainWindow(library)
    window.show()

    sys.exit(app.exec())
