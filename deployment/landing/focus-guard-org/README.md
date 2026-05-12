# Landing page for `focus-guard.org` (optional)

The file **`index.html`** in this folder is a **single static page**: short explanation + a button that links to **`https://guardian.focus-guard.org/admin`** (the real Focus Guard admin UI, which already has its own login).

**You do not need this folder** if you only redirect the apex domain to the guardian URL (see the main guide — that is the fastest path).

---

## Before you publish anything

1. **Real “who may open the dashboard” login (recommended)** is **Cloudflare Zero Trust Access** on **`guardian.focus-guard.org`**, not this HTML file. See  
   `docs/planning/mvp/FOCUS_GUARD_LANDING_AND_ACCESS.md` §3.

2. If the guardian hostname is **not** `guardian.focus-guard.org`, edit **`index.html`** and change the `href` on the “Open guardian dashboard” link.

---

## Option A — Upload to Cloudflare Pages (apex / `www` shows this page)

High level (Cloudflare UI changes; use their current docs if labels differ):

1. Log in to [Cloudflare Dashboard](https://dash.cloudflare.com/).
2. **Workers & Pages** → **Create** → **Pages** → **Upload assets** (or “Direct Upload”).
3. Project name e.g. `focus-guard-landing` → drag this **folder** (or zip containing `index.html` at root) → **Deploy site**.
4. **Custom domains** on the Pages project → **Set up a domain** → add **`focus-guard.org`** and optionally **`www.focus-guard.org`**.  
   Cloudflare will show **DNS** changes; approve them (often automatic if the zone is already on Cloudflare).
5. Wait until the Pages URL and custom domain show **Active**. Visit `https://focus-guard.org` — you should see this landing page.

**Conflict warning:** If the apex already has an **A** or **AAAA** record you do not need, Pages setup may ask to replace it — follow Cloudflare’s prompts so **traffic to the apex goes to Pages**.

---

## Option B — Do not host a page; redirect apex to guardian

Faster if you only want “typing `focus-guard.org` should end up at the dashboard”.  
See **`docs/planning/mvp/FOCUS_GUARD_LANDING_AND_ACCESS.md` §2** (redirect rules).

---

## Repo / license

This HTML is project-owned static content for operators. Customize copy and styling as you like.
