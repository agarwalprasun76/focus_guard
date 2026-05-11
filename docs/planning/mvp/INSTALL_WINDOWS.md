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

