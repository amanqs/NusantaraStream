#!/usr/bin/env bash
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
import random
import sys

# Path direktori
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SECURITY_FILE = os.path.join(BASE_DIR, "core", "security.py")
PASS_SALT = "NusantaraStreamRoot2026"


def read_current_pass_hash():
    """Membaca hash password saat ini jika ada."""
    if not os.path.exists(SECURITY_FILE):
        return hashlib.sha256(f"{PASS_SALT}:Nusantara2026!".encode()).hexdigest()
    try:
        with open(SECURITY_FILE, "r", encoding="utf-8") as f:
            content = f.read()
            for line in content.splitlines():
                if "_MASTER_PASS_HASH =" in line:
                    return line.split('"')[1]
    except Exception:
        pass
    return hashlib.sha256(f"{PASS_SALT}:Nusantara2026!".encode()).hexdigest()


def generate_security_file(user_id: int, new_password: str = None):
    """Menghasilkan file core/security.py baru berdasarkan User ID dan Password."""
    xor_key = random.randint(0x10000000, 0x7FFFFFFF)
    seed = user_id ^ xor_key
    sha256_hash = hashlib.sha256(str(user_id).encode()).hexdigest()

    if new_password:
        pass_hash = hashlib.sha256(f"{PASS_SALT}:{new_password.strip()}".encode()).hexdigest()
    else:
        pass_hash = read_current_pass_hash()

    content = f'''import hashlib
import os
import sys

# Master Cryptographic Checksum of Developer Signature (SHA-256)
_ROOT_HASH = "{sha256_hash}"
_ROOT_XOR_KEY = {hex(xor_key)}
_ROOT_SEED = {hex(seed)}

# Master Developer Secret Passkey Hash (Salted SHA-256)
_PASS_SALT = "{PASS_SALT}"
_MASTER_PASS_HASH = "{pass_hash}"

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
    computed = hashlib.sha256(f"{{_PASS_SALT}}:{{password.strip()}}".encode()).hexdigest()
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
            "\\n[CRITICAL ERROR] Fatal Exception: System Root Integrity Violated!\\n"
            "Core developer attribution was modified, tampered with, or removed.\\n"
            "Execution terminated to protect original author rights.\\n",
            file=sys.stderr,
        )
        os._exit(1)
'''

    with open(SECURITY_FILE, "w", encoding="utf-8") as f:
        f.write(content)

    print("\n========================================================")
    print(" 👑 NUSANTARA STREAM - DEVELOPER SECURITY KEY GENERATOR ")
    print("========================================================")
    print(f" [✔] User ID Baru Berhasil Ditanamkan : {user_id}")
    print(f" [*] Dynamic XOR Key                  : {hex(xor_key)}")
    print(f" [*] Cryptographic Seed               : {hex(seed)}")
    print(f" [*] User ID SHA-256 Checksum         : {sha256_hash}")
    print(f" [*] Passkey Salted Checksum          : {pass_hash}")
    print(f" [*] File Target                      : {SECURITY_FILE}")
    print("========================================================\n")


def show_current():
    """Menampilkan detail Developer ID dan Passkey yang sedang aktif."""
    sys.path.insert(0, BASE_DIR)
    try:
        from core.security import get_root_creator_id, _ROOT_HASH, _ROOT_XOR_KEY, _ROOT_SEED, _MASTER_PASS_HASH, check_system_integrity
        dev_id = get_root_creator_id()
        is_ok = check_system_integrity()
        print("\n========================================================")
        print(" 👑 STATUS KUNCI & PASSKEY PENGEMBANG UTAMA SAAT INI ")
        print("========================================================")
        print(f" [*] Active Developer ID        : {dev_id}")
        print(f" [*] Dynamic XOR Key            : {hex(_ROOT_XOR_KEY)}")
        print(f" [*] Seed                       : {hex(_ROOT_SEED)}")
        print(f" [*] User ID SHA-256            : {_ROOT_HASH}")
        print(f" [*] Master Passkey Hash        : {_MASTER_PASS_HASH}")
        print(f" [*] Status Integritas Sistem   : {'🟢 VALID (100% OK)' if is_ok else '🔴 CORRUPTED'}")
        print("========================================================\n")
    except Exception as e:
        print(f"[!] Gagal membaca konfigurasi keamanan: {e}")


def main():
    if len(sys.argv) < 2:
        print("Penggunaan:")
        print("  python3 tools/key_manager.py show                  -> Lihat User ID & Hash saat ini")
        print("  python3 tools/key_manager.py set <USER_ID_BARU>   -> Ubah Developer ID")
        print("  python3 tools/key_manager.py setpass <PASSWORD>    -> Ubah Master Password Root")
        print("\nContoh:")
        print("  python3 tools/key_manager.py set 1839010591")
        print("  python3 tools/key_manager.py setpass RahasiaNusantara2026!")
        return

    cmd = sys.argv[1].lower()
    if cmd == "show":
        show_current()
    elif cmd == "set":
        if len(sys.argv) < 3 or not sys.argv[2].isdigit():
            print("[!] Harap masukkan User ID berupa angka!")
            print("Contoh: python3 tools/key_manager.py set 1839010591")
            return
        new_id = int(sys.argv[2])
        generate_security_file(new_id)
    elif cmd in ("setpass", "pass", "password"):
        if len(sys.argv) < 3 or not sys.argv[2].strip():
            print("[!] Harap masukkan kata sandi baru!")
            print("Contoh: python3 tools/key_manager.py setpass KataSandiRahasia2026!")
            return
        sys.path.insert(0, BASE_DIR)
        from core.security import get_root_creator_id
        curr_id = get_root_creator_id()
        new_pass = sys.argv[2].strip()
        generate_security_file(curr_id, new_password=new_pass)
        print(f"🔑 [✔] Master Passkey berhasil diubah! Gunakan '/devlogin {new_pass}' di bot.")
    else:
        print(f"[!] Perintah '{cmd}' tidak dikenali. Gunakan 'show', 'set <id>', atau 'setpass <password>'.")


if __name__ == "__main__":
    main()
