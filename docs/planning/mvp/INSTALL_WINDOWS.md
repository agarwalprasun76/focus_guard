# Focus Guard MVP - Windows Install Guide

This is the canonical install/onboarding path for MVP validation.

## 1) Prerequisites
- Windows 10/11
- Python 3.10+ available in PATH
- Edge or Chrome installed

## 2) Clone and install dependencies

```powershell
git clone <your-focus-guard-repo-url>
cd focus_guard
pip install -r requirements.txt
```

## 3) Start Focus Guard runtime

```powershell
python -m focus_guard.main
```

**Recommended flow:** always use the command above—there is no separate installer that asks “run setup?” first. Same process: **configure in the wizard (only when no deployment config exists yet)** → core services and tray **start after you click Finish** → **Finish setup** dialog opens (~2 seconds later) to open the guardian dashboard and run the connection check. **Later runs:** no wizard; reopen **Settings…** from the tray to edit anything.

## 4) Complete first-run wizard
- While `deployment_config.json` exists (after a prior run), reopening the wizard or **Settings…** from the tray reloads your saved email, reporting interval, enforcement mode, personalization, time-budget fields, extension-install checkbox, and admin-password state (leave password fields empty to keep the current password).
- Configure email reports (optional but recommended)
- Install browser extension from store links
  - Edge store ID: `legaalcjhhgofgpgbbpoadafdjllckgg`
  - Chrome store ID: `hnpfnmlcmdhkbhnfifmnonehebeafclp`
- Set time limits / budgets
- Set admin password
- Finish the wizard; when the tray has started (~2 seconds later), complete the **Finish setup** dialog (**Open Guardian Dashboard**, **Run connection check**). Retry the check briefly if endpoints are still waking up.

## Supported deployment posture (Day 9 canonical model)

Focus Guard MVP currently supports one explicit machine-user model:

- **Installer run by admin:** install/setup is performed by a Windows administrator account.
- **Designated monitored user:** one primary monitored user is configured per machine (`monitored_user_name` in `deployment_config.json`).
- **Service/tray boundaries:**
  - Service/background components enforce policy, persistence, and API endpoints.
  - User-session monitoring/tray UX runs in the interactive user session.
- **Known multi-session limit:** behavior is validated for a single active interactive session at a time. Multiple concurrent user sessions are best-effort and not a guaranteed enforcement model for MVP.

This posture is persisted in deployment metadata (`deployment_posture_model`, `installer_account_name`, `monitored_user_name`, `session_scope`) for operator traceability.

### OpenAI / LLM (optional)

For OpenAI-backed classifiers, the runtime resolves the key in this order (first match wins):

1. **`OPENAI_API_KEY`** environment variable (typical for development). If this is set to an old or revoked key, it **overrides** `api_token.json` — clear or update the env var when rotating keys.
2. **`openai_api_key`** in `%ProgramData%\FocusGuard\api_token.json` — the **same** JSON file as the tab-server bearer token (`token`, `token_hash`, …), so both secrets can live in one ProgramData document. The alternate key name **`open_ai_api_key`** is also read if the canonical field is absent.

Use **no leading or trailing spaces** inside `token` and `token_hash` (those values are not trimmed). The OpenAI value is trimmed when read.

Add or edit the string field next to the existing token fields, then restart Focus Guard. Do not commit real keys to git. To confirm which credential is used, run `python scripts/verify_openai_key.py` (default order) or `python scripts/verify_openai_key.py --file-only` (ProgramData file only).

## 5) Verify core local endpoints
- Tab server health: `http://127.0.0.1:58392/api/health`
- Admin gateway: `http://127.0.0.1:58393/admin`
- Admin gateway health: `http://127.0.0.1:58393/admin/health`

### Remote guardian access (canonical MVP+ profile — Day 11)

Operators often need **rules, exceptions, enforcement mode, budgets, and monitoring** from another device. The endorsed model is documented in **`docs/planning/mvp/ADR_001_REMOTE_ADMIN_ACCESS.md`**. Summary:

| Approach | MVP stance |
|----------|------------|
| **Localhost-only** | Default and safest when the guardian sits at the monitored PC |
| **LAN / `0.0.0.0` binding + router port-forward** | **Not** the default recipe — high blast radius; easy to accidentally expose the admin SPA + API broadly |
| **Outbound tunnel → `127.0.0.1:58393` (canonical remote)** | **Preferred for remote guardians** — no inbound firewall pinhole when implemented as **localhost target + outbound tunnel** |

**Canonical remote profile:** run the admin gateway on **`127.0.0.1`** (default) and use an **outbound HTTPS tunnel** (e.g. **Cloudflare Tunnel + Access**, or an equivalent “reverse proxy / edge auth” stack) whose **origin** forwards to `http://127.0.0.1:58393`. The tunnel terminator handles TLS; Focus Guard stays off the raw public TCP port pattern.

#### Day 12 — Practical remote login runbook (out-of-network)

**Step-by-step Cloudflare setup (vendor UI changes over time):**  
`docs/planning/mvp/CLOUDFLARE_TUNNEL_SETUP_FOCUS_GUARD.md`

**Security guardrails (read first)**

1. **Do not** open a generic “DMZ / forward port **58393**” rule on a home router as your first step.
2. Keep a **strong, unique wizard admin password**; rotate if shared with anyone you no longer trust. Dashboard access equals **policy + monitoring control** over the monitored machine.
3. **Origin / CORS:** the admin SPA only talks to the gateway when the browser **`Origin`** is allow-listed. When the UI is opened at an HTTPS hostname (tunnel), set **`FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS`** to that origin exactly (scheme + host + port, **no path**), e.g. `https://guardian.example.com`. Multiple origins = comma-separated list. See `focus_guard/core/admin_gateway/config.py`.
4. **Session tokens:** treat gateway login like any sensitive app — log out on shared PCs; short TTL is configured on the gateway (`auth_token_ttl_seconds` in `AdminGatewayConfig`).
5. Optional bind overrides (`FOCUS_GUARD_ADMIN_GATEWAY_HOST` / `_PORT`): default remains loopback-only. Non-loopback bind belongs only with **Windows Firewall** scoping and ADR‑reviewed threat model — **still** avoid naked Internet port-forward.

**Recommended path: Cloudflare Tunnel (`cloudflared`) → localhost gateway**

High-level steps (follow vendor docs for install/auth details — links change less often than CLI flags):

1. On the **monitored PC** (where Focus Guard runs), confirm locally: `http://127.0.0.1:58393/admin/health` returns OK.
2. Install **Cloudflare Tunnel** (`cloudflared`) for Windows from Cloudflare’s documentation.
3. Create a **named tunnel** and a **DNS hostname** (e.g. `guardian.example.com`) you control in Cloudflare.
4. Configure tunnel ingress so that hostname’s traffic forwards to **`http://127.0.0.1:58393`** (not `https` — the gateway speaks HTTP on loopback).
5. Run `cloudflared` as a **Windows service** or an always-on scheduled task so reconnect happens after reboot/sleep.
6. Set environment for the Focus Guard process (service wrapper, tray parent, or user session — however you start the app):

   `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS=https://guardian.example.com`

   Use the **exact** URL guardians type in the browser (include `https`, no trailing slash in the origin sense). Restart Focus Guard after changing env.
7. **Optional but strongly recommended:** add **Cloudflare Zero Trust Access** (or another IdP) in front of the tunnel hostname so random visitors never see the login page without SSO/MFA. Productized IdP inside the gateway remains **[FR-024]**.
8. From a **different network** (e.g. cellular), open `https://guardian.example.com/admin`, log in with the wizard admin password, and confirm dashboard + settings load.

**Latency / reliability:** expect one extra network hop per API call. If the tunnel process stops, remote access stops — use service auto-restart and monitor `cloudflared` logs. For heavy rule-editing sessions, **RDP to the PC + localhost admin** (below) can feel snappier.

**Operational fallback paths**

| Fallback | When to use | Notes |
|----------|-------------|--------|
| **Remote Desktop / Chrome Remote Desktop** to the monitored PC, then `http://127.0.0.1:58393/admin` | Tunnel not ready yet; one-time support | No new exposure; higher friction. Works with existing localhost CORS defaults. |
| **Mesh VPN (Tailscale, etc.) + stay on localhost** | You already mesh the PC; still want zero inbound ports | Remote guardian uses RDP/screen share over mesh, or runs tunnel **only on the mesh interface** — do not improvise `0.0.0.0:58393` on coffee-shop Wi‑Fi. |
| **Trusted LAN only** | Same house, same router, no tunnel vendor | ADR‑001 Option 2 — bind + **firewall‑scoped** LAN rules if you must; never the default “port forward to the world” pattern. |

**Troubleshooting (remote)**

| Symptom | Likely cause | What to try |
|---------|----------------|-------------|
| Browser console: CORS / blocked by ORB | `Origin` not allow-listed | Set `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS` to the **browser address bar** origin; restart app. |
| HTTP **403** `origin not allowed` | Same as above | Include scheme + host + port exactly. |
| Tunnel **502** / empty response | Focus Guard not running or wrong ingress port | Confirm `58393` locally; tunnel service running. |
| Login fails with correct password | Wrong machine / stale deployment | Confirm you tunnel to the intended PC; check `%ProgramData%\FocusGuard\deployment_config.json`. |
| Quick tunnel URL changes every run | Ephemeral hostname | Either use a **named tunnel + fixed DNS**, or update `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS` each time — prefer stable hostname. |

**Automated API probe (same machine or via tunnel URL)**

From a shell with the app reachable:

```powershell
python scripts/admin_gateway_smoke.py --password "<ADMIN_PASSWORD>"
```

Optional: `--base-url https://guardian.example.com` to hit the public hostname (tunnel must already route to this PC’s gateway).

**Multiple guardians:** two people editing rules at once can still hit **last-write-wins** races until product support lands — see **`FEATURE_REQUESTS_PARKING_LOT.md` [FR-029]** and `ADR_001_REMOTE_ADMIN_ACCESS.md` (Option 3 notes). Until then: **refresh the settings view before saving** if another guardian may have changed policy, or coordinate a single editor for large edits.

Related environment variables live in **`focus_guard/core/admin_gateway/config.py`** (module docstring).

## 6) MVP smoke checks (minimum)
1. Open a known distracting site and confirm block flow.
2. Request an override and confirm override session behavior.
3. Open admin dashboard and verify settings can be changed.
4. Verify dashboard data is visible.
5. Trigger hourly/daily report path and verify report content is not blank.

## 7) Build packaged executable (optional, for installer validation)

```powershell
python deployment/application/windows/scripts/build_exe.py
```

Build artifacts should be created in:
- `deployment/application/dist/`
- `deployment/application/build/`

Run local installer batch from dist:

```powershell
deployment/application/dist/install_focus_guard.bat
```

## 8) Startup/service verification checklist

Use runtime diagnostics before declaring install healthy:

```powershell
python -m focus_guard.deployment.main_service diagnostics --format text
```

For CI-style gate (non-zero on readiness failure):

```powershell
python -m focus_guard.deployment.main_service diagnostics --format json --require-ready
```

Recommended pass criteria:
- Tab server health shows `healthy: True`
- Admin gateway health/meta checks are healthy
- `overall_ready: True`
- No critical recommendations about occupied ports or missing `uvicorn`

### Operator machine-prep checklist (before first run)

- [ ] Installation command is run from an **administrator** account.
- [ ] Intended monitored account is known and entered/verified in config (`user_name` / `monitored_user_name`).
- [ ] Browser extension is installed for the monitored user session (Chrome or Edge).
- [ ] `%ProgramData%\FocusGuard\deployment_config.json` exists and includes posture metadata fields.
- [ ] Service/tray starts successfully and local health endpoints respond (`58392`, `58393`).
- [ ] If multiple simultaneous Windows sessions are expected, operator accepts MVP best-effort behavior and validates manually.

## Troubleshooting
- If extension appears disconnected, verify tab server health endpoint first.
- If admin UI is unreachable, verify Focus Guard process is running and port `58393` is free.
- If reports are not sent, confirm SMTP settings in wizard/settings and check logs.
- **`Access is denied` saving `domain_config.json` under `%ProgramData%\FocusGuard`:** often the file or folder was created by an elevated install while you run the app as a normal user. This build mirrors domain rules to `%LocalAppData%\FocusGuard\domain_config.json` when ProgramData is not replaceable by your account, and writes a `.domain_config_use_localappdata` marker so future launches stay consistent (restart Focus Guard after migration). Fixing ACL so `Users` can modify `%ProgramData%\FocusGuard` is OK too if you want a machine-wide shared file again.

