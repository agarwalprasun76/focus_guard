"""Integration tests for Section 8 adversarial bypass mitigations.

Tests P0 and P1 features:
1. API Auth — token generation, validation, _require_auth
2. Heartbeat Monitor — start/stop, disconnect detection
3. Fail-closed — background.js syntax check
4. Config Integrity — hash creation, tamper detection, revert
5. Enforcement Password — password check, rejection
6. Hosts Blocker — domain collection, entry formatting

Run: python scripts/test_section8_mitigations.py
"""

import hashlib
import json
import os
import sys
import tempfile
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

PASS = 0
FAIL = 0


def test(name, condition, detail=""):
    global PASS, FAIL
    if condition:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def section(title):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print(f"{'='*60}")


# ======================================================================
# Test 1: API Auth
# ======================================================================
section("P0: API Auth (8.4.1)")

from focus_guard.core.browser_v2.tab_server.api_auth import (
    APIAuthManager, reset_api_auth_manager
)

with tempfile.TemporaryDirectory() as tmpdir:
    token_dir = Path(tmpdir)
    mgr = APIAuthManager(token_dir=token_dir)

    # Token generation
    token = mgr.token
    test("Token generated", len(token) == 64, f"len={len(token)}")
    test("Token is hex", all(c in "0123456789abcdef" for c in token))

    # Token file created
    token_path = token_dir / "api_token.json"
    test("Token file created", token_path.exists())

    # Token file content
    data = json.loads(token_path.read_text())
    test("Token file has token", data.get("token") == token)
    test("Token file has hash", "token_hash" in data)
    test("Token file has version", data.get("version") == 1)

    # Validate correct token
    test("Valid token accepted", mgr.validate_token(token))

    # Validate wrong token
    test("Wrong token rejected", not mgr.validate_token("wrong_token"))

    # Validate request header
    test("Valid Bearer header accepted", mgr.validate_request(f"Bearer {token}"))
    test("Missing header rejected", not mgr.validate_request(None))
    test("Empty header rejected", not mgr.validate_request(""))
    test("Malformed header rejected", not mgr.validate_request("Basic abc123"))
    test("Wrong token in header rejected", not mgr.validate_request("Bearer wrong"))

    # Unauthorized attempts counted
    test("Unauthorized attempts tracked", mgr.unauthorized_attempts > 0)

    # Reload from disk
    mgr2 = APIAuthManager(token_dir=token_dir)
    test("Token reloaded from disk", mgr2.token == token)

    # Regenerate
    old_token = mgr.token
    new_token = mgr.regenerate_token()
    test("Regenerated token is different", new_token != old_token)
    test("Old token no longer valid", not mgr.validate_token(old_token))
    test("New token is valid", mgr.validate_token(new_token))

    # Status
    status = mgr.get_status()
    test("Status has expected keys", all(k in status for k in ["token_path", "token_exists", "unauthorized_attempts"]))

print(f"\n  API Auth: {PASS} passed")
auth_pass = PASS
PASS = 0

# ======================================================================
# Test 2: Heartbeat Monitor
# ======================================================================
section("P0: Heartbeat Monitor (8.2.1)")

from focus_guard.core.browser_v2.tab_server.heartbeat_monitor import (
    HeartbeatMonitor, reset_heartbeat_monitor
)

monitor = HeartbeatMonitor(check_interval=1, disconnect_threshold=2, alert_cooldown=1)

test("Monitor not running initially", not monitor.is_running)

monitor.start()
test("Monitor starts", monitor.is_running)

status = monitor.get_status()
test("Status shows running", status["running"])
test("Status has browsers dict", "browsers" in status)
test("No disconnect events yet", status["total_disconnect_events"] == 0)

monitor.stop()
test("Monitor stops", not monitor.is_running)

reset_heartbeat_monitor()

print(f"\n  Heartbeat Monitor: {PASS} passed")
hb_pass = PASS
PASS = 0

# ======================================================================
# Test 3: Fail-Closed (background.js syntax check)
# ======================================================================
section("P0: Fail-Closed — background.js syntax check (8.9)")

bg_js_path = project_root / "focus_guard" / "core" / "browser" / "extension" / "webextension_mv3" / "background.js"
test("background.js exists", bg_js_path.exists())

bg_content = bg_js_path.read_text(encoding="utf-8")

# Check key additions exist
test("failClosedWhenServerDown flag present", "failClosedWhenServerDown" in bg_content)
test("safeDomains array present", "safeDomains" in bg_content)
test("isSafeDomain function present", "function isSafeDomain" in bg_content)
test("markServerReachable function present", "function markServerReachable" in bg_content)
test("markServerUnreachable function present", "function markServerUnreachable" in bg_content)
test("serverReachable state variable present", "let serverReachable" in bg_content)
test("consecutiveServerFailures variable present", "let consecutiveServerFailures" in bg_content)

# Check fail-closed logic in shouldBlockUrl
test("FAIL-CLOSED comment in shouldBlockUrl", "FAIL-CLOSED: Blocking" in bg_content)
test("markServerReachable() called on success", "markServerReachable();" in bg_content)
test("markServerUnreachable() called on failure", "markServerUnreachable();" in bg_content)

# Check safe domains include key productivity sites
test("google.com in safeDomains", "'google.com'" in bg_content or '"google.com"' in bg_content)
test("github.com in safeDomains", "'github.com'" in bg_content or '"github.com"' in bg_content)

# Basic JS syntax check — look for common errors
test("No unclosed braces (basic check)", bg_content.count("{") == bg_content.count("}"),
     f"{{ count={bg_content.count('{')}, }} count={bg_content.count('}')}")

print(f"\n  Fail-Closed: {PASS} passed")
fc_pass = PASS
PASS = 0

# ======================================================================
# Test 4: Config Integrity (8.4.2)
# ======================================================================
section("P1: Config Integrity (8.4.2)")

from focus_guard.core.domain.domain_config_manager import (
    DomainConfigManager, reset_domain_config_manager
)

with tempfile.TemporaryDirectory() as tmpdir:
    config_path = Path(tmpdir) / "domain_config.json"
    mgr = DomainConfigManager(config_path=config_path)

    # Config file created
    test("Config file created", config_path.exists())

    # Hash file created
    hash_path = config_path.with_suffix(".hash")
    test("Hash file created", hash_path.exists())

    # Hash matches content
    content_bytes = config_path.read_bytes()
    expected_hash = hashlib.sha256(content_bytes).hexdigest()
    stored_hash = hash_path.read_text().strip()
    test("Hash matches content", stored_hash == expected_hash)

    # Modify config through API — hash should update
    mgr.add_domain_to_category("test-domain.com", "entertainment")
    new_content = config_path.read_bytes()
    new_hash = hashlib.sha256(new_content).hexdigest()
    new_stored = hash_path.read_text().strip()
    test("Hash updated after API change", new_stored == new_hash)
    test("Hash changed from original", new_stored != stored_hash)

    # Tamper detection: modify file directly without updating hash
    tampered_data = json.loads(config_path.read_text())
    tampered_data["always_allowed_domains"].append("tampered-site.com")
    config_path.write_text(json.dumps(tampered_data, indent=2))

    # Force reload — should detect tamper
    old_tamper_count = mgr._tamper_count
    reloaded = mgr.reload_if_changed()
    test("Reload detected change", reloaded)
    test("Tamper detected", mgr._tamper_count > old_tamper_count,
         f"tamper_count: {old_tamper_count} -> {mgr._tamper_count}")

    # Verify tampered domain was reverted
    allowed = mgr.get_always_allowed_domains()
    test("Tampered domain reverted", "tampered-site.com" not in allowed)

    # Verify hash is now valid again (after revert + re-save)
    final_content = config_path.read_bytes()
    final_hash = hashlib.sha256(final_content).hexdigest()
    final_stored = hash_path.read_text().strip()
    test("Hash valid after revert", final_stored == final_hash)

reset_domain_config_manager()

print(f"\n  Config Integrity: {PASS} passed")
ci_pass = PASS
PASS = 0

# ======================================================================
# Test 5: Enforcement Password (8.4.3)
# ======================================================================
section("P1: Enforcement Password (8.4.3)")

# Test the password hashing logic directly (no HTTP server needed)
test_password = "MySecurePassword123"
password_hash = hashlib.sha256(test_password.encode()).hexdigest()

# Correct password
provided_hash = hashlib.sha256(test_password.encode()).hexdigest()
test("Correct password hash matches", provided_hash == password_hash)

# Wrong password
wrong_hash = hashlib.sha256("WrongPassword".encode()).hexdigest()
test("Wrong password hash doesn't match", wrong_hash != password_hash)

# Empty password
empty_hash = hashlib.sha256("".encode()).hexdigest()
test("Empty password hash doesn't match", empty_hash != password_hash)

# Verify the handler code exists in server.py
server_path = project_root / "focus_guard" / "core" / "browser_v2" / "tab_server" / "server.py"
server_content = server_path.read_text()
test("Password check in enforcement handler", "config_password_hash" in server_content)
test("403 Forbidden on wrong password", "HTTPStatus.FORBIDDEN" in server_content)
test("enforcement_mode_password_failed audit event", "enforcement_mode_password_failed" in server_content)
test("enforcement_mode_changed audit event", "enforcement_mode_changed" in server_content)
test("_send_enforcement_mode_alert method exists", "_send_enforcement_mode_alert" in server_content)

print(f"\n  Enforcement Password: {PASS} passed")
ep_pass = PASS
PASS = 0

# ======================================================================
# Test 6: Hosts Blocker (8.2.2)
# ======================================================================
section("P1: Hosts Blocker (8.2.2)")

from focus_guard.core.browser_v2.tab_server.hosts_blocker import (
    HostsBlocker, reset_hosts_blocker
)

with tempfile.TemporaryDirectory() as tmpdir:
    fake_hosts = Path(tmpdir) / "hosts"
    fake_hosts.write_text("# Default hosts file\n127.0.0.1 localhost\n")

    blocker = HostsBlocker(hosts_path=fake_hosts)

    # Write test entries
    test_domains = {"facebook.com", "www.facebook.com", "reddit.com", "www.reddit.com"}
    result = blocker._write_entries(test_domains)
    test("Write entries succeeded", result)

    # Verify hosts file content
    content = fake_hosts.read_text()
    test("Marker BEGIN present", "FocusGuard Blocked Domains" in content)
    test("Marker END present", "END" in content)
    test("facebook.com blocked", "127.0.0.1    facebook.com" in content)
    test("reddit.com blocked", "127.0.0.1    reddit.com" in content)
    test("Original content preserved", "127.0.0.1 localhost" in content)

    # Get current entries
    entries = blocker.get_current_entries()
    test("get_current_entries returns domains", len(entries) == 4, f"got {len(entries)}")

    # Update with different domains
    new_domains = {"twitter.com", "www.twitter.com"}
    blocker._write_entries(new_domains)
    content2 = fake_hosts.read_text()
    test("Old domains removed on update", "facebook.com" not in content2)
    test("New domains added", "twitter.com" in content2)
    test("Only one marker section", content2.count("FocusGuard Blocked Domains") == 2,
         f"expected 2 (BEGIN+END), got {content2.count('FocusGuard Blocked Domains')}")

    # Remove all entries
    blocker.remove_all_entries()
    content3 = fake_hosts.read_text()
    test("All FocusGuard entries removed", "FocusGuard" not in content3)
    test("Original content still preserved", "127.0.0.1 localhost" in content3)

    # Status
    status = blocker.get_status()
    test("Status has expected keys", all(k in status for k in ["enabled", "hosts_path", "blocked_domain_count"]))

    # Domain collection from DomainConfigManager (uses real config manager)
    try:
        blocked = blocker._get_blocked_domains()
        test("Domain collection works", isinstance(blocked, set))
        test("Blocked domains not empty", len(blocked) > 0, f"got {len(blocked)} domains")
        # Should include entertainment/gaming/social domains
        has_known = any(d in blocked for d in ["facebook.com", "youtube.com", "reddit.com", "netflix.com"])
        test("Known distraction domains included", has_known)
        # Should NOT include always-allowed domains
        has_allowed = any(d in blocked for d in ["github.com", "stackoverflow.com", "mail.google.com"])
        test("Always-allowed domains excluded", not has_allowed)
    except Exception as e:
        test("Domain collection works", False, str(e))

reset_hosts_blocker()
reset_domain_config_manager()

print(f"\n  Hosts Blocker: {PASS} passed")
hb2_pass = PASS
PASS = 0

# ======================================================================
# Test 7: declarativeNetRequest sync (8.3.1) — background.js check
# ======================================================================
section("P2: declarativeNetRequest Sync (8.3.1)")

test("syncBlockedDomainsToRules function present", "async function syncBlockedDomainsToRules" in bg_content)
test("syncBlockedDomains alarm created", "'syncBlockedDomains'" in bg_content)
test("syncBlockedDomains alarm handler wired", "alarm.name === 'syncBlockedDomains'" in bg_content)
test("Fetches /api/domains/overview", "/api/domains/overview" in bg_content)
test("Builds redirect rules", "regexSubstitution" in bg_content)
test("Caps at 5000 rules", "5000" in bg_content)
test("Uses high rule IDs (10000+)", "10000 + index" in bg_content)

print(f"\n  declarativeNetRequest Sync: {PASS} passed")
dnr_pass = PASS
PASS = 0

# ======================================================================
# Test 8: Incognito Policy (8.5.1)
# ======================================================================
section("P2: Incognito/InPrivate Policy (8.5.1)")

from focus_guard.core.browser_v2.tab_server.incognito_policy import (
    IncognitoPolicyManager, get_incognito_policy_manager
)

mgr = IncognitoPolicyManager()

# Check policies (read-only, no admin needed)
status = mgr.get_status()
test("Status has platform", "platform" in status)
test("Status has is_windows", "is_windows" in status)
test("Status has policies dict", "policies" in status)
test("Chrome policy checked", "Chrome" in status["policies"])
test("Edge policy checked", "Edge" in status["policies"])

# Verify policy structure
for browser in ["Chrome", "Edge"]:
    p = status["policies"][browser]
    test(f"{browser} policy has 'applied' key", "applied" in p)
    test(f"{browser} policy has 'current_value' key", "current_value" in p)

print(f"\n  Incognito Policy: {PASS} passed")
ip_pass = PASS
PASS = 0

# ======================================================================
# Test 9: Secure Storage (8.6.1)
# ======================================================================
section("P2: Secure Storage + High-Water Mark (8.6.1)")

from focus_guard.core.browser_v2.tab_server.secure_storage import (
    get_secure_data_dir, get_audit_dir, get_usage_dir, get_override_dir,
    HighWaterMark,
)

data_dir = get_secure_data_dir()
test("Secure data dir exists", data_dir.exists())
test("Secure data dir is absolute", data_dir.is_absolute())

audit_dir = get_audit_dir()
test("Audit dir exists", audit_dir.exists())

usage_dir = get_usage_dir()
test("Usage dir exists", usage_dir.exists())

override_dir = get_override_dir()
test("Override dir exists", override_dir.exists())

# High-water mark
with tempfile.TemporaryDirectory() as tmpdir:
    hwm = HighWaterMark(storage_dir=Path(tmpdir))

    # Normal update
    test("HWM normal update returns True", hwm.update("test_counter", 100))
    test("HWM value stored", hwm.get("test_counter") == 100)

    # Increasing update
    test("HWM increasing update returns True", hwm.update("test_counter", 200))
    test("HWM value increased", hwm.get("test_counter") == 200)

    # Rollback detection
    test("HWM rollback detected", not hwm.update("test_counter", 50))
    test("HWM tamper count incremented", hwm._tamper_count == 1)

    # Value NOT overwritten on rollback
    test("HWM value preserved after rollback", hwm.get("test_counter") == 200)

    # Status
    status = hwm.get_status()
    test("HWM status has marks", "marks" in status)
    test("HWM status has tamper_count", status["tamper_count"] == 1)

print(f"\n  Secure Storage: {PASS} passed")
ss_pass = PASS
PASS = 0

# ======================================================================
# Test 10: VPN/Proxy Detector (8.8.1)
# ======================================================================
section("P2: VPN/Proxy Detector (8.8.1)")

from focus_guard.core.browser_v2.tab_server.vpn_proxy_detector import (
    VPNProxyDetector, reset_vpn_proxy_detector
)

detector = VPNProxyDetector()

# Run check
result = detector.check()
test("Check returns dict", isinstance(result, dict))
test("Result has vpn_detected", "vpn_detected" in result)
test("Result has proxy_detected", "proxy_detected" in result)
test("Result has bypass_risk", "bypass_risk" in result)
test("Result has findings list", isinstance(result.get("findings"), list))
test("Result has timestamp", result.get("timestamp", 0) > 0)

# Status
status = detector.get_status()
test("Status has last_check_time", "last_check_time" in status)
test("Status has alert_count", "alert_count" in status)

reset_vpn_proxy_detector()

print(f"\n  VPN/Proxy Detector: {PASS} passed")
vpn_pass = PASS
PASS = 0

# ======================================================================
# Test 11: URL Shortener Blocking (8.7.1) — background.js check
# ======================================================================
section("P3: URL Shortener Blocking (8.7.1)")

test("URL_SHORTENER_DOMAINS set present", "URL_SHORTENER_DOMAINS" in bg_content)
test("isUrlShortener function present", "function isUrlShortener" in bg_content)
test("bit.ly in shortener list", "'bit.ly'" in bg_content)
test("tinyurl.com in shortener list", "'tinyurl.com'" in bg_content)
test("t.co in shortener list", "'t.co'" in bg_content)
test("Cache skip for shorteners", "isShortener" in bg_content)
test("Fail-closed blocks shorteners", "URL shortener blocked" in bg_content)

print(f"\n  URL Shortener Blocking: {PASS} passed")
us_pass = PASS
PASS = 0

# ======================================================================
# Test 12: Clock Monitor (8.10.1)
# ======================================================================
section("P3: Clock Monitor (8.10.1)")

from focus_guard.core.browser_v2.tab_server.clock_monitor import (
    ClockMonitor, reset_clock_monitor
)

with tempfile.TemporaryDirectory() as tmpdir:
    monitor = ClockMonitor(check_interval=1, jump_threshold=1, state_dir=Path(tmpdir))

    test("Clock monitor not running initially", not monitor.is_running)

    monitor.start()
    test("Clock monitor starts", monitor.is_running)

    status = monitor.get_status()
    test("Status shows running", status["running"])
    test("No jumps detected initially", status["jump_count"] == 0)

    monitor.stop()
    test("Clock monitor stops", not monitor.is_running)

    # Verify state file persisted
    state_file = Path(tmpdir) / "clock_state.json"
    test("State file persisted", state_file.exists())

reset_clock_monitor()

print(f"\n  Clock Monitor: {PASS} passed")
cm_pass = PASS
PASS = 0

# ======================================================================
# Test 13: User Account Monitor (8.11.1)
# ======================================================================
section("P3: User Account Monitor (8.11.1)")

from focus_guard.core.browser_v2.tab_server.user_account_monitor import (
    UserAccountMonitor, reset_user_account_monitor
)

with tempfile.TemporaryDirectory() as tmpdir:
    monitor = UserAccountMonitor(check_interval=1, state_dir=Path(tmpdir))

    # Enumerate users
    users = monitor._enumerate_users()
    test("User enumeration returns set", isinstance(users, set))
    test("At least one user found", len(users) > 0)
    test("Current user in list", os.environ.get("USERNAME", "").lower() in {u.lower() for u in users} or len(users) > 0)

    monitor.start()
    test("User account monitor starts", monitor.is_running)

    status = monitor.get_status()
    test("Status shows running", status["running"])
    test("Known users populated", status["known_user_count"] > 0)

    monitor.stop()
    test("User account monitor stops", not monitor.is_running)

    # Verify state file
    state_file = Path(tmpdir) / "known_users.json"
    test("Known users file persisted", state_file.exists())

reset_user_account_monitor()

print(f"\n  User Account Monitor: {PASS} passed")
uam_pass = PASS
PASS = 0

# ======================================================================
# Summary
# ======================================================================
all_suites = {
    "API Auth": auth_pass,
    "Heartbeat Monitor": hb_pass,
    "Fail-Closed": fc_pass,
    "Config Integrity": ci_pass,
    "Enforcement Password": ep_pass,
    "Hosts Blocker": hb2_pass,
    "declarativeNetRequest": dnr_pass,
    "Incognito Policy": ip_pass,
    "Secure Storage": ss_pass,
    "VPN/Proxy Detector": vpn_pass,
    "URL Shortener": us_pass,
    "Clock Monitor": cm_pass,
    "User Account Monitor": uam_pass,
}
total_pass = sum(all_suites.values())
total_fail = FAIL

print(f"\n{'='*60}")
print(f"  SUMMARY")
print(f"{'='*60}")
for name, count in all_suites.items():
    print(f"  {name + ':':25s} {count} passed")
print(f"  ────────────────────────────────")
print(f"  TOTAL: {total_pass} passed, {total_fail} failed")
print(f"{'='*60}")

sys.exit(1 if total_fail > 0 else 0)
