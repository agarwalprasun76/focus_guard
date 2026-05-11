# ADR 001 — Remote guardian / admin dashboard access

## Status

Accepted — MVP+ Week 2 (Day 11)

## Context

The admin gateway controls enforcement mode, budgets, domain rules, time-bound exceptions, and exposes monitoring/dashboard APIs. Operators often want remote access from another device or network. Exposing HTTP services directly to the Internet or to unbounded LAN interfaces raises clear confidentiality and misuse risk (credential theft, policy tampering).

## Lightweight threat model

| Actor | Capability | Impact |
|--------|-------------|--------|
| Random Internet host | Hits public IP + open port | High — brute force / abuse of bearer auth + SPA |
| Same LAN stranger | Reachable `0.0.0.0` bind on shared Wi‑Fi | Medium–High |
| Legitimate guardian | Needs reliable, auditable path | Required |

Assumptions: admin password is set; bearer tokens are short-lived; origin checks remain on for browser clients.

## Options compared

### 1) Localhost-only (baseline)

- **How:** Gateway listens on `127.0.0.1` only; browser on the same machine uses `http://127.0.0.1:58393/admin`.
- **Pros:** Smallest attack surface; no network exposure; simplest mental model.
- **Cons:** No remote control without extra tooling.
- **Cost:** None.

### 2) LAN exposure (bind to LAN / `0.0.0.0` + router or same-subnet access)

- **How:** Bind gateway to all interfaces or a LAN IP; optionally port-forward on a router.
- **Pros:** Simple for “parent laptop on home Wi‑Fi”; no vendor tunnel.
- **Cons:** Larger blast radius on shared networks; misconfigured Windows firewall → unexpected exposure; **consumer port-forward punches a raw hole from the Internet** unless carefully firewalled.
- **Cost:** Low direct cost; operational risk higher.

### 3) Authenticated outbound tunnel → localhost (**MVP+ canonical**)

- **How:** Leave the gateway on **`127.0.0.1:58393`**. Run a tunnel client (e.g. **Cloudflare Tunnel / `cloudflared`**, enterprise equivalents, or similar “reverse proxy outbound” tooling) that receives HTTPS at the vendor edge and forwards to `http://127.0.0.1:58393`. Add **edge authentication** (e.g. Cloudflare Access, OAuth) where the product supports it so the URL is not a naked admin surface.
- **Pros:** **No inbound firewall pinholes** by default; service stays localhost-bound; HTTPS termination + optional SSO at edge; aligns with Week 2 “no raw public port” guardrail when done correctly (outbound-only tunnel).
- **Cons:** Depends on vendor/process for tunnel + Access policies; operational steps for keys/domains unless using quick tunnels (which need extra care — see INSTALL).
- **Cost:** Typical free/low tiers suffice for guardians.

### 4) Hosted relay / SaaS control plane

- **How:** Devices phone home to a central API; dashboards live in cloud.
- **Pros:** Fleet scale; consistent identity; centralized audit.
- **Cons:** Highest build/operate burden; tenancy, GDPR-style data residency, uptime contracts — **explicitly deferred** beyond MVP Week 2 (see Week 2 master plan parking-lot framing).

## Decision

**Canonical MVP+ remote profile:** **Option 3 — outbound authenticated tunnel terminating on `127.0.0.1:58393`**, with **`FOCUS_GUARD_ADMIN_ALLOWED_ORIGINS`** updated to include the **browser `Origin`** of the SPA (HTTPS tunnel hostname).

**Operational fallback when tunnel is undesirable:** Option 2 only on networks you trust — **combined with tight Windows Firewall rules**, strong admin password rotation, **no** unconditional consumer port-forward — or prefer **VPN / mesh that does not advertise the gateway to the whole Internet** before raw exposure.

Localhost-only (1) remains the **production default posture** when remote access is not needed.

## Consequences

- Install docs MUST warn against naked `0.0.0.0` + public port-forward as default.
- CORS/origin guidance MUST mention tunnel/hosted UI origins.
- Day 12 runbook SHOULD give copy-paste steps for one tunnel stack (narrowed practical guide).

## Links

- `docs/planning/mvp/INSTALL_WINDOWS.md` — operator steps + guardrails  
- `docs/planning/mvp/MVP_DAY7_HANDOFF.md` — Week 1 freeze handoff continuity  
- `docs/planning/mvp/MVP_SPRINT_MASTER_PLAN_Week2.md` — Workstream E/F  
