#!/usr/bin/env bash
# ==============================================================================
#  🇮🇩 NUSANTARA STREAM - Systemd Service Management Script
# ==============================================================================
#  Author   : Amang (@BukanDevelopers)
#  GitHub   : https://github.com/amanqs
#  Project  : Nusantara Stream Telegram Bot
#  License  : GNU General Public License v3.0
# ==============================================================================

SERVICE_NAME="nusantarastream"
SERVICE_FILE="/etc/systemd/system/${SERVICE_NAME}.service"
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_USER="$(whoami)"

# Deteksi python di .venv atau venv atau default python3
if [ -f "${APP_DIR}/.venv/bin/python3" ]; then
    PYTHON_EXEC="${APP_DIR}/.venv/bin/python3"
elif [ -f "${APP_DIR}/venv/bin/python3" ]; then
    PYTHON_EXEC="${APP_DIR}/venv/bin/python3"
else
    PYTHON_EXEC="$(which python3)"
fi

# Warna terminal
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

# Verifikasi akses root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        echo -e "${RED}[!] Harap jalankan script ini dengan hak akses sudo / root!${NC}"
        echo -e "    Contoh: ${BOLD}sudo bash systemd.sh $1${NC}"
        exit 1
    fi
}

# 1. Install Service
install_service() {
    check_root "install"
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${BOLD} 🇮🇩 Memasang Layanan Systemd Nusantara Stream...${NC}"
    echo -e "${CYAN}=====================================================${NC}"

    echo -e "${BLUE}[*] Direktori Kerja :${NC} ${APP_DIR}"
    echo -e "${BLUE}[*] Eksekutor Python:${NC} ${PYTHON_EXEC}"
    echo -e "${BLUE}[*] Pengguna Sistem :${NC} ${CURRENT_USER}"

    cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Nusantara Stream Telegram Music & Video Bot
After=network.target network-online.target
Wants=network-online.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${APP_DIR}
ExecStart=${PYTHON_EXEC} main.py
Restart=always
RestartSec=5s
KillSignal=SIGINT
TimeoutStopSec=15s
StandardOutput=journal
StandardError=journal
LimitNOFILE=65535

[Install]
WantedBy=multi-user.target
EOF

    chmod 644 "${SERVICE_FILE}"
    systemctl daemon-reload
    systemctl enable "${SERVICE_NAME}"

    echo -e "${GREEN}[✔] Layanan ${SERVICE_NAME}.service berhasil dipasang & diaktifkan saat boot!${NC}"
    echo -e "${YELLOW}[💡] Ketik 'sudo bash systemd.sh start' untuk memulai bot.${NC}"
}

# 2. Start Service
start_service() {
    check_root "start"
    if [ ! -f "${SERVICE_FILE}" ]; then
        echo -e "${YELLOW}[!] Service belum terpasang. Memasang terlebih dahulu...${NC}"
        install_service
    fi

    echo -e "${YELLOW}[*] Menjalankan layanan ${SERVICE_NAME}...${NC}"
    systemctl start "${SERVICE_NAME}"
    sleep 1
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${GREEN}[✔] Nusantara Stream berhasil online di latar belakang (Background Systemd)!${NC}"
    else
        echo -e "${RED}[✘] Gagal menjalankan bot. Periksa log dengan 'sudo bash systemd.sh logs'${NC}"
    fi
}

# 3. Stop Service
stop_service() {
    check_root "stop"
    echo -e "${YELLOW}[*] Menghentikan layanan ${SERVICE_NAME}...${NC}"
    systemctl stop "${SERVICE_NAME}"
    echo -e "${GREEN}[✔] Nusantara Stream berhasil dihentikan.${NC}"
}

# 4. Restart Service
restart_service() {
    check_root "restart"
    echo -e "${YELLOW}[*] Memulai ulang (restart) layanan ${SERVICE_NAME}...${NC}"
    systemctl restart "${SERVICE_NAME}"
    sleep 1
    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        echo -e "${GREEN}[✔] Nusantara Stream berhasil di-restart dan kembali aktif!${NC}"
    else
        echo -e "${RED}[✘] Gagal me-restart bot. Periksa log dengan 'sudo bash systemd.sh logs'${NC}"
    fi
}

# 5. Status Service
status_service() {
    systemctl status "${SERVICE_NAME}"
}

# 6. View Live Logs
logs_service() {
    echo -e "${CYAN}[*] Menampilkan log langsung (Tekan Ctrl+C untuk keluar)...${NC}"
    journalctl -u "${SERVICE_NAME}" -f -n 50
}

# 7. Uninstall Service
uninstall_service() {
    check_root "uninstall"
    echo -e "${YELLOW}[*] Menghapus layanan ${SERVICE_NAME}...${NC}"
    systemctl stop "${SERVICE_NAME}" 2>/dev/null
    systemctl disable "${SERVICE_NAME}" 2>/dev/null
    rm -f "${SERVICE_FILE}"
    systemctl daemon-reload
    echo -e "${GREEN}[✔] Layanan ${SERVICE_NAME} berhasil dicopot (uninstalled).${NC}"
}

# Tampilkan Menu Interaktif jika dijalankan tanpa argumen
menu() {
    clear
    echo -e "${CYAN}=====================================================${NC}"
    echo -e "${BOLD}     🇮🇩 NUSANTARA STREAM - SYSTEMD CONTROLLER 🇮🇩     ${NC}"
    echo -e "${CYAN}=====================================================${NC}"
    echo -e " [1] Pasang Layanan (Install / Enable Service)"
    echo -e " [2] Jalankan Bot (Start Service)"
    echo -e " [3] Hentikan Bot (Stop Service)"
    echo -e " [4] Mulai Ulang (Restart Service)"
    echo -e " [5] Cek Status (Status Service)"
    echo -e " [6] Pantau Log Langsung (Live Logs)"
    echo -e " [7] Hapus Layanan (Uninstall Service)"
    echo -e " [0] Keluar"
    echo -e "${CYAN}-----------------------------------------------------${NC}"
    read -rp "Pilih opsi [0-7]: " opt

    case $opt in
        1) install_service ;;
        2) start_service ;;
        3) stop_service ;;
        4) restart_service ;;
        5) status_service ;;
        6) logs_service ;;
        7) uninstall_service ;;
        0) exit 0 ;;
        *) echo -e "${RED}[!] Pilihan tidak valid.${NC}" ;;
    esac
}

# Routing argumen CLI
case "$1" in
    install|setup)
        install_service
        ;;
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart|reload)
        restart_service
        ;;
    status)
        status_service
        ;;
    log|logs)
        logs_service
        ;;
    uninstall|remove)
        uninstall_service
        ;;
    *)
        if [ -n "$1" ]; then
            echo -e "${RED}[!] Perintah '$1' tidak dikenal.${NC}"
            echo -e "Gunakan: $0 {install|start|stop|restart|status|logs|uninstall}"
            exit 1
        else
            menu
        fi
        ;;
esac
