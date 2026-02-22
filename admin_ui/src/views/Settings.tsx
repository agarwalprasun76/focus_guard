export function Settings() {
  return (
    <div className="space-y-4">
      <h2 className="font-display text-2xl text-ink">Settings</h2>
      <p className="text-sm text-gray-600">
        Account, session, and device preference settings will be available here in a future update.
      </p>

      <div className="grid gap-4 md:grid-cols-2">
        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Protection Level</h3>
          <p className="mt-1 text-xs text-gray-500">
            Control how FocusGuard responds to distracting sites.
          </p>
          <p className="mt-3 text-sm text-gray-600">Coming soon — configure enforcement mode from the dashboard.</p>
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Time Budgets</h3>
          <p className="mt-1 text-xs text-gray-500">
            Set daily limits for entertainment and social media.
          </p>
          <p className="mt-3 text-sm text-gray-600">Coming soon — adjust budgets directly from the admin console.</p>
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Email Reports</h3>
          <p className="mt-1 text-xs text-gray-500">
            Configure activity report delivery.
          </p>
          <p className="mt-3 text-sm text-gray-600">Coming soon — manage email settings without editing config files.</p>
        </section>

        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Security</h3>
          <p className="mt-1 text-xs text-gray-500">
            Admin password, API tokens, and audit log.
          </p>
          <p className="mt-3 text-sm text-gray-600">Coming soon — change password and review security events.</p>
        </section>
      </div>
    </div>
  );
}
