from __future__ import annotations

import ctypes
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path


APP_NAME = "Quant Hunter"
INSTALL_DIR = Path(os.environ.get("LocalAppData", "")) / "Programs" / "QuantHunter"
DESKTOP_LINK = Path(os.environ.get("UserProfile", "")) / "Desktop" / "Quant Hunter.lnk"
START_MENU_LINK = (
    Path(os.environ.get("AppData", ""))
    / "Microsoft"
    / "Windows"
    / "Start Menu"
    / "Programs"
    / "Quant Hunter.lnk"
)


def _message_box(message: str, title: str, *, error: bool = False) -> None:
    flags = 0x10 if error else 0x40
    try:
        ctypes.windll.user32.MessageBoxW(None, message, title, flags)
    except Exception:
        pass


def _bundle_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", "")
    if meipass:
        return Path(meipass)
    return Path(__file__).resolve().parent


def _portable_zip_path() -> Path:
    path = _bundle_root() / "quant_hunter_portable.zip"
    if not path.exists():
        raise FileNotFoundError(f"Portable package not found: {path}")
    return path


def _create_shortcuts(target_exe: Path) -> None:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if not powershell:
        return
    command = (
        "$ws = New-Object -ComObject WScript.Shell; "
        f"$desktop = $ws.CreateShortcut('{DESKTOP_LINK}'); "
        f"$desktop.TargetPath = '{target_exe}'; "
        f"$desktop.WorkingDirectory = '{target_exe.parent}'; "
        f"$desktop.IconLocation = '{target_exe}'; "
        "$desktop.Save(); "
        f"$start = $ws.CreateShortcut('{START_MENU_LINK}'); "
        f"$start.TargetPath = '{target_exe}'; "
        f"$start.WorkingDirectory = '{target_exe.parent}'; "
        f"$start.IconLocation = '{target_exe}'; "
        "$start.Save();"
    )
    subprocess.run([powershell, "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", command], check=False)


def _install() -> Path:
    portable_zip = _portable_zip_path()
    INSTALL_DIR.parent.mkdir(parents=True, exist_ok=True)
    if INSTALL_DIR.exists():
        shutil.rmtree(INSTALL_DIR, ignore_errors=True)
    INSTALL_DIR.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(portable_zip) as archive:
        archive.extractall(INSTALL_DIR)
    target_exe = INSTALL_DIR / "quant_hunter.exe"
    if not target_exe.exists():
        raise FileNotFoundError(f"Installed executable not found: {target_exe}")
    START_MENU_LINK.parent.mkdir(parents=True, exist_ok=True)
    _create_shortcuts(target_exe)
    return target_exe


def main() -> int:
    try:
        target_exe = _install()
    except Exception as exc:
        _message_box(f"{APP_NAME} installation failed.\n\n{exc}", APP_NAME, error=True)
        return 1

    subprocess.Popen([str(target_exe)], cwd=str(target_exe.parent))
    _message_box(
        f"{APP_NAME} installed successfully.\n\nLocation:\n{INSTALL_DIR}",
        APP_NAME,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
