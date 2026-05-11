# Cloudflare Tunnel → Focus Guard admin gateway (step-by-step)

This guide assumes the **monitored PC** runs Focus Guard and the admin gateway on **`http://127.0.0.1:58393`** (default). You will expose only that HTTP service through Cloudflare’s **outbound** tunnel (no router port-forward).

**Official reference (kept current by Cloudflare):**  
[Create a Cloudflare Tunnel · Cloudflare One docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/)

### Is `cloudflared` installed by Focus Guard?

**No — not in the current MVP build.** You install `cloudflared` separately (see §1 below). The Focus Guard installer does **not** bundle Cloudflare’s connector; tunnel **tokens**, **DNS hostnames**, and **Access** policies are always created in your **Cloudflare** account first.

If we later add an **optional assistant** inside Focus Guard (download official binary, health check, maybe service install), that work is tracked as **`FEATURE_REQUESTS_PARKING_LOT.md` [FR-030]** and will be called out in `INSTALL_WINDOWS.md` when shipped.

---

## 0) Prerequisites

1. A **Cloudflare account** (free tier is enough for many home setups).
2. A **domain** whose DNS is managed by Cloudflare (add the site in the Cloudflare dashboard and point its nameservers to Cloudflare if you have not already).
3. On the monitored PC: Focus Guard running; local check works in a browser:  
   `http://127.0.0.1:58393/admin/health` → JSON with `"status": "ok"` (or equivalent).

---

## 1) Install `cloudflared` on Windows (monitored PC)

Pick one:

```powershell
winget install --id Cloudflare.cloudflared
```

Or download the latest **Windows amd64** executable from Cloudflare’s downloads page:  
[Downloads · cloudflared](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/downloads/)

After install, confirm:

```powershell
cloudflared --version
```

**If `cloudflared` is “not recognized” right after `winget install`:** the MSI updated **machine** `PATH`, but **this PowerShell window** still has the old environment. Do one of the following:

1. **Easiest:** close the terminal (or restart Cursor / VS Code), open a **new** PowerShell window, then run `cloudflared --version` again.
2. **Reload `PATH` in the current session** (then try `cloudflared` again):

   ```powershell
   $env:Path = [System.Environment]::GetEnvironmentVariable("Path","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path","User")
   ```

3. **Call the binary by full path** (works even before PATH refreshes). Typical MSI locations — try in order:

   ```powershell
   & "${env:ProgramFiles(x86)}\cloudflared\cloudflared.exe" --version
   & "$env:ProgramFiles\cloudflared\cloudflared.exe" --version
   ```

4. **Locate the exe** if install path changed:

   ```powershell
   winget show --id Cloudflare.cloudflared
   Get-Command cloudflared.exe -ErrorAction SilentlyContinue | Select-Object Source
   ```

`cloudflared` on Windows does **not** auto-update; plan occasional manual updates.

---

## 2) Create a tunnel in Cloudflare Zero Trust (dashboard)

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. Open **Zero Trust** (may prompt you to pick a team name once — free tier exists).
3. Go to **Networks** → **Connectors** → **Cloudflare Tunnels** (wording may be **Tunnels** under **Network** depending on UI revision).
4. Click **Create a tunnel** (or **Add a tunnel**).
5. Choose **Cloudflared** as the connector type, enter a tunnel name (e.g. `focus-guard-admin`), **Save**.

The next screen usually shows **Install and run a connector** with a **copy** button for a command that looks like:

```text
cloudflared.exe service install eyJhIjoi...
```

That long `eyJ...` string is your **tunnel token**. Treat it like a secret (anyone with it can attach a connector to your tunnel).

---

## 3) Install the connector as a Windows service (recommended)

On the **monitored PC**, open **PowerShell as Administrator** and run the **exact** command Cloudflare gave you (it registers and starts the service):

```powershell
cloudflared.exe service install <TOKEN>
```

If you only downloaded `cloudflared.exe` without `winget`, use the full path to the executable.

Check the service:

```powershell
Get-Service cloudflared
```

---

## 4) Route a public hostname to the admin gateway

In the same tunnel’s configuration in Zero Trust:

1. Under **Public hostnames** (or **Published application routes**), **Add a public hostname**.
2. **Subdomain:** e.g. `guardian`  
   **Domain:** pick the zone on Cloudflare (e.g. `example.com`) → full hostname `guardian.example.com`.
3. **Service type:** HTTP  
4. **URL:** `http://127.0.0.1:58393`  
   (Use **http**, not https — the gateway listens in plain HTTP on loopback.)

Save. DNS for `guardian.example.com` is usually created automatically as a **CNAME** to your tunnel.

Wait a minute for DNS/propagation if needed.

---

## 5) Allow the browser `Origin` in Focus Guard (required)

The admin SPA calls the API from the **same origin** as the page. After you open `https://guardian.example.com/admin`, the browser sends:

`Origin: https://guardian.example.com`

Set this **before or right after** first remote login (then restart Focus Guard so the process reads env):

```text
FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS=https://guardian.example.com
```

How you set env depends on how you start Focus Guard (user session, scheduled task, service wrapper). If you use a shortcut, you can set system or user env vars under **Windows Settings → System → About → Advanced system settings → Environment variables**.

**Restart Focus Guard** after changing environment variables.

Details: `focus_guard/core/admin_gateway/config.py` and `INSTALL_WINDOWS.md` § Remote guardian access.

---

## 6) Verify from another network

On your phone (cellular, not Wi‑Fi):

1. Open `https://guardian.example.com/admin`
2. Log in with the **wizard admin password**
3. Confirm dashboard and settings load.

Optional API check from any machine that can reach the URL (repo root):

```powershell
python scripts/admin_gateway_smoke.py --password "<ADMIN_PASSWORD>" --base-url https://guardian.example.com
```

---

## 7) Strongly recommended: Cloudflare Access (who can open the URL)

Without **Access**, anyone who guesses or learns the URL can hit the **login page** (brute-force risk — see parking lot **FR-025**).

In Zero Trust:

1. **Access** → **Applications** → **Add an application** → **Self-hosted**.
2. **Application domain:** `guardian.example.com` (same hostname as the tunnel).
3. Add a **policy** (e.g. allow emails ending in `@yourfamily.com`, or Google/GitHub login for specific accounts).

Then only identities passing Access reach your tunnel; Focus Guard’s own password remains a second layer (defense in depth). Long-term IdP inside the app is **FR-024**.

---

## Troubleshooting

| Issue | What to check |
|--------|----------------|
| **502** / bad gateway | Focus Guard not running; wrong service URL (must be `127.0.0.1:58393`); `cloudflared` service stopped. |
| **403** `origin not allowed` | Set `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS` exactly to `https://guardian.example.com` (no path); restart app. |
| **SSL errors** | Browser must use **https** to the Cloudflare hostname; do not point the tunnel at `https://127.0.0.1:58393`. |
| Tunnel “down” in dashboard | PC asleep, firewall blocking outbound QUIC/HTTPS, or token revoked — reinstall connector with new token if needed. |
| **Quick Tunnel** (`trycloudflare.com`) | Hostname changes often → you must update `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS` each time. Prefer a **named tunnel + your domain**. |

---

## Security reminder

Do **not** use consumer **router port-forward to 58393** as your primary remote path. The tunnel keeps the admin surface off a raw public TCP listener on your home IP. See `ADR_001_REMOTE_ADMIN_ACCESS.md`.
