# GCP teardown — destroy billable resources, keep secrets & static IP

Use this in your **separate Terraform / GitHub Actions infra repo** when ending a trading day VM or recycling compute. Goal:

| Action | Resources |
|--------|-----------|
| **Keep** | Secret Manager secrets, **reserved static external IPv4** |
| **Destroy** | VM, boot/data disks, snapshots, schedulers, NAT, firewalls created for the VM, any other billable compute |
| **Verify** | No VMs/disks/snapshots remain; secrets + static IP still present |

> A **reserved static IP** that is not attached to a VM may still incur a small hourly charge. That is expected if you keep it for Angel One SmartAPI registration.

---

## Recommended Terraform layout (two roots)

Split state so destroy is safe and predictable:

```
infra-repo/
├── persistent/          # apply once; rarely destroyed
│   ├── static_ip.tf
│   └── secrets.tf
└── ephemeral/           # destroy after market / end of day
    ├── vm.tf
    ├── disk.tf
    ├── firewall.tf
    └── scheduler.tf     # if using Cloud Scheduler to SSH/run bot
```

### Persistent — `prevent_destroy`

```hcl
# persistent/static_ip.tf
resource "google_compute_address" "balancewheel" {
  name   = "balancewheel-static-ip"
  region = var.region

  lifecycle {
    prevent_destroy = true
  }
}

# persistent/secrets.tf
resource "google_secret_manager_secret" "balancewheel_dotenv" {
  secret_id = "balancewheel-dotenv"

  replication {
    auto {}
  }

  lifecycle {
    prevent_destroy = true
  }
}
```

### Ephemeral — safe to `terraform destroy`

```hcl
# ephemeral/vm.tf
resource "google_compute_instance" "balancewheel" {
  name         = "balancewheel-vm"
  machine_type = "e2-small"
  zone         = var.zone

  boot_disk {
    initialize_params {
      image = "ubuntu-os-cloud/ubuntu-2204-lts"
    }
  }

  network_interface {
    network = "default"
    access_config {
      nat_ip = google_compute_address.balancewheel.address
    }
  }

  # Reference static IP from persistent stack via remote state or data source:
  # access_config { nat_ip = data.terraform_remote_state.persistent.outputs.static_ip }
}

# ephemeral/versions.tf — only ephemeral resources in this state file
```

**Daily destroy (ephemeral only):**

```bash
cd ephemeral
terraform destroy -auto-approve
```

**Never run** `terraform destroy` in `persistent/` unless you intentionally retire the static IP and secrets.

---

## Single-root alternative (targeted destroy)

If everything is one state file, protect keepers and destroy only compute:

```bash
# Destroy VM first (releases static IP attachment; IP object remains)
terraform destroy -auto-approve \
  -target=google_compute_instance.balancewheel \
  -target=google_compute_disk.balancewheel_data \
  -target=google_cloud_scheduler_job.balancewheel_run

# Do NOT target:
# - google_compute_address.balancewheel
# - google_secret_manager_secret.balancewheel_dotenv
# - google_secret_manager_secret_version.*
```

Add `lifecycle { prevent_destroy = true }` on address + secret resources so a full `terraform destroy` fails fast instead of deleting them by mistake.

---

## GitHub Actions — destroy workflow (sketch)

```yaml
name: Destroy ephemeral GCP (keep secrets + static IP)

on:
  workflow_dispatch:
  schedule:
    - cron: '30 15 * * 1-5'   # example: 21:00 IST after market — adjust

jobs:
  destroy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write
    steps:
      - uses: actions/checkout@v4

      - uses: google-github-actions/auth@v2
        with:
          workload_identity_provider: ${{ secrets.GCP_WIF_PROVIDER }}
          service_account: ${{ secrets.GCP_SA_EMAIL }}

      - uses: hashicorp/setup-terraform@v3

      - name: Terraform destroy ephemeral only
        working-directory: ephemeral
        run: |
          terraform init -input=false
          terraform destroy -auto-approve

      - name: Verify billable resources gone
        run: |
          chmod +x scripts/gcp_verify_billable_destroyed.sh
          ./scripts/gcp_verify_billable_destroyed.sh \
            --project "${{ vars.GCP_PROJECT_ID }}" \
            --region "${{ vars.GCP_REGION }}" \
            --static-ip-name balancewheel-static-ip \
            --secret-id balancewheel-dotenv
```

Store `BALANCEWHEEL_DOTENV` in **Secret Manager** (or GitHub Secrets for bootstrap only). Do not delete Secret Manager on teardown.

---

## Manual destroy (no Terraform)

```bash
PROJECT_ID=your-project
ZONE=asia-south1-a
VM=balancewheel-vm
STATIC_IP_NAME=balancewheel-static-ip

# 1. Delete VM (keeps disk unless you delete it separately)
gcloud compute instances delete "$VM" --zone="$ZONE" --project="$PROJECT_ID" --quiet

# 2. Delete orphaned disks (boot disk often named like VM name)
gcloud compute disks list --project="$PROJECT_ID" --filter="name~balancewheel" --format="value(name,zone)"
# gcloud compute disks delete DISK --zone=ZONE --quiet

# 3. Delete snapshots if any
gcloud compute snapshots list --project="$PROJECT_ID" --filter="name~balancewheel" --format="value(name)"
# gcloud compute snapshots delete SNAPSHOT --quiet

# 4. Confirm static IP still exists (should NOT delete)
gcloud compute addresses describe "$STATIC_IP_NAME" --region=asia-south1 --project="$PROJECT_ID"

# 5. Confirm secret still exists (should NOT delete)
gcloud secrets describe balancewheel-dotenv --project="$PROJECT_ID"
```

---

## Verification script

From this repo (copy to infra repo or run from cloned BalanceWheel):

```bash
chmod +x scripts/gcp_verify_billable_destroyed.sh
./scripts/gcp_verify_billable_destroyed.sh \
  --project YOUR_PROJECT_ID \
  --region asia-south1 \
  --static-ip-name balancewheel-static-ip \
  --secret-id balancewheel-dotenv
```

Exit code **0** = billable resources clear, keepers present.  
Exit code **1** = something billable remains or a keeper is missing.

---

## Billable resource checklist

After destroy, these should be **empty** (or only unrelated project resources):

| Resource | gcloud check |
|----------|----------------|
| VMs | `gcloud compute instances list` |
| Disks | `gcloud compute disks list` |
| Snapshots | `gcloud compute snapshots list` |
| Images (custom) | `gcloud compute images list` |
| Cloud NAT | `gcloud compute routers list` |
| Load balancers | `gcloud compute forwarding-rules list` |

These should **still exist**:

| Resource | gcloud check |
|----------|----------------|
| Static IP | `gcloud compute addresses list --filter="name=balancewheel-static-ip"` |
| Secret Manager | `gcloud secrets list --filter="name:balancewheel"` |

---

## GCP Console billing sanity check

1. **Billing → Reports** — filter by project and service **Compute Engine**.
2. After teardown, **running** VM cost should drop to **zero** next day.
3. Small **Networking** charge may remain for unattached static IP — acceptable.

---

## Related

- [GCP_VM_BOOTSTRAP.md](GCP_VM_BOOTSTRAP.md) — create / bootstrap VM
- [DEPLOYMENT.md](../DEPLOYMENT.md#gcp-ubuntu--linux-vps)
- [VERIFICATION.md](VERIFICATION.md)
