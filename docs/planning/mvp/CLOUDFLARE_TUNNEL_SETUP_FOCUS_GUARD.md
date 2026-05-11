# Cloudflare Tunnel → Focus Guard admin gateway (step-by-step)

This guide assumes the **monitored PC** runs Focus Guard and the admin gateway on **`http://127.0.0.1:58393`** (default). You will expose only that HTTP service through Cloudflare’s **outbound** tunnel (no router port-forward).

**Official reference (kept current by Cloudflare):**  
[Create a Cloudflare Tunnel · Cloudflare One docs](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/)

### Is `cloudflared` installed by Focus Guard?

**No — not in the current MVP build.** You install `cloudflared` separately (see §1 below). The Focus Guard installer does **not** bundle Cloudflare’s connector; tunnel **tokens**, **DNS hostnames**, and **Access** policies are always created in your **Cloudflare** account first.

If we later add an **optional assistant** inside Focus Guard (download official binary, health check, maybe service install), that work is tracked as **`FEATURE_REQUESTS_PARKING_LOT.md` [FR-030]** and will be called out in `INSTALL_WINDOWS.md` when shipped.

### End-to-end checklist — remote guardian can open the admin UI

Do these **on the monitored PC** (where Focus Guard runs), unless noted.

| Step | Action |
|------|--------|
| 1 | Start **Focus Guard** and confirm locally: `http://127.0.0.1:58393/admin` loads and `http://127.0.0.1:58393/admin/health` returns OK. |
| 2 | Ensure you have a **Cloudflare** account and a **domain** whose DNS is managed by Cloudflare. |
| 3 | Install **`cloudflared`** (§1). If `cloudflared` is not found in the terminal, reload `PATH` or restart Cursor (§1). |
| 4 | In **Zero Trust → Networks → Connectors → Cloudflare Tunnels**, **Create a tunnel**, then run the dashboard’s **`cloudflared.exe service install …`** command in **Administrator** PowerShell on this PC. |
| 5 | In the tunnel config, add a **public hostname** (e.g. `guardian.example.com`) whose **service URL** is **`http://127.0.0.1:58393`** (HTTP, not HTTPS, to loopback). |
| 6 | Set environment variable **`FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS`** to exactly **`https://guardian.example.com`** (your real hostname; scheme + host, no path). Apply it to the **same user/service account** that starts Focus Guard. |
| 7 | **Restart Focus Guard** so it reads the new env var. |
| 8 | *(Strongly recommended)* Add **Cloudflare Access** on that hostname so the world does not see your login page without SSO/MFA (§7 in this doc). |
| 9 | On a **different network** (e.g. phone on cellular), open **`https://guardian.example.com/admin`** and log in with the **wizard admin password**. |
| 10 | *(Optional)* From any machine that can reach the URL: `python scripts/admin_gateway_smoke.py --password "<pwd>" --base-url https://guardian.example.com` |

More detail for each row is in the sections below. **`INSTALL_WINDOWS.md`** § Remote guardian access has the same architecture summary and links back here.

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

**If `cloudflared` is “not recognized” right after `winget install`:** the MSI updated **machine** `PATH`, but **this PowerShell window** still has the old environment. **Cursor / VS Code terminals** often inherit `PATH` from when the **IDE started**, so even a “new” terminal tab can stay stale until you reload `PATH` (below) or **fully restart Cursor**.

1. **Easiest:** fully **quit and reopen Cursor** (or VS Code), then open a new terminal and run `cloudflared --version` again.
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

## 1.5) Tunnel name vs public URL — can I use `https://focus-guard.com`?

**Tunnel name** (e.g. `FocusGuard-admin`) is only an **internal label** in Cloudflare. It does **not** have to match the website address guardians type in the browser. You can rename tunnels later; what matters for Focus Guard is the **public hostname** you configure in the next steps.

**Public hostname (the URL you will open):**

- Cloudflare only publishes hostnames under **DNS zones attached to your Cloudflare account** — usually a **domain you registered** (at Cloudflare Registrar or anywhere else) with **nameservers pointed to Cloudflare**, or a subdomain of such a domain.
- You **cannot** pick an arbitrary URL like `https://focus-guard.com` unless **you control that domain** (it is in your Cloudflare account and DNS resolves there). If `focus-guard.com` is already owned by someone else, you would need to **buy a different available domain** or use a **subdomain of a domain you already own**.

**Choosing a name that “matches” the app:**

| Approach | Example | Notes |
|----------|---------|--------|
| **Subdomain of a domain you already have** | `https://guardian.yourfamily.com` or `https://fg-admin.example.com` | Cheapest and clearest; no need for the word “FocusGuard” in the URL. |
| **Register a new brand-style domain** | `https://focusguard.example` (if available at a registrar) | Costs money yearly; then add that zone to Cloudflare and create e.g. `https://admin.focusguard.example`. |
| **Obscure hostname** | `https://a8f3-yourname.example.com` | Slightly less guessable; **not** a substitute for **Cloudflare Access** + strong admin password. |

**What you set in Focus Guard:** `FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS` must be the **exact** origin you use (e.g. `https://guardian.yourfamily.com` — scheme + host, typically **no trailing slash** in the env value; the path `/admin` is separate in the browser).

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
