#!/bin/bash

set -euo pipefail

project_dir="$(cd "$(dirname "$0")/.." && pwd)"
service_user="$(id -un)"
service_group="$(id -gn)"

sudo apt-get update
sudo apt-get install -y python3 alsa-utils avahi-daemon curl
sudo usermod -aG audio "$service_user"

sudo tee /etc/systemd/system/blackout.service >/dev/null <<EOF
[Unit]
Description=Blackout building game
Wants=network-online.target
After=network-online.target sound.target

[Service]
Type=simple
User=$service_user
Group=$service_group
SupplementaryGroups=audio
WorkingDirectory=$project_dir
Environment=PYTHONUNBUFFERED=1
Environment=BLACKOUT_HOST=0.0.0.0
ExecStart=/usr/bin/python3 $project_dir/blackout_game.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now avahi-daemon blackout.service

pi_address="$(hostname -I | awk '{print $1}')"
echo
echo "Blackout is installed and running."
echo "Phone remote: http://blackout.local:8765/controller"
if [[ -n "$pi_address" ]]; then
  echo "IP fallback:  http://$pi_address:8765/controller"
fi
echo "Status: sudo systemctl status blackout"
echo "Logs:   journalctl -u blackout -f"
