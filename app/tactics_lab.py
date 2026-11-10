"""FM27 Tactics Lab: a local tactics board that reads your Football Manager saves.

Run it, and it serves the Lab on http://127.0.0.1:27427 and opens your browser. The Lab can
list your FM27 saves and read the squad (attributes, position ratings, CA/PA) straight from
the .fm file. Nothing is uploaded: the server only listens on this computer.
"""

from __future__ import annotations

import json
import os
import re
import sys
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import lab_reader

APP_NAME = "FM27 Tactics Lab"
HOST = "127.0.0.1"
PORTS = range(27427, 27437)  # a fixed port keeps the browser's saved data between runs
GAME_DIRS = ("Football Manager 27", "Football Manager 2027")


def resource(name: str) -> Path:
    """A bundled file, both when run from source and from the PyInstaller exe."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent))
    return base / name


def documents_dirs() -> list[Path]:
    """Every Documents folder the game might use, OneDrive-redirected ones included."""
    home = Path.home()
    found: list[Path] = []
    if sys.platform == "win32":
        try:
            import ctypes
            from ctypes import wintypes

            class GUID(ctypes.Structure):
                _fields_ = [("a", wintypes.DWORD), ("b", wintypes.WORD), ("c", wintypes.WORD), ("d", ctypes.c_ubyte * 8)]

            # FOLDERID_Documents {FDD39AD0-238F-46AF-ADB4-6C85480369C7}
            fid = GUID(0xFDD39AD0, 0x238F, 0x46AF, (ctypes.c_ubyte * 8)(0xAD, 0xB4, 0x6C, 0x85, 0x48, 0x03, 0x69, 0xC7))
            out = ctypes.c_wchar_p()
            if ctypes.windll.shell32.SHGetKnownFolderPath(ctypes.byref(fid), 0, None, ctypes.byref(out)) == 0:
                found.append(Path(out.value))
                ctypes.windll.ole32.CoTaskMemFree(out)
        except Exception:
            pass
    for env in ("OneDrive", "OneDriveConsumer", "OneDriveCommercial"):
        if os.environ.get(env):
            found.append(Path(os.environ[env]) / "Documents")
    found += [home / "OneDrive" / "Documents", home / "Documents"]
    if sys.platform == "darwin":
        found.append(home / "Library" / "Application Support")
    return found


def save_folders() -> list[Path]:
    """Folders that hold FM27 saves, from the usual places and the game's own last-save record."""
    folders: list[Path] = []
    for docs in documents_dirs():
        for game in GAME_DIRS:
            folders.append(docs / "Sports Interactive" / game / "games")
    local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    for game in GAME_DIRS:
        prefs = local / "Sports Interactive" / game / "Preferences"
        folders.append(local / "Sports Interactive" / game / "cloud" / "games")
        if prefs.is_dir():
            for record in prefs.rglob("last_saved_*.xml"):
                try:
                    match = re.search(r'value="([^"]+\.fm)"', record.read_text(errors="ignore"))
                except OSError:
                    continue
                if match:
                    folders.append(Path(match.group(1)).parent)
    extra = os.environ.get("FM_SAVES_DIR")
    if extra:
        folders.insert(0, Path(extra))
    unique: list[Path] = []
    for folder in folders:
        try:
            resolved = folder.resolve()
        except OSError:
            continue
        if resolved.is_dir() and resolved not in unique:
            unique.append(resolved)
    return unique


def list_saves() -> list[dict[str, object]]:
    saves = []
    for folder in save_folders():
        for path in folder.glob("*.fm"):
            try:
                stat = path.stat()
            except OSError:
                continue
            saves.append({"path": str(path), "name": path.stem, "folder": str(folder),
                          "size": stat.st_size, "modified": stat.st_mtime})
    saves.sort(key=lambda s: s["modified"], reverse=True)
    return saves


_read_lock = threading.Lock()


class Handler(BaseHTTPRequestHandler):
    server_version = "FM27TacticsLab/1"

    def log_message(self, *args: object) -> None:  # keep the console tidy
        pass

    def _send(self, code: int, body: bytes, ctype: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _json(self, data: object, code: int = 200) -> None:
        self._send(code, json.dumps(data).encode(), "application/json")

    def do_GET(self) -> None:
        # Only answer requests addressed to this machine, so other sites can't use the API.
        host = (self.headers.get("Host") or "").split(":")[0]
        if host not in (HOST, "localhost"):
            return self._send(403, b"forbidden", "text/plain")
        url = urlparse(self.path)
        if url.path in ("/", "/index.html"):
            return self._send(200, resource("web/index.html").read_bytes(), "text/html; charset=utf-8")
        if url.path == "/api/ping":
            return self._json({"app": APP_NAME, "local": True})
        if url.path == "/api/saves":
            return self._json({"saves": list_saves(), "folders": [str(f) for f in save_folders()]})
        if url.path == "/api/read":
            query = parse_qs(url.query)
            path = Path(query.get("path", [""])[0])
            scope = query.get("scope", ["squad"])[0]
            if path.suffix.lower() != ".fm" or not path.is_file():
                return self._json({"error": "Pick a .fm save file."}, 400)
            print(f"Reading {path.name} ...", flush=True)
            started = time.time()
            with _read_lock:
                result = lab_reader.safe_read(str(path), "all" if scope == "all" else "squad")
            print(f"  done in {time.time() - started:.1f}s", flush=True)
            return self._send(200, result.encode(), "application/json")
        self._send(404, b"not found", "text/plain")


def selftest() -> int:
    """Used by the build: check the bundled page and the save reader load."""
    import fmsave
    page = resource("web/index.html")
    ok = page.is_file() and b"FM27 Tactics Lab" in page.read_bytes()
    print(f"fmsave {fmsave.__version__}; page {'ok' if ok else 'MISSING'}")
    return 0 if ok else 1


def main() -> None:
    if "--selftest" in sys.argv:
        sys.exit(selftest())
    server = None
    for port in PORTS:
        try:
            server = ThreadingHTTPServer((HOST, port), Handler)
            break
        except OSError:
            continue
    if server is None:
        print("Could not open a local port. Is the Lab already running?")
        input("Press Enter to close.")
        return
    url = f"http://{HOST}:{server.server_address[1]}/"
    print(f"{APP_NAME} is running at {url}")
    folders = save_folders()
    print("Save folders found:" if folders else "No FM27 save folders found yet.")
    for folder in folders:
        print(f"  {folder}")
    print("\nKeep this window open while you use the Lab. Close it to quit.")
    if "--no-browser" not in sys.argv:
        threading.Timer(0.6, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
