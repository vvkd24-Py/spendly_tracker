#!/usr/bin/env bash
# One-time setup script — run on a fresh Ubuntu 22.04 EC2 instance
# Usage: sudo bash setup_server.sh
set -euo pipefail

APP_DIR="/home/ubuntu/spendly"
VENV_DIR="$APP_DIR/venv"
LOG_DIR="/var/log/spendly"

echo "==> Updating system packages..."
export DEBIAN_FRONTEND=noninteractive
# Suppress needrestart interactive prompts on Ubuntu 22.04
sudo sed -i "s/#\$nrconf{restart} = 'i';/\$nrconf{restart} = 'a';/" /etc/needrestart/needrestart.conf 2>/dev/null || true
sudo apt-get update -y
sudo apt-get install -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" python3 python3-pip python3-venv nginx git rsync

echo "==> Creating log directory..."
sudo mkdir -p "$LOG_DIR"
sudo chown ubuntu:ubuntu "$LOG_DIR"

echo "==> Creating Python virtual environment..."
python3 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip -q
pip install -r "$APP_DIR/requirements.txt" gunicorn -q

echo "==> Generating production secret key..."
SECRET_KEY=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo "FLASK_SECRET_KEY=$SECRET_KEY" > "$APP_DIR/.env"
echo "FLASK_ENV=production"        >> "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"

echo "==> Setting ownership..."
chown -R ubuntu:ubuntu "$APP_DIR"

echo "==> Installing systemd service..."
sudo cp "$APP_DIR/deploy/spendly.service" /etc/systemd/system/spendly.service
sudo systemctl daemon-reload
sudo systemctl enable spendly
sudo systemctl start spendly

echo "==> Configuring nginx..."
sudo cp "$APP_DIR/deploy/nginx.conf" /etc/nginx/sites-available/spendly
sudo ln -sf /etc/nginx/sites-available/spendly /etc/nginx/sites-enabled/spendly
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl restart nginx

echo "==> Configuring firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 'Nginx Full'
sudo ufw --force enable

PUBLIC_IP=$(curl -s http://169.254.169.254/latest/meta-data/public-ipv4 2>/dev/null || echo "<your-ec2-ip>")
echo ""
echo "✅  Spendly is live!"
echo "    Visit: http://$PUBLIC_IP"
