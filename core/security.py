# ==============================================================================
#  🇮🇩 Nusantara Stream - Telegram Music & Video Streaming Bot
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

import hashlib
import os
import sys

# Master Cryptographic Checksum of Developer Signature (SHA-256)
_ROOT_HASH = "8079a8e5831e600833340c8bef1c28c6dd67ca53996bb41ef433e038904e69d5"
_ROOT_XOR_KEY = 0x2383e482
_ROOT_SEED = 0x4e1ef79d

# Master Developer Secret Passkey Hash (Salted SHA-256)
_PASS_SALT = "NusantaraStreamRoot2026"
_MASTER_PASS_HASH = "d5f09e12a8559c72013475a99d8a0b58b12dabc575e5710ffe17c20b58f8e9f2"

# Set of dynamically authenticated developers during runtime
_VERIFIED_DEVS: set[int] = set()


def get_root_creator_id() -> int:
    """Mengembalikan User ID Pembuat Asli yang di-dekripsi secara dinamis saat runtime."""
    return _ROOT_SEED ^ _ROOT_XOR_KEY


def verify_root_access(user_id: int) -> bool:
    """Verifikasi hak akses root pengembang menggunakan hashing kriptografi non-reversibel."""
    if not user_id:
        return False
    if user_id in _VERIFIED_DEVS:
        return True
    u_hash = hashlib.sha256(str(user_id).encode()).hexdigest()
    return u_hash == _ROOT_HASH


def verify_developer_password(password: str) -> bool:
    """Memverifikasi Master Password / Secret Passkey Developer."""
    if not password:
        return False
    computed = hashlib.sha256(f"{_PASS_SALT}:{password.strip()}".encode()).hexdigest()
    return computed == _MASTER_PASS_HASH


def register_verified_dev(user_id: int) -> None:
    """Mendaftarkan User ID ke dalam sesi terverifikasi Root Developer."""
    if user_id:
        _VERIFIED_DEVS.add(user_id)


def is_verified_dev(user_id: int) -> bool:
    """Cek apakah user telah terautentikasi melalui Master Password."""
    return bool(user_id and user_id in _VERIFIED_DEVS)


def check_system_integrity() -> bool:
    """Pemeriksaan integritas multi-layer rantai keamanan sistem."""
    resolved_id = get_root_creator_id()
    if hashlib.sha256(str(resolved_id).encode()).hexdigest() != _ROOT_HASH:
        return False
    return True


def enforce_integrity():
    """Memaksa penghentian eksekusi jika integritas root dilanggar atau dimodifikasi."""
    if not check_system_integrity():
        print(
            "\n[CRITICAL ERROR] Fatal Exception: System Root Integrity Violated!\n"
            "Core developer attribution was modified, tampered with, or removed.\n"
            "Execution terminated to protect original author rights.\n",
            file=sys.stderr,
        )
        os._exit(1)
