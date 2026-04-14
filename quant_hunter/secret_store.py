from __future__ import annotations

import base64
import ctypes
import os
from ctypes import wintypes

_DPAPI_PREFIX = "dpapi:v1:"
_CRYPTPROTECT_UI_FORBIDDEN = 0x01


class _DataBlob(ctypes.Structure):
    _fields_ = [
        ("cbData", wintypes.DWORD),
        ("pbData", ctypes.POINTER(ctypes.c_char)),
    ]


def _is_windows() -> bool:
    return os.name == "nt"


def _build_blob(data: bytes) -> tuple[_DataBlob, ctypes.Array[ctypes.c_char]]:
    buffer = ctypes.create_string_buffer(data)
    blob = _DataBlob(len(data), ctypes.cast(buffer, ctypes.POINTER(ctypes.c_char)))
    return blob, buffer


def _blob_to_bytes(blob: _DataBlob) -> bytes:
    if not blob.cbData or not blob.pbData:
        return b""
    return ctypes.string_at(blob.pbData, blob.cbData)


def _crypt_protect_data(data: bytes) -> bytes:
    if not _is_windows():
        raise OSError("DPAPI is only available on Windows.")
    if not data:
        return b""
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buffer = _build_blob(data)
    out_blob = _DataBlob()
    if not crypt32.CryptProtectData(
        ctypes.byref(in_blob),
        "QuantHunter",
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)
        del in_buffer


def _crypt_unprotect_data(data: bytes) -> bytes:
    if not _is_windows():
        raise OSError("DPAPI is only available on Windows.")
    if not data:
        return b""
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32
    in_blob, in_buffer = _build_blob(data)
    out_blob = _DataBlob()
    if not crypt32.CryptUnprotectData(
        ctypes.byref(in_blob),
        None,
        None,
        None,
        None,
        _CRYPTPROTECT_UI_FORBIDDEN,
        ctypes.byref(out_blob),
    ):
        raise ctypes.WinError()
    try:
        return _blob_to_bytes(out_blob)
    finally:
        if out_blob.pbData:
            kernel32.LocalFree(out_blob.pbData)
        del in_buffer


def protect_secret(value: str) -> str:
    if not value:
        return ""
    if value.startswith(_DPAPI_PREFIX):
        return value
    if not _is_windows():
        return value
    try:
        protected = _crypt_protect_data(value.encode("utf-8"))
    except OSError:
        return value
    return f"{_DPAPI_PREFIX}{base64.b64encode(protected).decode('ascii')}"


def reveal_secret(value: str) -> str:
    if not value:
        return ""
    if not value.startswith(_DPAPI_PREFIX):
        return value
    if not _is_windows():
        return ""
    encoded = value[len(_DPAPI_PREFIX) :]
    try:
        protected = base64.b64decode(encoded.encode("ascii"))
        plain = _crypt_unprotect_data(protected)
    except (OSError, ValueError):
        return ""
    try:
        return plain.decode("utf-8")
    except UnicodeDecodeError:
        return ""
