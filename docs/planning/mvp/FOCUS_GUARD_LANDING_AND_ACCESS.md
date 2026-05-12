# `focus-guard.org` — landing page, redirects, and login (beginner-oriented)

You already have a **working admin app** at **`https://guardian.focus-guard.org/admin`** with Focus Guard’s **own login** (wizard admin password). Nothing in this doc replaces that — it only helps visitors who type the **apex** domain (`focus-guard.org`) or who want a **prettier entry** and **extra protection** at Cloudflare.

**Three separate ideas (do not confuse them):**

| Layer | Where | What it does |
|-------|--------|----------------|
| **A) Optional “landing” on the apex** | `https://focus-guard.org` | A small static page or a **redirect** to the guardian URL. |
| **B) Cloudflare Access (recommended)** | Hostname `guardian.focus-guard.org` | Cloudflare asks for **Google / GitHub / email** *before* traffic hits Focus Guard. Official docs: [Cloudflare Access](https://developers.cloudflare.com/cloudflare-one/policies/access/). |
| **C) Focus Guard login** | Inside the admin SPA | Your **wizard admin password** — always required after Access (if you use Access). |

This repository includes a **ready-made static landing page** you can upload to **Cloudflare Pages**:  
`deployment/landing/focus-guard-org/index.html` (see **`deployment/landing/focus-guard-org/README.md`**).

---

## 1) What you already have (no change required)

- **Tunnel:** `FocusGuard-admin` → **Healthy** → `guardian.focus-guard.org` → `http://127.0.0.1:58393`
- **Admin UI + login:** `https://guardian.focus-guard.org/admin`

If that URL works, **you do not need a landing page** for the product to function. The sections below are **optional polish and security**.

---

## 2) Simplest apex behavior: redirect `focus-guard.org` → guardian (no HTML)

Goal: when someone opens `https://focus-guard.org` or `https://www.focus-guard.org`, the browser ends up at **`https://guardian.focus-guard.org/admin`**.

### Steps (Cloudflare dashboard — names may vary slightly)

1. Open [Cloudflare Dashboard](https://dash.cloudflare.com/) → select zone **`focus-guard.org`** (Websites / Domains).
2. Go to **Rules** in the left sidebar (sometimes under **Rules** → **Overview**).
3. Open **Redirect Rules** (or **Single Redirect** / **Bulk Redirects** — prefer **Redirect Rules** for a few hostnames).
4. **Create rule** (or **Create redirect**).
5. **Rule name:** e.g. `apex-to-guardian`
6. **When incoming requests match…** use the rule builder, for example:
   - **Field:** `Hostname` **Operator:** `equals` **Value:** `focus-guard.org`  
   **OR** add a second condition with **OR** for `www.focus-guard.org` if you use `www`.  
   (Exact UI: sometimes “All incoming requests” + **Edit expression** — use **(http.host eq "focus-guard.org" or http.host eq "www.focus-guard.org")** if you use the expression editor.)
7. **Then…** → **URL redirect** → **Dynamic** or **Static** redirect:
   - **Target URL:** `https://guardian.focus-guard.org/admin`
   - **Status code:** `302` (temporary) while testing; later you can use `301` if permanent.
8. **Save** / **Deploy**.

Test in a **private window**: `https://focus-guard.org` → should land on the admin URL.

**Note:** If you later put **Cloudflare Pages** on the apex, **do not** also use a conflicting apex redirect — pick one behavior per hostname.

---

## 3) Cloudflare Access — “login before the dashboard” (recommended)

This is the **right place** for “only my family should see the admin URL at all”, if you are not comfortable exposing Focus Guard’s login page to the whole internet.

### Steps (Zero Trust)

1. Go to [Cloudflare Zero Trust](https://one.dash.cloudflare.com/) (same account; pick your team if asked).
2. **Access** → **Applications** → **Add an application**.
3. Choose **Self-hosted**.
4. **Application name:** e.g. `Focus Guard guardian`
5. **Session duration:** e.g. 24 hours (your choice).
6. **Application domain:** enter **`guardian.focus-guard.org`** (must match the tunnel hostname exactly — no `https://` in some UIs; follow the form).
7. **Add policy** → example:
   - **Policy name:** `Family Google`
   - **Action:** Allow
   - **Include:** **Emails** ending in `@gmail.com` *or* **Selector:** Google Workspace / **Login methods** → enable **Google** and restrict to specific emails if the UI offers it.  
   Simpler pattern: **Emails** → `is` → `focusguardapp@gmail.com` (repeat policies for each family member if needed).
8. **Save** the application.

Now when you open `https://guardian.focus-guard.org/admin`, Cloudflare shows **its** login first; after success, you still see **Focus Guard’s** login and enter the **wizard admin password**.

More detail: [Self-hosted applications · Access](https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/).

---

## 4) Optional branded landing on the apex (static HTML + Cloudflare Pages)

Use this if you want **`https://focus-guard.org`** to show a **nice page** with a button (“Open guardian dashboard”) instead of an immediate redirect.

1. On your PC, open folder **`deployment/landing/focus-guard-org/`** in this repo (contains **`index.html`**).
2. Cloudflare → **Workers & Pages** → **Create** → **Pages** → **Upload assets**.
3. Create project (e.g. `focus-guard-landing`) → upload **the folder** or a **zip** with `index.html` at the **root** → **Deploy**.
4. Pages project → **Custom domains** → **Set up a domain** → **`focus-guard.org`** (and **`www.focus-guard.org`** if you want). Follow DNS prompts.
5. Wait until status is **Active**. Visit `https://focus-guard.org` — you should see the landing page; the button goes to **`https://guardian.focus-guard.org/admin`**.

If the apex is already used by a **redirect rule** (§2), remove or adjust that rule so it does not fight Pages.

---

## 5) What we did **not** implement in code (and why)

- **No second password system** in this repo for the landing page — the button is just a link. Real pre-auth is **Cloudflare Access** (§3).
- **No automatic Cloudflare API calls** from Focus Guard — tunnel and Access stay operator-controlled in the dashboard (simpler, safer for credentials).

---

## 6) Quick decision guide

| I want… | Do this |
|---------|---------|
| Apex URL to open the dashboard immediately | §2 **Redirect rules** |
| A pretty home page on apex + button to dashboard | §4 **Pages** + repo **`index.html`** |
| Strangers must not see Focus Guard login at all | §3 **Access** on **`guardian.focus-guard.org`** |
| Only the above, minimal work | §2 **or** §4, **plus** §3 |

Related: `docs/planning/mvp/CLOUDFLARE_TUNNEL_SETUP_FOCUS_GUARD.md` (tunnel + env vars).
