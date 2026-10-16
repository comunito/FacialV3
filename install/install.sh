#!/usr/bin/env bash
set -euo pipefail

ME="$(whoami)"
APP_DIR="/home/$ME/comunito_facial"
VENV="$APP_DIR/comunito-venv"
SVC="/etc/systemd/system/comunito-facial.service"

sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3-full python3-venv python3-pip libglib2.0-0 libgl1 git ca-certificates

if [[ ! -d "$APP_DIR/.git" ]]; then
  git clone --branch dev/facial-portal-rebuild https://github.com/comunito/FacialV3.git "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin
  git -C "$APP_DIR" pull --ff-only origin dev/facial-portal-rebuild
fi

python3 -m venv "$VENV"
source "$VENV/bin/activate"
python -m pip install --upgrade pip wheel
pip install -r "$APP_DIR/requirements.txt"

cd "$APP_DIR"
[[ -f config.json ]] || cp config.example.json config.json
mkdir -p data
sudo cp systemd/comunito-facial.service "$SVC"
sudo sed -i "s/USER_PLACEHOLDER/$ME/g" "$SVC"
sudo systemctl daemon-reload
sudo systemctl enable comunito-facial.service
sudo systemctl restart comunito-facial.service
echo "Portal facial instalado en http://$(hostname -I | awk '{print $1}'):5001"
echo "El gate físico permanece desactivado hasta cambiar gate.enabled y gate.allow_physical explícitamente."
