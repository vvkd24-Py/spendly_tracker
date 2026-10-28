#!/usr/bin/env bash
# Push local changes to EC2 and restart the app.
# Run from Git Bash (Windows) or any bash shell.
# Usage: bash deploy/deploy.sh <EC2_PUBLIC_IP> <PATH_TO_PEM_KEY>
# Example: bash deploy/deploy.sh 54.123.45.67 ~/Downloads/spendly-key.pem
set -euo pipefail

EC2_IP="${1:?Usage: $0 <ec2-public-ip> <path/to/key.pem>}"
KEY="${2:?Usage: $0 <ec2-public-ip> <path/to/key.pem>}"
REMOTE_DIR="/home/ubuntu/spendly"

echo "▶  Syncing project to EC2 ($EC2_IP)..."
rsync -avz \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='*.pyc' \
    --exclude='.pytest_cache' \
    --exclude='tests/__pycache__' \
    --exclude='database/__pycache__' \
    --exclude='venv' \
    --exclude='.env' \
    --exclude='spendly.db' \
    -e "ssh -i $KEY -o StrictHostKeyChecking=no" \
    ./ ubuntu@"$EC2_IP":"$REMOTE_DIR"/

echo "▶  Installing/updating Python packages on EC2..."
ssh -i "$KEY" -o StrictHostKeyChecking=no ubuntu@"$EC2_IP" \
    "source $REMOTE_DIR/venv/bin/activate && pip install -r $REMOTE_DIR/requirements.txt gunicorn -q"

echo "▶  Restarting gunicorn..."
ssh -i "$KEY" -o StrictHostKeyChecking=no ubuntu@"$EC2_IP" \
    "sudo systemctl restart spendly && sudo systemctl status spendly --no-pager"

echo ""
echo "✅  Deploy complete!"
echo "    Visit: http://$EC2_IP"
