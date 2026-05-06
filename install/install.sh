#!/usr/bin/env bash
set -euo pipefail

echo "==> Comunito Portal: instalador base (GitHub)"

ME="$(whoami)"
APP_DIR="/home/$ME/comunito_facial"
VENV="$APP_DIR/comunito-venv"
SVC="/etc/systemd/system/comunito-facial.service"

echo "==> 1) Paquetes base"
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
  python3-full python3-venv python3-pip \
  libglib2.0-0 libxext6 libsm6 libxrender1 libgl1 \
  build-essential curl ca-certificates git unzip \
  network-manager tzdata iproute2 net-tools \
  gstreamer1.0-tools gstreamer1.0-libav gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
  dnsmasq

sudo systemctl enable NetworkManager --now || true

echo "==> 2) Clonar/actualizar repo"
if [ -d "$APP_DIR/.git" ]; then
  echo "Actualizando repositorio V3..."
  cd "$APP_DIR"
  git fetch --all
  git reset --hard origin/master
else
  echo "Clonando repositorio V3..."
  sudo rm -rf "$APP_DIR"
  git clone https://github.com/comunito/FacialV3.git "$APP_DIR"
  cd "$APP_DIR"
fi

echo "==> 3) Crear venv e instalar requirements"
python3 -m venv "$VENV"
# shellcheck disable=SC1091
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel setuptools
pip install -r "$APP_DIR/requirements.txt"

echo "==> 3.1) Validar Motores OpenCV (Face)"
python - <<'PYCHK'
import sys
try:
    import cv2
    detector = cv2.FaceDetectorYN.create(
        "models/face_detection_yunet.onnx", "", (320, 320)
    )
    recognizer = cv2.FaceRecognizerSF.create(
        "models/face_recognition_sface.onnx", ""
    )
    print("[OK] OpenCV Face Recognition Engine Listo")
except Exception as e:
    print("[ERROR] Motores faciales no operativos:", e)
    sys.exit(1)
PYCHK

echo "==> 4) Configurar LAN de cámaras en eth0"
sudo nmcli connection delete comunito-cam-lan 2>/dev/null || true
sudo nmcli connection add \
  type ethernet \
  ifname eth0 \
  con-name comunito-cam-lan \
  ipv4.method manual \
  ipv4.addresses 192.168.88.1/24 \
  ipv6.method ignore \
  autoconnect yes || true
sudo nmcli connection up comunito-cam-lan || true

echo "==> 5) Configurar DHCP para cámaras"
sudo mkdir -p /etc/dnsmasq.d
sudo cp "$APP_DIR/install/network/cam_eth.conf" /etc/dnsmasq.d/cam_eth.conf
sudo systemctl enable dnsmasq
sudo systemctl restart dnsmasq

echo "==> 6) Instalar Tailscale"
curl -fsSL https://tailscale.com/install.sh | sh
sudo systemctl enable tailscaled --now || true
echo "==> Tailscale instalado. Después ejecuta: sudo tailscale up"

echo "==> 7) Instalar systemd service"
sudo cp "$APP_DIR/systemd/comunito-facial.service" "$SVC"
sudo sed -i "s|^User=.*|User=$ME|g" "$SVC"
sudo sed -i "s|/home/pi|/home/$ME|g" "$SVC"

echo "==> 8) Habilitar servicio"
sudo systemctl daemon-reload
sudo systemctl enable comunito-facial.service --now

IP_NOW="$(hostname -I | awk '{print $1}')"
echo
echo "==> Listo:"
echo "    Portal Facial: http://$IP_NOW:5001"
echo "    Settings:      http://$IP_NOW:5001/settings"
echo "    Tailscale: ejecuta sudo tailscale up"
