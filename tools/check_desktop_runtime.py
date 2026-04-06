from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path


def _python_root() -> Path:
    return Path(sys.executable).resolve().parent


def _runtime_snapshot() -> dict[str, object]:
    root = _python_root()
    tcl_dir = root / "tcl" / "tcl8.6"
    tk_dir = root / "tcl" / "tk8.6"
    if tcl_dir.exists() and "TCL_LIBRARY" not in os.environ:
        os.environ["TCL_LIBRARY"] = str(tcl_dir)
    if tk_dir.exists() and "TK_LIBRARY" not in os.environ:
        os.environ["TK_LIBRARY"] = str(tk_dir)
    snapshot: dict[str, object] = {
        "python_executable": str(sys.executable),
        "python_version": sys.version,
        "tcl_dir_exists": tcl_dir.exists(),
        "tk_dir_exists": tk_dir.exists(),
        "tcl_init_exists": (tcl_dir / "init.tcl").exists(),
        "tk_init_exists": (tk_dir / "tk.tcl").exists(),
        "tcl_library_env": os.environ.get("TCL_LIBRARY", ""),
        "tk_library_env": os.environ.get("TK_LIBRARY", ""),
        "pyinstaller_installed": importlib.util.find_spec("PyInstaller") is not None,
    }
    try:
        import tkinter as tk

        snapshot["tkinter_importable"] = True
        try:
            root_window = tk.Tk()
        except Exception as exc:  # pragma: no cover - environment diagnostic only
            snapshot["tk_root_ok"] = False
            snapshot["tk_error"] = str(exc)
        else:
            snapshot["tk_root_ok"] = True
            snapshot["tk_patchlevel"] = root_window.tk.call("info", "patchlevel")
            root_window.destroy()
    except Exception as exc:  # pragma: no cover - environment diagnostic only
        snapshot["tkinter_importable"] = False
        snapshot["tk_root_ok"] = False
        snapshot["tk_error"] = str(exc)
    return snapshot


if __name__ == "__main__":
    print(json.dumps(_runtime_snapshot(), ensure_ascii=False, indent=2))
