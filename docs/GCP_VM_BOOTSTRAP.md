# GCP VM bootstrap (Terraform / GitHub Actions)

Use when a **new Ubuntu VM** is created by your **separate infra repo**. Bootstrap installs the app only — **no crontab** (you schedule ~10:30 IST Mon–Fri externally).

## GitHub secret (infra repo)

| Secret | Content |
|--------|---------|
| `BALANCEWHEEL_DOTENV` | Full `.env` file body (see [.env.example](../.env.example)) |

## Bootstrap commands (every new VM)

```bash
export DEBIAN_FRONTEND=noninteractive
export APP_DIR=/opt/balancewheel
export REPO_URL=https://github.com/nir351988/Balancewheel.git
export REPO_BRANCH=master
export BALANCEWHEEL_DOTENV='<<from secret>>'

sudo timedatectl set-timezone Asia/Kolkata
sudo apt-get update -qq
sudo apt-get install -y git ca-certificates python3 python3-venv python3-pip

if [[ ! -d "$APP_DIR/.git" ]]; then
  sudo mkdir -p /opt
  sudo git clone --branch "$REPO_BRANCH" --depth 1 "$REPO_URL" "$APP_DIR"
  sudo chown -R "$USER:$USER" "$APP_DIR"
else
  git -C "$APP_DIR" fetch origin "$REPO_BRANCH" --depth 1
  git -C "$APP_DIR" checkout "$REPO_BRANCH"
  git -C "$APP_DIR" reset --hard "origin/$REPO_BRANCH"
fi

cd "$APP_DIR"
python3 -m venv venv
./venv/bin/pip install --upgrade pip setuptools wheel
./venv/bin/pip install -r requirements-runtime.txt

umask 077
printf '%s\n' "$BALANCEWHEEL_DOTENV" > "$APP_DIR/.env"
chmod 600 "$APP_DIR/.env"
rm -f "$APP_DIR/.credentials.json"

"$APP_DIR/venv/bin/python" "$APP_DIR/balance_wheel.py" --account
```

## Daily run (your scheduler — not installed by bootstrap)

```bash
cd /opt/balancewheel && /opt/balancewheel/venv/bin/python balance_wheel.py
```

## Static IP (live orders)

Reserve a GCP static external IP, attach to the VM, register it in the Angel One SmartAPI portal.

## Teardown (end of day)

Destroy **VM, disks, and other billable compute** — **keep** Secret Manager secrets and the **static IP**. See [GCP_TEARDOWN.md](GCP_TEARDOWN.md) and run:

```bash
./scripts/gcp_verify_billable_destroyed.sh --project ID --region REGION \
  --static-ip-name balancewheel-static-ip --secret-id balancewheel-dotenv
```

## Related

- [GCP_TEARDOWN.md](GCP_TEARDOWN.md) — destroy + verify billable resources
- [DEPLOYMENT.md](../DEPLOYMENT.md#gcp-ubuntu--linux-vps)
- [VERIFICATION.md](VERIFICATION.md)
- [TRADING_DIARY.md](TRADING_DIARY.md)
