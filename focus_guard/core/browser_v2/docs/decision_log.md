# Browser v2 Decision Log

| Date       | Decision | Context | Status | Follow-ups |
|------------|----------|---------|--------|------------|
| 2025-10-28 | Target Windows (Chrome & Edge) first; macOS Phase 2 | Aligns with MVP deployment focus and user availability for testing. | Accepted | Define macOS placeholders in extension packaging docs. |
| 2025-10-28 | Installer requires admin privileges | Prevents easy removal/circumvention of Focus Guard controls. | Accepted | Design elevation UX (prompt vs helper). |
| 2025-10-28 | Dev flow may use `--load-extension` until store/policy path ready | Enables progress before store publishing complexity is solved. | Accepted | Research Chrome/Edge store vs policy deployments. |
| 2025-10-28 | Telemetry defaults to local file, with coordinator pipeline integration | Simplifies initial logging while keeping path to cloud logging. | Accepted | Define local log format + coordinator hook schema. |
| 2025-10-28 | Headless browsers unsuitable for automated testing | Security restrictions block realistic site access. | Accepted | Focus integration tests on mock harness + manual real-browser smoke tests. |
| 2025-10-28 | Tab server v2 exposes callback-based health metrics | Keeps server skeleton simple while allowing controller to plug in real metrics later. | Accepted | Define concrete health payload (uptime, connected browsers, error counters). |
| 2025-10-28 | Command processing handled via injectable handler (no queue yet) | Enables fast iteration; dedicated command queue deferred until requirements clarified. | Accepted | Evaluate queue/back-pressure needs once installer + coordinator integration firm up. |
| 2026-01-31 | **Store distribution is primary path** | After failed attempts with --load-extension, registry policies, and native messaging for installation, store distribution provides best UX. | Accepted | Submit to Chrome Web Store and Edge Add-ons. |
| 2026-01-31 | Implemented full browser_v2 stack | Tab server v2 with storage, blocking, runner; installer strategies (dev/store); integration controller with lifecycle management. | Implemented | Add unit tests, wire to existing Focus Guard components. |
| 2026-01-31 | Extension popup added for user feedback | Users need visibility into connection status; popup shows connected state and tab count. | Implemented | Polish UI, add more status details. |
| 2026-01-31 | Command queue for tab close operations | Extension polls for commands; server queues close_tab commands per browser. | Implemented | Wire to blocking system for automatic tab closing. |
