# BalanceWheel Trading Diary

Chronological record of bot runs, orders, and verification notes.  
Sources: `logs/balance_wheel.log` (GCP/Linux), Angel One order book (manual check).

---

## 2026-06-04 — Live HDFCBANK buy (verified from logs)

**Environment:** GCP Linux VM (`/opt/balancewheel`), BalanceWheel **v1.0.9**, **LIVE PRODUCTION MODE**.

### Confirmed app trade

| Field | Value |
|--------|--------|
| Date / time (IST) | **2026-06-04 10:36:38** |
| Symbol | **HDFCBANK-EQ** |
| Side | **BUY** |
| Quantity | **10** shares |
| Order type | **LIMIT** @ **₹747.6** |
| Product | **DELIVERY** |
| Angel One order ID | **`260604000384963`** |
| Approx. order value | **₹7,476.00** |
| Signal | `[BUY]` — price dip **~19.92%** vs portfolio avg (≥ 15% rule) |
| Log confirmation | `Order placed successfully` → `Execution result: Order placed: 260604000384963` |

**Sizing note:** Analysis suggested **27** shares; execution placed **10** after balance / safety-buffer constraints.

### Holdings cross-check (app DMAT snapshot)

| Time (IST) | HDFCBANK qty | Notes |
|------------|--------------|--------|
| 10:36:38 (before order) | **7** | Cash ~₹8,577.61 |
| 10:51:54 (later run) | **17** | **+10** shares — aligns with filled/placed order |

### Other runs same day (no additional live orders)

| Time (IST) | Outcome |
|------------|---------|
| 10:31 | Trading cycle failed — Angel API **rate limit** on holdings; **no orders** |
| 10:38 | HCLTECH **BUY** signal → **blocked** — insufficient balance after safety buffer |
| 10:51 | HCLTECH / BAJAJFINSV skipped — could not fetch LTP (Angel rate limit + Yahoo 429); **no orders** |

### Manual verification (Angel One app)

- [ ] Order book: order ID **`260604000384963`** on **4 Jun 2026**
- [ ] Trade book: executed qty/price for HDFCBANK
- [ ] Confirm status: complete / pending / rejected

---

## Window: last 2–3 days (as of 2026-06-04)

| Date | Log activity | Live orders by app |
|------|--------------|-------------------|
| 2026-06-02 | None in repo logs | — |
| 2026-06-03 | None in repo logs | — |
| 2026-06-04 | Multiple runs (see above) | **1** — HDFCBANK × 10 |

**Summary:** In this window, **only one** real order was placed by BalanceWheel (HDFCBANK, order ID above).

---

## Earlier history (reference — outside 2–3 day window)

### 2026-05-30 — Dry run only

- Mode: **DRY RUN** (no real broker orders).
- Logged simulated buys: HCLTECH, HDFCBANK, BAJAJFINSV (`[DRY RUN] Would place order`).

### 2026-05-19 — Live attempts failed

- Mode: LIVE (`Dry Run Mode: False`).
- HCLTECH & HDFCBANK **BUY** signals → broker response: **“No response from broker — Order rejected or error occurred”**.
- **No successful placements** logged.

### 2026-05-14 — Live attempts failed

- Same pattern as 2026-05-19: HCLTECH & HDFCBANK **BUY** attempted → **failed** at broker.
- **No successful placements** logged.

---

## Operational notes

- **Rate limits:** Repeated `Access denied because of exceeding access rate` (Angel) and Yahoo **429** on Nifty/LTP fallbacks — can block analysis and second orders same session.
- **Cash:** After the HDFCBANK order, later runs showed lower cash (~₹1,092) and blocked further HCLTECH buys.
- **Log source:** Pushed from VM via `GITHUB_TOKEN` to `logs/balance_wheel.log`. Local DB on VM: `data/balance_wheel.db` → table `executed_trades` (if present).
- **Security:** Avoid committing tokens; `logs/` may contain sensitive API errors — prefer private repo or stop log push to public GitHub.

---

## How to add a new diary entry

1. Run bot or pull latest logs: `git pull` → check `logs/balance_wheel.log`.
2. Search: `Placing LIVE order`, `Order placed successfully`, `Execution blocked`, `DRY RUN`.
3. Copy order ID and snapshot lines into a new dated section above.
4. Cross-check in Angel One order/trade book.

```bash
# On GCP VM
grep -E "Placing LIVE|Order placed successfully|Execution blocked|DRY RUN" logs/balance_wheel.log | tail -20
```

---

*Last updated: 2026-06-04 (from log analysis in repo).*
