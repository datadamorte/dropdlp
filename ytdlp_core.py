"""Shared, Qt-free helpers for locating yt-dlp and building its command line."""

from __future__ import annotations

import os
import platform
import re
import shutil
import signal
import stat
import subprocess
import sys
import urllib.request
from dataclasses import dataclass
from typing import Callable, Iterable, Optional
from urllib.parse import urlparse

APP_NAME = "dropdlp"
APP_VERSION = "1.3.0"
USER_AGENT = f"{APP_NAME}/{APP_VERSION}"
OUTPUT_TEMPLATE = "%(title)s [%(id)s].%(ext)s"
PLAYLIST_TEMPLATE = os.path.join(
    "%(playlist_title|NA)s",
    "%(playlist_index)03d - %(title)s [%(id)s].%(ext)s",
)

PERCENT_RE = re.compile(r"(^|\s)(\d+(?:\.\d+)?)%")
SPEED_RE = re.compile(r"at\s+(\S+/s)")
ETA_RE = re.compile(r"ETA\s+(\S+)")
DEST_RE = re.compile(r"\[download\] Destination:\s+(.+)$")


def ytdlp_exe_name(system: Optional[str] = None) -> str:
    system = system or platform.system()
    return "yt-dlp.exe" if system == "Windows" else "yt-dlp"


def ytdlp_release_url(system: Optional[str] = None) -> str:
    system = system or platform.system()
    if system == "Windows":
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"
    if system == "Darwin":
        return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp_macos"
    return "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp"


def is_runnable_ytdlp(path: str, timeout: float = 8.0) -> bool:
    """Return True if path looks like a yt-dlp executable that can actually start."""
    if not path or not os.path.isfile(path):
        return False
    kwargs = {
        "capture_output": True,
        "text": True,
        "timeout": timeout,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    try:
        result = subprocess.run([path, "--version"], **kwargs)
    except (OSError, subprocess.TimeoutExpired, ValueError):
        return False
    return result.returncode == 0


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def executable_dir() -> str:
    """Directory containing this process's executable (or the source file)."""
    if is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return os.path.dirname(os.path.abspath(__file__))


def portable_root() -> str:
    """User-visible folder next to the exe, or next to the .app on macOS."""
    exe_dir = executable_dir()
    if os.path.basename(exe_dir) == "MacOS":
        contents = os.path.dirname(exe_dir)
        if os.path.basename(contents) == "Contents":
            return os.path.dirname(os.path.dirname(contents))
    return exe_dir


def ytdlp_install_dir(system: Optional[str] = None, home: Optional[str] = None) -> str:
    """Writable location for the downloaded yt-dlp binary (not inside a .app)."""
    system = system or platform.system()
    home = os.path.abspath(home or os.path.expanduser("~"))
    if system == "Darwin":
        return os.path.join(home, "Library", "Application Support", APP_NAME)
    if system == "Windows":
        base = os.environ.get("LOCALAPPDATA") or home
        return os.path.join(base, APP_NAME)
    xdg = os.environ.get("XDG_DATA_HOME")
    if xdg:
        return os.path.join(xdg, APP_NAME)
    return os.path.join(home, ".local", "share", APP_NAME)


def resolve_ytdlp_path(
    app_dir: str,
    cwd: Optional[str] = None,
    *,
    extra_dirs: Optional[Iterable[str]] = None,
    which: Callable[[str], Optional[str]] = shutil.which,
    system: Optional[str] = None,
    is_runnable: Callable[[str], bool] = is_runnable_ytdlp,
) -> Optional[str]:
    """Find a working yt-dlp next to the app, in extra dirs, in cwd, or on PATH."""
    exe_name = ytdlp_exe_name(system)
    candidates = [os.path.join(app_dir, exe_name)]
    for folder in extra_dirs or ():
        if folder:
            candidates.append(os.path.join(folder, exe_name))
    if cwd:
        candidates.append(os.path.join(cwd, exe_name))
    seen = set()
    for path in candidates:
        if path in seen:
            continue
        seen.add(path)
        if os.path.isfile(path) and is_runnable(path):
            return path
    found = which(exe_name)
    if found and is_runnable(found):
        return found
    return None


def is_valid_url(url: str) -> bool:
    if not url or not isinstance(url, str):
        return False
    try:
        result = urlparse(url.strip())
        return bool(result.scheme and result.netloc) and result.scheme in ("http", "https")
    except ValueError:
        return False


def first_url_in_text(text: str) -> Optional[str]:
    """Return the first http(s) URL in free text (clipboard, drag-and-drop)."""
    if not text:
        return None
    for token in text.replace("\n", " ").split():
        token = token.strip("<>\"'")
        if is_valid_url(token):
            return token
    return None


def build_format_selector(quality_text: str, extract_audio: bool) -> Optional[str]:
    if extract_audio or quality_text == "Audio Only":
        return "bestaudio/best"
    if quality_text.endswith("p") and quality_text[:-1].isdigit():
        height = quality_text[:-1]
        return (
            f"bestvideo[height<={height}]+bestaudio/"
            f"best[height<={height}]/best"
        )
    return None


def build_ytdlp_command(
    exe_path: str,
    url: str,
    options: dict,
    output_path: Optional[str],
    *,
    system: Optional[str] = None,
) -> list[str]:
    """Build a yt-dlp argv. Does not recode video unless options['recode'] is true."""
    system = system or platform.system()
    extract_audio = bool(options.get("extract_audio"))
    quality = options.get("quality") or ""

    cmd = [
        exe_path,
        "--newline",
        "--no-colors",
        "--progress",
        "--no-update",
        "--retries",
        "10",
        "--fragment-retries",
        "10",
    ]

    format_spec = options.get("format") or build_format_selector(quality, extract_audio)
    if format_spec:
        cmd.extend(["-f", format_spec])

    if extract_audio or quality == "Audio Only":
        cmd.extend(["-x", "--audio-format", options.get("audio_format", "mp3")])
        cmd.extend(["--audio-quality", "0"])
    else:
        video_format = options.get("video_format")
        if video_format and video_format != "Auto (Best)":
            container = video_format.lower()
            cmd.extend(["--merge-output-format", container])
            if options.get("recode"):
                cmd.extend(["--recode-video", container])

    if options.get("subtitle"):
        cmd.append("--write-subs")
    if options.get("auto_sub"):
        cmd.append("--write-auto-subs")
    if options.get("thumbnail"):
        cmd.append("--write-thumbnail")
    if options.get("description"):
        cmd.append("--write-description")

    if options.get("playlist"):
        cmd.extend(["--yes-playlist", "--ignore-errors"])
        start = options.get("playlist_start") or 0
        end = options.get("playlist_end") or 0
        if start:
            cmd.extend(["--playlist-start", str(int(start))])
        if end:
            cmd.extend(["--playlist-end", str(int(end))])
    else:
        cmd.append("--no-playlist")

    speed_limit = options.get("speed_limit") or 0
    if speed_limit and int(speed_limit) > 0:
        cmd.extend(["-r", f"{int(speed_limit)}K"])

    cookies_browser = options.get("cookies_browser")
    if cookies_browser and cookies_browser != "None":
        cmd.extend(["--cookies-from-browser", str(cookies_browser).lower()])

    if options.get("impersonate"):
        # Needed for Cloudflare-protected sites (requires curl_cffi in yt-dlp).
        cmd.extend(["--extractor-args", "generic:impersonate"])

    if system == "Windows":
        cmd.append("--windows-filenames")

    if output_path:
        template = PLAYLIST_TEMPLATE if options.get("playlist") else OUTPUT_TEMPLATE
        cmd.extend(["-o", os.path.join(output_path, template)])

    cmd.append(url)
    return cmd


def popen_kwargs() -> dict:
    """Safe defaults for streaming yt-dlp output from a GUI worker."""
    kwargs = {
        "stdout": subprocess.PIPE,
        "stderr": subprocess.STDOUT,
        "text": True,
        "bufsize": 1,
        "encoding": "utf-8",
        "errors": "replace",
    }
    if platform.system() == "Windows":
        kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0)
    else:
        kwargs["start_new_session"] = True
    return kwargs


def terminate_process(process: Optional[subprocess.Popen], timeout: float = 3.0) -> None:
    if process is None or process.poll() is not None:
        return
    try:
        if platform.system() == "Windows":
            process.terminate()
        else:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=timeout)
    except (subprocess.TimeoutExpired, ProcessLookupError, OSError):
        try:
            if platform.system() == "Windows":
                process.kill()
            else:
                os.killpg(os.getpgid(process.pid), signal.SIGKILL)
        except (ProcessLookupError, OSError):
            pass


@dataclass
class ProgressInfo:
    percent: Optional[int] = None
    speed: Optional[str] = None
    eta: Optional[str] = None
    destination: Optional[str] = None
    already_downloaded: bool = False
    postprocessing: bool = False


def parse_progress_line(line: str) -> Optional[ProgressInfo]:
    if not line:
        return None
    info = ProgressInfo()
    found = False

    percent_match = PERCENT_RE.search(line)
    if percent_match:
        try:
            info.percent = max(0, min(100, int(float(percent_match.group(2)))))
            found = True
        except ValueError:
            pass

    speed_match = SPEED_RE.search(line)
    if speed_match:
        info.speed = speed_match.group(1)
        found = True

    eta_match = ETA_RE.search(line)
    if eta_match:
        info.eta = eta_match.group(1)
        found = True

    dest_match = DEST_RE.search(line)
    if dest_match:
        info.destination = dest_match.group(1).strip()
        found = True

    if "has already been downloaded" in line:
        info.already_downloaded = True
        info.percent = 100
        found = True

    if any(tag in line for tag in ("[Merger]", "[ExtractAudio]", "[VideoConvertor]", "[Embed]")):
        info.postprocessing = True
        found = True

    return info if found else None


def ffmpeg_available(which: Callable[[str], Optional[str]] = shutil.which) -> bool:
    return which("ffmpeg") is not None


def make_executable(path: str, system: Optional[str] = None) -> None:
    system = system or platform.system()
    if system != "Windows":
        mode = os.stat(path).st_mode
        os.chmod(path, mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)


def download_file(
    url: str,
    dest: str,
    progress_cb: Optional[Callable[[int], None]] = None,
    timeout: int = 120,
    chunk_size: int = 64 * 1024,
) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=timeout) as response, open(dest, "wb") as out:
        total = int(response.headers.get("Content-Length") or 0)
        read = 0
        while True:
            chunk = response.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            read += len(chunk)
            if progress_cb and total:
                progress_cb(max(0, min(100, int(read * 100 / total))))
    if progress_cb:
        progress_cb(100)
