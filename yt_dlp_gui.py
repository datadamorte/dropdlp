import html
import os
import platform
import subprocess
import sys
import tempfile
from datetime import datetime

from PyQt5.QtCore import (
    QPoint,
    QSettings,
    Qt,
    QThread,
    QTimer,
    QUrl,
    pyqtSignal,
)
from PyQt5.QtGui import (
    QColor,
    QDesktopServices,
    QFont,
    QFontDatabase,
    QIcon,
    QKeySequence,
    QPainter,
    QPainterPath,
    QPalette,
    QPen,
    QPixmap,
    QPolygon,
)
from PyQt5.QtWidgets import (
    QAction,
    QApplication,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QShortcut,
    QSizePolicy,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from ytdlp_core import (
    APP_VERSION,
    build_ytdlp_command,
    download_file,
    ffmpeg_available,
    first_url_in_text,
    is_frozen,
    is_valid_url,
    make_executable,
    parse_progress_line,
    popen_kwargs,
    portable_root,
    resolve_ytdlp_path,
    terminate_process,
    ytdlp_exe_name,
    ytdlp_install_dir,
    ytdlp_release_url,
)
WINDOW_TITLE = "yt-dlp Downloader"


def preferred_ui_font():
    families = QFontDatabase().families()
    system = platform.system()
    if system == "Darwin":
        candidates = [".AppleSystemUIFont", "SF Pro Text", "Helvetica Neue"]
    elif system == "Windows":
        candidates = ["Segoe UI", "Segoe UI Variable"]
    else:
        candidates = ["Inter", "Ubuntu", "Noto Sans", "DejaVu Sans"]
    for name in candidates:
        if name in families:
            font = QFont(name, 10)
            break
    else:
        font = QFont()
        font.setStyleHint(QFont.SansSerif)
        font.setPointSize(10)
    font.setHintingPreference(QFont.PreferFullHinting)
    return font


def make_app_icon():
    size = 64
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setBrush(QColor("#1c1c1f"))
    painter.setPen(QPen(QColor("#3a3a40"), 2))
    painter.drawRoundedRect(4, 4, 56, 56, 14, 14)
    painter.setPen(Qt.NoPen)
    painter.setBrush(QColor("#ececee"))
    painter.drawRoundedRect(28, 16, 8, 20, 1, 1)
    arrow = QPainterPath()
    arrow.moveTo(18, 34)
    arrow.lineTo(32, 50)
    arrow.lineTo(46, 34)
    arrow.closeSubpath()
    painter.drawPath(arrow)
    painter.end()
    return QIcon(pixmap)


def make_check_icon_path():
    path = os.path.join(tempfile.gettempdir(), "ytdlp-gui-check.png")
    pixmap = QPixmap(12, 12)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#111113"))
    pen.setWidth(2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygon([QPoint(2, 6), QPoint(5, 9), QPoint(10, 3)]))
    painter.end()
    pixmap.save(path, "PNG")
    return path.replace("\\", "/")


def make_chevron_icon_path():
    path = os.path.join(tempfile.gettempdir(), "ytdlp-gui-chevron.png")
    pixmap = QPixmap(10, 10)
    pixmap.fill(Qt.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.Antialiasing)
    pen = QPen(QColor("#8e8e96"))
    pen.setWidth(2)
    pen.setCapStyle(Qt.RoundCap)
    pen.setJoinStyle(Qt.RoundJoin)
    painter.setPen(pen)
    painter.drawPolyline(QPolygon([QPoint(2, 3), QPoint(5, 7), QPoint(8, 3)]))
    painter.end()
    pixmap.save(path, "PNG")
    return path.replace("\\", "/")


def apply_dark_palette(app):
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#101012"))
    palette.setColor(QPalette.WindowText, QColor("#f0f0f2"))
    palette.setColor(QPalette.Base, QColor("#1c1c1f"))
    palette.setColor(QPalette.AlternateBase, QColor("#161618"))
    palette.setColor(QPalette.Text, QColor("#f0f0f2"))
    palette.setColor(QPalette.Button, QColor("#1c1c1f"))
    palette.setColor(QPalette.ButtonText, QColor("#f0f0f2"))
    palette.setColor(QPalette.BrightText, QColor("#f0f0f2"))
    palette.setColor(QPalette.Highlight, QColor("#3a3a40"))
    palette.setColor(QPalette.HighlightedText, QColor("#f0f0f2"))
    palette.setColor(QPalette.Link, QColor("#c8c8ce"))
    palette.setColor(QPalette.ToolTipBase, QColor("#1c1c1f"))
    palette.setColor(QPalette.ToolTipText, QColor("#f0f0f2"))
    palette.setColor(QPalette.PlaceholderText, QColor("#63636b"))
    palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#63636b"))
    palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#63636b"))
    palette.setColor(QPalette.Disabled, QPalette.WindowText, QColor("#63636b"))
    app.setPalette(palette)


def app_stylesheet(check_path, chevron_path):
    return f"""
        QMainWindow {{
            background-color: #121214;
        }}
        QWidget {{
            color: #f0f0f2;
            font-size: 13px;
        }}
        QWidget#root {{
            background-color: #121214;
        }}

        QMenuBar {{
            background-color: #121214;
            color: #c8c8ce;
            border-bottom: 1px solid #2a2a2e;
            padding: 2px 10px;
            spacing: 4px;
        }}
        QMenuBar::item {{
            background: transparent;
            padding: 5px 9px;
            border-radius: 4px;
        }}
        QMenuBar::item:selected {{
            background: #1c1c1f;
        }}
        QMenu {{
            background-color: #161618;
            color: #f0f0f2;
            border: 1px solid #2a2a2e;
            padding: 6px;
        }}
        QMenu::item {{
            padding: 6px 28px 6px 12px;
            border-radius: 4px;
        }}
        QMenu::item:selected {{
            background: #2a2a2e;
        }}
        QMenu::separator {{
            height: 1px;
            background: #2a2a2e;
            margin: 5px 8px;
        }}

        QStatusBar {{
            background-color: #121214;
            color: #8e8e96;
            border-top: 1px solid #2a2a2e;
        }}
        QStatusBar QLabel {{
            color: #8e8e96;
            font-size: 12px;
            padding-left: 4px;
        }}

        QLabel#sectionTitle {{
            font-size: 12px;
            font-weight: 600;
            color: #d0d0d6;
            padding-bottom: 4px;
        }}
        QLabel#fieldLabel {{
            font-size: 12px;
            color: #8e8e96;
        }}
        QLabel#rowLabel {{
            font-size: 12px;
            color: #8e8e96;
            min-width: 58px;
        }}
        QLabel#versionLabel {{
            font-size: 11px;
            color: #63636b;
            padding-right: 8px;
        }}

        QFrame#hairline {{
            background: #2a2a2e;
            border: none;
            max-height: 1px;
            min-height: 1px;
        }}
        QFrame#panel {{
            background-color: #1a1a1d;
            border: 1px solid #2a2a2e;
            border-radius: 8px;
        }}

        QLineEdit {{
            background-color: #1c1c1f;
            border: 1px solid #2a2a2e;
            border-radius: 6px;
            padding: 7px 10px;
            color: #f0f0f2;
            selection-background-color: #3a3a40;
            min-height: 18px;
        }}
        QLineEdit:focus {{
            border: 1px solid #5c5c64;
            background-color: #161618;
        }}
        QLineEdit:disabled {{
            color: #63636b;
        }}
        QLineEdit#urlField {{
            font-size: 13px;
            padding: 8px 12px;
        }}

        QComboBox, QSpinBox {{
            background-color: #1c1c1f;
            border: 1px solid #2a2a2e;
            border-radius: 6px;
            padding: 5px 8px;
            min-height: 18px;
            color: #f0f0f2;
        }}
        QComboBox:on, QComboBox:focus, QSpinBox:focus {{
            border: 1px solid #5c5c64;
        }}
        QComboBox:disabled, QSpinBox:disabled {{
            color: #63636b;
            background-color: #161618;
        }}
        QComboBox::drop-down {{
            border: none;
            width: 22px;
        }}
        QComboBox::down-arrow {{
            image: url({chevron_path});
            width: 10px;
            height: 10px;
            margin-right: 6px;
        }}
        QComboBox QAbstractItemView {{
            background-color: #161618;
            border: 1px solid #2a2a2e;
            selection-background-color: #2a2a2e;
            color: #f0f0f2;
            outline: none;
            padding: 4px;
        }}

        QCheckBox {{
            spacing: 8px;
            color: #d8d8de;
        }}
        QCheckBox:disabled {{
            color: #63636b;
        }}
        QCheckBox::indicator {{
            width: 15px;
            height: 15px;
            border: 1px solid #3a3a40;
            border-radius: 4px;
            background-color: #1c1c1f;
        }}
        QCheckBox::indicator:hover {{
            border-color: #5c5c64;
        }}
        QCheckBox::indicator:checked {{
            background-color: #ececee;
            border-color: #ececee;
            image: url({check_path});
        }}
        QCheckBox::indicator:checked:disabled {{
            background-color: #3a3a40;
            border-color: #3a3a40;
        }}
        QCheckBox::indicator:disabled {{
            background-color: #161618;
            border-color: #2a2a2e;
        }}

        QPushButton {{
            background-color: #1c1c1f;
            border: 1px solid #2a2a2e;
            border-radius: 6px;
            padding: 7px 14px;
            font-weight: 500;
            color: #f0f0f2;
        }}
        QPushButton:hover {{
            background-color: #242428;
            border-color: #3a3a40;
        }}
        QPushButton:pressed {{
            background-color: #161618;
        }}
        QPushButton:disabled {{
            color: #63636b;
            border-color: #2a2a2e;
            background-color: #161618;
        }}

        QPushButton#download_btn {{
            background-color: #ececee;
            color: #111113;
            border: none;
            font-weight: 600;
            padding: 8px 18px;
            min-width: 108px;
        }}
        QPushButton#download_btn:hover {{
            background-color: #ffffff;
        }}
        QPushButton#download_btn:pressed {{
            background-color: #d4d4d8;
        }}
        QPushButton#download_btn:disabled {{
            background-color: #2a2a2e;
            color: #63636b;
        }}

        QPushButton#cancel_btn {{
            background-color: transparent;
            color: #e4b4b4;
            border: 1px solid #5c3a3a;
            font-weight: 600;
            padding: 8px 18px;
            min-width: 108px;
        }}
        QPushButton#cancel_btn:hover {{
            background-color: #2a1818;
            border-color: #7a4a4a;
        }}
        QPushButton#cancel_btn:disabled {{
            color: #63636b;
            border-color: #2a2a2e;
        }}

        QPushButton#secondary_btn {{
            background-color: #1c1c1f;
            border: 1px solid #2a2a2e;
            font-weight: 500;
        }}

        QPushButton#linkBtn {{
            background: transparent;
            border: none;
            color: #8e8e96;
            font-weight: 500;
            padding: 4px 8px;
        }}
        QPushButton#linkBtn:hover {{
            color: #f0f0f2;
            background: #1c1c1f;
        }}
        QPushButton#linkBtn:disabled {{
            color: #4a4a52;
            background: transparent;
        }}

        QProgressBar {{
            border: none;
            background-color: #1c1c1f;
            border-radius: 4px;
            text-align: center;
            color: transparent;
            min-height: 6px;
            max-height: 6px;
        }}
        QProgressBar::chunk {{
            background-color: #ececee;
            border-radius: 4px;
        }}

        QTextEdit#logView {{
            background-color: #0c0c0e;
            border: 1px solid #2a2a2e;
            border-radius: 8px;
            font-family: "Menlo", "SF Mono", "Cascadia Mono", "Consolas", "Ubuntu Mono", monospace;
            font-size: 12px;
            padding: 10px 12px;
        }}

        QScrollBar:vertical {{
            border: none;
            background: transparent;
            width: 10px;
            margin: 4px 2px;
        }}
        QScrollBar::handle:vertical {{
            background: #3a3a40;
            min-height: 24px;
            border-radius: 4px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: #4a4a52;
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical,
        QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
            height: 0;
            background: none;
        }}
        QScrollBar:horizontal {{
            border: none;
            background: transparent;
            height: 10px;
            margin: 2px 4px;
        }}
        QScrollBar::handle:horizontal {{
            background: #3a3a40;
            min-width: 24px;
            border-radius: 4px;
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal,
        QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
            width: 0;
            background: none;
        }}

        QToolTip {{
            background-color: #1c1c1f;
            color: #f0f0f2;
            border: 1px solid #2a2a2e;
            padding: 5px 8px;
        }}

        QMessageBox {{
            background-color: #161618;
        }}
    """


class DownloadThread(QThread):
    progress = pyqtSignal(str)
    progress_percent = pyqtSignal(int)
    progress_status = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, exe_path, url, options, output_path):
        super().__init__()
        self.exe_path = exe_path
        self.url = url
        self.options = options
        self.output_path = output_path
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process(self.process)

    def run(self):
        try:
            options = dict(self.options)
            returncode = self._run_once(options)
            if returncode is None:
                return
            if (
                returncode != 0
                and not self._is_cancelled
                and self._needs_impersonate
                and not options.get("impersonate")
            ):
                self.progress.emit("Cloudflare challenge detected — retrying with browser impersonation…")
                options["impersonate"] = True
                returncode = self._run_once(options)
                if returncode is None:
                    return

            if self._is_cancelled:
                self.error.emit("Download cancelled by user")
            elif returncode == 0:
                self.finished.emit("Download completed successfully")
            else:
                self.error.emit(f"Download failed with return code: {returncode}")
        except Exception as e:
            self.error.emit(f"Error: {e}")

    def _run_once(self, options):
        """Run yt-dlp once. Returns its exit code, or None if an error was already emitted."""
        self._needs_impersonate = False
        cmd = build_ytdlp_command(self.exe_path, self.url, options, self.output_path)
        self.process = subprocess.Popen(cmd, **popen_kwargs())

        for line in self.process.stdout:
            if self._is_cancelled:
                break
            line = line.strip()
            if not line:
                continue
            self.progress.emit(line)
            if "generic:impersonate" in line:
                self._needs_impersonate = True
            info = parse_progress_line(line)
            if not info:
                continue
            if info.percent is not None:
                self.progress_percent.emit(info.percent)
            parts = []
            if info.percent is not None:
                parts.append(f"{info.percent}%")
            if info.speed:
                parts.append(info.speed)
            if info.eta:
                parts.append(f"ETA {info.eta}")
            if info.postprocessing:
                parts.append("Processing…")
            if info.destination:
                parts.append(os.path.basename(info.destination))
            if parts:
                self.progress_status.emit("  ·  ".join(parts))

        try:
            self.process.wait(timeout=15)
        except subprocess.TimeoutExpired:
            terminate_process(self.process)
            self.error.emit("Download did not exit cleanly")
            return None

        return self.process.returncode


class UpdateThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, exe_path):
        super().__init__()
        self.exe_path = exe_path
        self.process = None
        self._is_cancelled = False

    def cancel(self):
        self._is_cancelled = True
        terminate_process(self.process)

    def run(self):
        try:
            cmd = [self.exe_path, "-U"]
            self.process = subprocess.Popen(cmd, **popen_kwargs())
            output_lines = []
            for line in self.process.stdout:
                if self._is_cancelled:
                    terminate_process(self.process)
                    self.error.emit("Update cancelled")
                    return
                stripped = line.strip()
                output_lines.append(stripped)
                self.progress.emit(stripped)
            self.process.wait(timeout=30)

            if self._is_cancelled:
                self.error.emit("Update cancelled")
                return

            if self.process.returncode == 0:
                self.finished.emit("yt-dlp update completed.")
                return

            output_text = "\n".join(output_lines)
            if self.process.returncode == 100 or "installed yt-dlp with pip" in output_text:
                if is_frozen():
                    self.error.emit(
                        "yt-dlp on PATH was installed with pip; this portable app "
                        "cannot upgrade it via pip. It will still run."
                    )
                    return
                self.progress.emit("Detected pip installation, updating via pip...")
                self._update_via_pip()
            else:
                self.error.emit(f"Update failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"Error: {e}")

    def _update_via_pip(self):
        try:
            if is_frozen():
                self.error.emit(
                    "This portable build cannot upgrade yt-dlp via pip."
                )
                return
            cmd = [sys.executable, "-m", "pip", "install", "-U", "yt-dlp"]
            self.process = subprocess.Popen(cmd, **popen_kwargs())
            for line in self.process.stdout:
                if self._is_cancelled:
                    terminate_process(self.process)
                    self.error.emit("Update cancelled")
                    return
                self.progress.emit(line.strip())
            self.process.wait(timeout=30)
            if self.process.returncode == 0:
                self.finished.emit("yt-dlp updated via pip.")
            else:
                self.error.emit(f"pip update failed with return code: {self.process.returncode}")
        except Exception as e:
            self.error.emit(f"pip update error: {e}")


class InstallThread(QThread):
    progress_percent = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, dest_path, system_name):
        super().__init__()
        self.dest_path = dest_path
        self.system_name = system_name

    def run(self):
        tmp_path = self.dest_path + ".download"
        try:
            url = ytdlp_release_url(self.system_name)
            download_file(url, tmp_path, progress_cb=self.progress_percent.emit)
            make_executable(tmp_path, self.system_name)
            os.replace(tmp_path, self.dest_path)
            self.finished.emit(self.dest_path)
        except Exception as e:
            try:
                if os.path.exists(tmp_path):
                    os.remove(tmp_path)
            except OSError:
                pass
            self.error.emit(str(e))


class YTDLPWindow(QMainWindow):
    def __init__(self, skip_startup=False, settings=None):
        super().__init__()
        self.download_thread = None
        self.update_thread = None
        self.install_thread = None
        self._auto_updating = False
        self._busy = False
        self.settings = settings or QSettings("YTDLPGui", "ModernYTDLP")
        self.last_clipboard = ""
        self._warned_ffmpeg = False
        self._did_initial_focus = False

        self.init_ui()
        self.apply_theme()
        self.load_settings()
        self.setup_shortcuts()
        self.sync_dependent_controls()

        self.check_clipboard_timer = QTimer(self)
        self.check_clipboard_timer.timeout.connect(self.check_clipboard)

        if not skip_startup:
            self.check_clipboard_timer.start(1000)
            QTimer.singleShot(100, self.check_and_install_ytdlp)
            QTimer.singleShot(200, self.warn_if_ffmpeg_missing)

    def _app_dir(self):
        return portable_root()

    def _install_dir(self):
        path = ytdlp_install_dir()
        os.makedirs(path, exist_ok=True)
        return path

    def _ytdlp_exe_name(self):
        return ytdlp_exe_name()

    def resolve_ytdlp_path(self):
        return resolve_ytdlp_path(
            self._install_dir(),
            os.getcwd(),
            extra_dirs=[self._app_dir()],
        )

    def _field_label(self, text, buddy=None):
        label = QLabel(text)
        label.setObjectName("fieldLabel")
        if buddy is not None:
            label.setBuddy(buddy)
        return label

    def _section_title(self, text):
        label = QLabel(text)
        label.setObjectName("sectionTitle")
        return label

    def _row_label(self, text, buddy=None):
        label = QLabel(text)
        label.setObjectName("rowLabel")
        label.setFixedWidth(58)
        if buddy is not None:
            label.setBuddy(buddy)
        return label

    def _wrap_panel(self, inner_layout):
        frame = QFrame()
        frame.setObjectName("panel")
        frame.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        wrap = QVBoxLayout(frame)
        wrap.setContentsMargins(18, 16, 18, 16)
        wrap.setSpacing(12)
        wrap.addLayout(inner_layout)
        return frame

    def log(self, message, level="info"):
        if not message:
            return
        colors = {
            "info": "#9a9aa2",
            "ok": "#86c994",
            "warn": "#d4b56a",
            "error": "#e89090",
            "raw": "#c4c4ca",
        }
        stamp = datetime.now().strftime("%H:%M:%S")
        color = colors.get(level, colors["info"])
        self.log_output.append(
            f'<span style="color:#5c5c64">{stamp}</span>'
            f'&nbsp;&nbsp;<span style="color:{color}">{html.escape(str(message))}</span>'
        )
        self.log_output.verticalScrollBar().setValue(
            self.log_output.verticalScrollBar().maximum()
        )
        if level in ("error", "warn", "ok") and not self._busy:
            self.status_label.setText(str(message))

    def set_status(self, text):
        self.status_label.setText(text)

    def warn_if_ffmpeg_missing(self):
        if self._warned_ffmpeg or ffmpeg_available():
            return
        self._warned_ffmpeg = True
        self.log(
            "ffmpeg was not found on PATH. Some formats need it to merge video and audio.",
            "warn",
        )

    def check_and_install_ytdlp(self):
        exe_name = self._ytdlp_exe_name()
        exe_path = self.resolve_ytdlp_path()
        if exe_path:
            self.start_update(auto=True)
            return

        local_path = os.path.join(self._install_dir(), exe_name)
        self.log(f"{exe_name} not found. Downloading automatically…", "warn")
        self.download_btn.setEnabled(False)
        self.update_btn.setEnabled(False)
        self._show_progress(determinate=True, value=0, text="Downloading yt-dlp: %p%")
        self.set_status("Downloading yt-dlp…")

        self.install_thread = InstallThread(local_path, platform.system())
        self.install_thread.progress_percent.connect(self._install_progress)
        self.install_thread.finished.connect(self._install_finished)
        self.install_thread.error.connect(self._install_error)
        self.install_thread.start()

    def _install_progress(self, percent):
        self.progress_bar.setValue(percent)
        self.progress_bar.setFormat(f"Downloading yt-dlp: {percent}%")
        self.set_status(f"Downloading yt-dlp… {percent}%")

    def _install_finished(self, path):
        self.log(f"{os.path.basename(path)} downloaded and installed.", "ok")
        self._hide_progress()
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)
        self.start_update(auto=True)

    def _install_error(self, message):
        self.log(f"Failed to download yt-dlp: {message}", "error")
        self.log("Download it manually from https://github.com/yt-dlp/yt-dlp/releases", "info")
        self._hide_progress()
        self.download_btn.setEnabled(True)
        self.update_btn.setEnabled(True)

    def init_ui(self):
        self.setWindowTitle(WINDOW_TITLE)
        self.setMinimumSize(880, 620)
        self.resize(980, 700)
        self.setAcceptDrops(True)
        self.setWindowIcon(make_app_icon())

        self._build_menubar()

        root = QWidget()
        root.setObjectName("root")
        self.setCentralWidget(root)

        layout = QVBoxLayout(root)
        layout.setContentsMargins(24, 16, 24, 10)
        layout.setSpacing(16)

        layout.addLayout(self._build_url_row())
        layout.addLayout(self._build_save_row())
        layout.addLayout(self._build_options_row())
        layout.addLayout(self._build_activity_header())
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(6)
        layout.addWidget(self.progress_bar)

        self.log_output = QTextEdit()
        self.log_output.setObjectName("logView")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("yt-dlp output will appear here")
        self.log_output.setToolTip("yt-dlp output")
        self.log_output.setUndoRedoEnabled(False)
        self.log_output.document().setMaximumBlockCount(4000)
        self.log_output.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        log_palette = self.log_output.palette()
        log_palette.setColor(QPalette.Text, QColor("#c4c4ca"))
        log_palette.setColor(QPalette.Base, QColor("#0c0c0e"))
        self.log_output.setPalette(log_palette)
        layout.addWidget(self.log_output, 1)

        self.status_label = QLabel("Ready")
        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setObjectName("versionLabel")
        self.statusBar().setSizeGripEnabled(True)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(version_label)

    def _build_menubar(self):
        file_menu = self.menuBar().addMenu("&File")

        choose_act = QAction("Choose folder…", self)
        choose_act.setShortcut(QKeySequence("Ctrl+Shift+O"))
        choose_act.triggered.connect(self.browse_output_dir)
        file_menu.addAction(choose_act)

        open_act = QAction("Open folder", self)
        open_act.setShortcut(QKeySequence("Ctrl+O"))
        open_act.triggered.connect(self.open_output_dir)
        file_menu.addAction(open_act)

        file_menu.addSeparator()
        quit_act = QAction("Quit", self)
        quit_act.setShortcut(QKeySequence.Quit)
        quit_act.triggered.connect(self.close)
        file_menu.addAction(quit_act)

        edit_menu = self.menuBar().addMenu("&Edit")
        paste_act = QAction("Paste URL", self)
        paste_act.setShortcut(QKeySequence("Ctrl+Shift+V"))
        paste_act.triggered.connect(self.paste_from_clipboard)
        edit_menu.addAction(paste_act)

        clear_act = QAction("Clear activity", self)
        clear_act.setShortcut(QKeySequence("Ctrl+L"))
        clear_act.triggered.connect(self.clear_log)
        edit_menu.addAction(clear_act)

        help_menu = self.menuBar().addMenu("&Help")
        update_act = QAction("Check for updates", self)
        update_act.triggered.connect(self.start_update)
        help_menu.addAction(update_act)
        about_act = QAction("About yt-dlp", self)
        about_act.triggered.connect(self.show_about)
        help_menu.addAction(about_act)

    def _build_url_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.url_input = QLineEdit()
        self.url_input.setObjectName("urlField")
        self.url_input.setPlaceholderText("Paste or drop a video URL")
        self.url_input.setMinimumHeight(36)
        self.url_input.setClearButtonEnabled(True)
        self.url_input.setToolTip("Video or playlist URL. Drag-and-drop also works.")
        self.url_input.returnPressed.connect(self.start_download)

        paste_btn = QPushButton("Paste")
        paste_btn.setObjectName("secondary_btn")
        paste_btn.setFixedWidth(76)
        paste_btn.setMinimumHeight(36)
        paste_btn.setToolTip("Paste clipboard text into the URL field")
        paste_btn.clicked.connect(self.paste_from_clipboard)

        self.download_btn = QPushButton("Download")
        self.download_btn.setObjectName("download_btn")
        self.download_btn.setCursor(Qt.PointingHandCursor)
        self.download_btn.setDefault(True)
        self.download_btn.setMinimumHeight(36)
        self.download_btn.setMinimumWidth(112)
        self.download_btn.setToolTip("Start download (Enter)")
        self.download_btn.clicked.connect(self.start_download)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("cancel_btn")
        self.cancel_btn.setCursor(Qt.PointingHandCursor)
        self.cancel_btn.setMinimumHeight(36)
        self.cancel_btn.setMinimumWidth(112)
        self.cancel_btn.setToolTip("Cancel the download in progress (Esc)")
        self.cancel_btn.clicked.connect(self.cancel_download)
        self.cancel_btn.setVisible(False)

        row.addWidget(self._row_label("URL", self.url_input))
        row.addWidget(self.url_input, 1)
        row.addWidget(paste_btn)
        row.addWidget(self.download_btn)
        row.addWidget(self.cancel_btn)
        return row

    def _build_save_row(self):
        row = QHBoxLayout()
        row.setSpacing(8)
        self.output_path = QLineEdit()
        self.output_path.setText(os.getcwd())
        self.output_path.setReadOnly(True)
        self.output_path.setToolTip("Folder where files are saved")
        self.output_path.setMinimumHeight(36)

        browse_btn = QPushButton("Choose")
        browse_btn.setObjectName("secondary_btn")
        browse_btn.setMinimumHeight(36)
        browse_btn.setFixedWidth(76)
        browse_btn.clicked.connect(self.browse_output_dir)

        self.open_folder_btn = QPushButton("Reveal")
        self.open_folder_btn.setObjectName("secondary_btn")
        self.open_folder_btn.setMinimumHeight(36)
        self.open_folder_btn.setMinimumWidth(112)
        self.open_folder_btn.setToolTip("Open the save location in your file manager")
        self.open_folder_btn.clicked.connect(self.open_output_dir)

        row.addWidget(self._row_label("Save to", self.output_path))
        row.addWidget(self.output_path, 1)
        row.addWidget(browse_btn)
        row.addWidget(self.open_folder_btn)
        return row

    def _build_options_row(self):
        row = QHBoxLayout()
        row.setSpacing(12)
        row.addWidget(self._wrap_panel(self._build_format_column()), 1)
        row.addWidget(self._wrap_panel(self._build_extras_column()), 1)
        return row

    def _build_format_column(self):
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(self._section_title("Format"))

        self.format_combo = QComboBox()
        self.format_combo.addItems(["Best Quality", "1080p", "720p", "480p", "360p", "Audio Only"])
        self.format_combo.setToolTip("Cap video height, or extract audio only")
        self.format_combo.currentTextChanged.connect(self.sync_dependent_controls)

        self.video_format_combo = QComboBox()
        self.video_format_combo.addItems(["Auto (Best)", "MP4", "MKV", "WEBM"])
        self.video_format_combo.setToolTip(
            "Remux into this container without re-encoding. Re-encode only if you turn that option on."
        )
        self.video_format_combo.currentTextChanged.connect(self.sync_dependent_controls)

        self.audio_format_combo = QComboBox()
        self.audio_format_combo.addItems(["mp3", "m4a", "wav", "flac"])
        self.audio_format_combo.setToolTip("Used when extracting audio or when quality is Audio Only")

        self.speed_limit_spin = QSpinBox()
        self.speed_limit_spin.setRange(0, 100000)
        self.speed_limit_spin.setSpecialValueText("No limit")
        self.speed_limit_spin.setSuffix(" KB/s")
        self.speed_limit_spin.setToolTip("0 means unlimited")

        self.cookies_combo = QComboBox()
        self.cookies_combo.addItems(["None", "Chrome", "Firefox", "Safari", "Edge", "Brave", "Opera"])
        self.cookies_combo.setToolTip("Use browser cookies to bypass 403 errors and age-gates")

        for widget in (
            self.format_combo,
            self.video_format_combo,
            self.audio_format_combo,
            self.speed_limit_spin,
            self.cookies_combo,
        ):
            widget.setMinimumHeight(30)
            widget.setMinimumWidth(200)
            widget.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.recode_cb = QCheckBox("Re-encode if remux fails")
        self.recode_cb.setToolTip("Slower. Only needed if remuxing into the chosen container fails.")

        form = QFormLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setHorizontalSpacing(12)
        form.setVerticalSpacing(8)
        form.setLabelAlignment(Qt.AlignRight | Qt.AlignVCenter)
        form.setFieldGrowthPolicy(QFormLayout.FieldsStayAtSizeHint)
        form.addRow(self._field_label("Quality", self.format_combo), self.format_combo)
        form.addRow(self._field_label("Container", self.video_format_combo), self.video_format_combo)
        form.addRow("", self.recode_cb)
        form.addRow(self._field_label("Audio", self.audio_format_combo), self.audio_format_combo)
        form.addRow(self._field_label("Rate limit", self.speed_limit_spin), self.speed_limit_spin)
        form.addRow(self._field_label("Cookies", self.cookies_combo), self.cookies_combo)
        col.addLayout(form)
        col.addStretch()
        return col

    def _build_extras_column(self):
        col = QVBoxLayout()
        col.setSpacing(10)
        col.addWidget(self._section_title("Extras"))

        self.extract_audio_cb = QCheckBox("Extract audio")
        self.subtitle_cb = QCheckBox("Subtitles")
        self.auto_sub_cb = QCheckBox("Auto-captions")
        self.thumbnail_cb = QCheckBox("Thumbnail")
        self.description_cb = QCheckBox("Description")
        self.playlist_cb = QCheckBox("Download playlist")
        self.extract_audio_cb.setToolTip("Download audio only in the selected audio format")
        self.playlist_cb.setToolTip("Download every video in a playlist instead of a single item")
        self.auto_sub_cb.setToolTip("Include auto-generated captions even if official subs are missing")
        self.extract_audio_cb.toggled.connect(self.sync_dependent_controls)
        self.playlist_cb.toggled.connect(self.sync_dependent_controls)

        grid = QGridLayout()
        grid.setContentsMargins(0, 0, 0, 0)
        grid.setHorizontalSpacing(16)
        grid.setVerticalSpacing(8)
        grid.addWidget(self.extract_audio_cb, 0, 0)
        grid.addWidget(self.subtitle_cb, 0, 1)
        grid.addWidget(self.auto_sub_cb, 1, 0)
        grid.addWidget(self.thumbnail_cb, 1, 1)
        grid.addWidget(self.description_cb, 2, 0)
        grid.addWidget(self.playlist_cb, 2, 1)
        col.addLayout(grid)

        playlist_range = QHBoxLayout()
        playlist_range.setSpacing(8)
        playlist_range.addWidget(self._field_label("Items"))
        self.playlist_start_spin = QSpinBox()
        self.playlist_start_spin.setRange(0, 9999)
        self.playlist_start_spin.setSpecialValueText("First")
        self.playlist_start_spin.setToolTip("1-based start index. First means the beginning of the playlist.")
        playlist_range.addWidget(self.playlist_start_spin, 1)
        playlist_range.addWidget(self._field_label("–"))
        self.playlist_end_spin = QSpinBox()
        self.playlist_end_spin.setRange(0, 9999)
        self.playlist_end_spin.setSpecialValueText("Last")
        self.playlist_end_spin.setToolTip("1-based end index. Last means the end of the playlist.")
        playlist_range.addWidget(self.playlist_end_spin, 1)
        col.addLayout(playlist_range)
        col.addStretch()
        return col

    def _build_activity_header(self):
        row = QHBoxLayout()
        row.addWidget(self._section_title("Activity"))
        row.addStretch()
        self.update_btn = QPushButton("Check for updates")
        self.update_btn.setObjectName("linkBtn")
        self.update_btn.setCursor(Qt.PointingHandCursor)
        self.update_btn.setToolTip("Update the local yt-dlp binary")
        self.update_btn.clicked.connect(self.start_update)
        self.clear_btn = QPushButton("Clear")
        self.clear_btn.setObjectName("linkBtn")
        self.clear_btn.setCursor(Qt.PointingHandCursor)
        self.clear_btn.setToolTip("Clear the activity log (Ctrl+L)")
        self.clear_btn.clicked.connect(self.clear_log)
        row.addWidget(self.update_btn)
        row.addWidget(self.clear_btn)
        return row

    def apply_theme(self):
        self.setStyleSheet(app_stylesheet(make_check_icon_path(), make_chevron_icon_path()))

    def setup_shortcuts(self):
        download_shortcut = QShortcut(QKeySequence("Return"), self.url_input)
        download_shortcut.activated.connect(self.start_download)

        download_anywhere = QShortcut(QKeySequence("Ctrl+Return"), self)
        download_anywhere.activated.connect(self.start_download)

        cancel_shortcut = QShortcut(QKeySequence("Escape"), self)
        cancel_shortcut.activated.connect(self.cancel_download)

    def show_about(self):
        QMessageBox.about(
            self,
            "About yt-dlp",
            (
                f"<b>yt-dlp</b> {APP_VERSION}"
                "<p>A desktop front-end for yt-dlp — download video and audio "
                "from YouTube and many other sites.</p>"
                "<p>https://github.com/yt-dlp/yt-dlp</p>"
            ),
        )

    def showEvent(self, event):
        super().showEvent(event)
        if not self._did_initial_focus:
            self._did_initial_focus = True
            self.url_input.setFocus()

    def sync_dependent_controls(self, *_args):
        audio_mode = self.extract_audio_cb.isChecked() or self.format_combo.currentText() == "Audio Only"
        self.video_format_combo.setEnabled(not audio_mode)
        container_chosen = (not audio_mode) and self.video_format_combo.currentText() != "Auto (Best)"
        self.recode_cb.setEnabled(container_chosen)
        self.audio_format_combo.setEnabled(audio_mode)
        playlist_on = self.playlist_cb.isChecked()
        self.playlist_start_spin.setEnabled(playlist_on)
        self.playlist_end_spin.setEnabled(playlist_on)

    def collect_options(self):
        quality = self.format_combo.currentText()
        extract_audio = self.extract_audio_cb.isChecked() or quality == "Audio Only"
        start = self.playlist_start_spin.value()
        end = self.playlist_end_spin.value()
        return {
            "quality": quality,
            "extract_audio": extract_audio,
            "video_format": self.video_format_combo.currentText(),
            "audio_format": self.audio_format_combo.currentText(),
            "subtitle": self.subtitle_cb.isChecked(),
            "auto_sub": self.auto_sub_cb.isChecked(),
            "thumbnail": self.thumbnail_cb.isChecked(),
            "description": self.description_cb.isChecked(),
            "playlist": self.playlist_cb.isChecked(),
            "playlist_start": start,
            "playlist_end": end,
            "speed_limit": self.speed_limit_spin.value(),
            "cookies_browser": self.cookies_combo.currentText(),
            "recode": self.recode_cb.isChecked(),
        }

    def paste_from_clipboard(self):
        clipboard = QApplication.clipboard()
        text = (clipboard.text() or "").strip()
        if not text:
            return
        url = first_url_in_text(text)
        self.url_input.setText(url or text)
        self.url_input.setFocus()

    def check_clipboard(self):
        clipboard = QApplication.clipboard()
        text = clipboard.text() or ""
        if text == self.last_clipboard:
            return
        self.last_clipboard = text
        if self.url_input.text().strip():
            return
        url = first_url_in_text(text)
        if url:
            self.url_input.setText(url)

    def dragEnterEvent(self, event):
        mime = event.mimeData()
        if mime.hasUrls() or mime.hasText():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        mime = event.mimeData()
        candidates = []
        if mime.hasUrls():
            candidates.extend(url.toString() for url in mime.urls())
        if mime.hasText():
            candidates.append(mime.text())
        for item in candidates:
            url = first_url_in_text(item)
            if url:
                self.url_input.setText(url)
                event.acceptProposedAction()
                return
        event.ignore()

    def load_settings(self):
        last_dir = self.settings.value("output_dir", os.getcwd())
        self.output_path.setText(last_dir)
        self.format_combo.setCurrentIndex(self.settings.value("format_index", 0, type=int))
        self.video_format_combo.setCurrentIndex(self.settings.value("video_format_index", 0, type=int))
        self.audio_format_combo.setCurrentIndex(self.settings.value("audio_format_index", 0, type=int))
        self.extract_audio_cb.setChecked(self.settings.value("extract_audio", False, type=bool))
        self.subtitle_cb.setChecked(self.settings.value("subtitle", False, type=bool))
        self.auto_sub_cb.setChecked(self.settings.value("auto_sub", False, type=bool))
        self.thumbnail_cb.setChecked(self.settings.value("thumbnail", False, type=bool))
        self.description_cb.setChecked(self.settings.value("description", False, type=bool))
        self.playlist_cb.setChecked(self.settings.value("playlist", False, type=bool))
        self.playlist_start_spin.setValue(self.settings.value("playlist_start", 0, type=int))
        self.playlist_end_spin.setValue(self.settings.value("playlist_end", 0, type=int))
        self.speed_limit_spin.setValue(self.settings.value("speed_limit", 0, type=int))
        self.cookies_combo.setCurrentIndex(self.settings.value("cookies_index", 0, type=int))
        self.recode_cb.setChecked(self.settings.value("recode", False, type=bool))

    def save_settings(self):
        self.settings.setValue("output_dir", self.output_path.text())
        self.settings.setValue("format_index", self.format_combo.currentIndex())
        self.settings.setValue("video_format_index", self.video_format_combo.currentIndex())
        self.settings.setValue("audio_format_index", self.audio_format_combo.currentIndex())
        self.settings.setValue("extract_audio", self.extract_audio_cb.isChecked())
        self.settings.setValue("subtitle", self.subtitle_cb.isChecked())
        self.settings.setValue("auto_sub", self.auto_sub_cb.isChecked())
        self.settings.setValue("thumbnail", self.thumbnail_cb.isChecked())
        self.settings.setValue("description", self.description_cb.isChecked())
        self.settings.setValue("playlist", self.playlist_cb.isChecked())
        self.settings.setValue("playlist_start", self.playlist_start_spin.value())
        self.settings.setValue("playlist_end", self.playlist_end_spin.value())
        self.settings.setValue("speed_limit", self.speed_limit_spin.value())
        self.settings.setValue("cookies_index", self.cookies_combo.currentIndex())
        self.settings.setValue("recode", self.recode_cb.isChecked())

    def browse_output_dir(self):
        directory = QFileDialog.getExistingDirectory(self, "Save downloads to", self.output_path.text())
        if directory:
            self.output_path.setText(directory)
            self.settings.setValue("output_dir", directory)

    def open_output_dir(self):
        directory = self.output_path.text().strip() or os.getcwd()
        if not os.path.isdir(directory):
            self.log(f"Folder does not exist: {directory}", "error")
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(os.path.abspath(directory)))

    def _show_progress(self, determinate=True, value=0, text=""):
        self.progress_bar.setVisible(True)
        if determinate:
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(value)
        else:
            self.progress_bar.setRange(0, 0)
        if text:
            self.progress_bar.setFormat(text)

    def _hide_progress(self):
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        if not self._busy:
            self.set_status("Ready")

    def start_download(self):
        url = self.url_input.text().strip()
        if not url:
            self.log("Enter a URL to download", "error")
            self.url_input.setFocus()
            return

        if not is_valid_url(url):
            self.log("That does not look like an http:// or https:// URL", "error")
            self.url_input.setFocus()
            self.url_input.selectAll()
            return

        if self.download_thread and self.download_thread.isRunning():
            self.log("A download is already in progress", "error")
            return

        if self.update_thread and self.update_thread.isRunning():
            self.log("Wait for the yt-dlp update to finish before downloading", "error")
            return

        if self.install_thread and self.install_thread.isRunning():
            self.log("Wait for yt-dlp to finish installing", "error")
            return

        options = self.collect_options()
        if options["playlist"] and options["playlist_end"] and options["playlist_start"]:
            if options["playlist_end"] < options["playlist_start"]:
                self.log("Playlist end must be greater than or equal to start", "error")
                return

        exe_path = self.resolve_ytdlp_path()
        if not exe_path:
            self.log(
                f"{self._ytdlp_exe_name()} not found. Install it or place it in the app directory.",
                "error",
            )
            return

        output_dir = self.output_path.text().strip() or os.getcwd()
        if not os.path.isdir(output_dir):
            try:
                os.makedirs(output_dir, exist_ok=True)
            except OSError as e:
                self.log(f"Cannot create output folder: {e}", "error")
                return

        self.save_settings()

        self.log(f"Starting download: {url}", "info")
        self.log(f"Saving to {output_dir}", "info")
        self.log(f"Using {exe_path}", "info")

        self.download_thread = DownloadThread(exe_path, url, options, output_dir)
        self.download_thread.progress.connect(self.update_log)
        self.download_thread.progress_percent.connect(self.update_progress)
        self.download_thread.progress_status.connect(self.update_progress_status)
        self.download_thread.finished.connect(self.download_finished)
        self.download_thread.error.connect(self.download_error)

        self._busy = True
        self.download_btn.setVisible(False)
        self.cancel_btn.setVisible(True)
        self._show_progress(determinate=True, value=0, text="Starting…")
        self.set_status("Downloading…")
        self.setWindowTitle(f"{WINDOW_TITLE} — downloading")

        self.download_thread.start()

    def cancel_download(self):
        if self.download_thread and self.download_thread.isRunning():
            self.log("Cancelling download…", "warn")
            self.download_thread.cancel()
            self.cancel_btn.setEnabled(False)
            self.set_status("Cancelling…")

    def update_progress(self, percent):
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(percent)

    def update_progress_status(self, status):
        self.progress_bar.setFormat(status)
        self.set_status(status)
        self.setWindowTitle(f"{WINDOW_TITLE} — {status}")

    def update_log(self, message):
        if self._auto_updating:
            return
        upper = message.upper()
        if "ERROR:" in upper or upper.startswith("ERROR"):
            level = "error"
        elif "WARNING:" in upper:
            level = "warn"
        else:
            level = "raw"
        self.log(message, level)

    def download_finished(self, message):
        self.log(message, "ok")
        self.reset_download_ui()

    def download_error(self, message):
        self.log(message, "error")
        self.reset_download_ui()

    def reset_download_ui(self):
        self._busy = False
        self.download_btn.setVisible(True)
        self.cancel_btn.setVisible(False)
        self.cancel_btn.setEnabled(True)
        self._hide_progress()
        self.setWindowTitle(WINDOW_TITLE)

    def start_update(self, auto=False):
        if self.download_thread and self.download_thread.isRunning():
            if not auto:
                self.log("Wait for the current download to finish before updating yt-dlp", "error")
            return
        if self.update_thread and self.update_thread.isRunning():
            if not auto:
                self.log("An update is already in progress", "error")
            return

        exe_path = self.resolve_ytdlp_path()
        if not exe_path:
            if not auto:
                self.log(
                    f"{self._ytdlp_exe_name()} not found. Install it, or place a copy "
                    "next to the app or in the dropdlp data folder.",
                    "error",
                )
            return

        self._auto_updating = auto
        if auto:
            self.set_status("Checking for yt-dlp updates…")
        else:
            self.log("Checking for yt-dlp updates…", "info")
            self.set_status("Checking for yt-dlp updates…")

        self.update_thread = UpdateThread(exe_path)
        self.update_thread.progress.connect(self.update_log)
        self.update_thread.finished.connect(self.update_finished)
        self.update_thread.error.connect(self.update_error)

        self.update_btn.setText("Checking…")
        self.update_btn.setEnabled(False)
        self.download_btn.setEnabled(False)
        if not auto:
            self._show_progress(determinate=False)

        self.update_thread.start()

    def update_finished(self, message):
        prefix = "Startup update: " if self._auto_updating else ""
        self.log(f"{prefix}{message}".rstrip("."), "ok")
        self._auto_updating = False
        self.update_btn.setText("Check for updates")
        self.update_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        if not self._busy:
            self._hide_progress()

    def update_error(self, message):
        if self._auto_updating:
            self.log(f"Startup update skipped: {message}", "warn")
            self.log('Downloads still work. Use "Check for updates" later if needed.', "info")
        else:
            self.log(message, "error")
        self._auto_updating = False
        self.update_btn.setText("Check for updates")
        self.update_btn.setEnabled(True)
        self.download_btn.setEnabled(True)
        if not self._busy:
            self._hide_progress()

    def clear_log(self):
        self.log_output.clear()

    def closeEvent(self, event):
        self.save_settings()
        for thread in (self.download_thread, self.update_thread, self.install_thread):
            if thread and thread.isRunning():
                if hasattr(thread, "cancel"):
                    thread.cancel()
                thread.wait(4000)
        event.accept()


# Back-compat for tests and external imports
ModernYTDLPGUI = YTDLPWindow


def main(argv=None):
    argv = list(sys.argv if argv is None else argv)
    smoke = "--smoke-test" in argv
    if smoke:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        argv = [item for item in argv if item != "--smoke-test"]
        sys.argv = argv

    if hasattr(Qt, "AA_EnableHighDpiScaling"):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, "AA_UseHighDpiPixmaps"):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(argv)
    app.setStyle("Fusion")
    app.setFont(preferred_ui_font())
    apply_dark_palette(app)
    app.setWindowIcon(make_app_icon())
    app.setApplicationName("dropdlp")
    app.setApplicationVersion(APP_VERSION)
    app.setOrganizationName("dropdlp")

    window = YTDLPWindow(skip_startup=smoke)
    if smoke:
        window.collect_options()
        marker = os.environ.get("DROP_DLP_SMOKE_MARKER")
        if marker:
            with open(marker, "w", encoding="utf-8") as handle:
                handle.write(f"ok {APP_VERSION}\n")
        print(f"smoke-test ok {APP_VERSION}", flush=True)
        return 0

    window.show()
    return app.exec_()


if __name__ == "__main__":
    sys.exit(main())
