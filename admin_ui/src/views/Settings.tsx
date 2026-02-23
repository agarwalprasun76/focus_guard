import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClientError, settingsApi } from "../api";
import type { EnforcementMode, DomainEntry } from "../api/settings";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

// ── Helpers ───────────────────────────────────────────────────────

function formatMinutes(seconds: number | null | undefined): string {
  if (seconds == null || !Number.isFinite(seconds)) return "—";
  const m = Math.round(seconds / 60);
  if (m < 60) return `${m} min`;
  const h = Math.floor(m / 60);
  const rm = m % 60;
  return rm > 0 ? `${h}h ${rm}m` : `${h}h`;
}

function deriveStatus(d: DomainEntry): "allowed" | "blocked" | "budgeted" | "tracked" {
  if (d.whitelisted || d.status === "allowed") return "allowed";
  if (d.blocked || d.status === "blocked") return "blocked";
  if ((d.budget_seconds != null && d.budget_seconds > 0) || d.status === "budgeted") return "budgeted";
  return "tracked";
}

const PROTECTION_LEVELS: {
  mode: EnforcementMode;
  label: string;
  desc: string;
  color: string;
  ring: string;
  bg: string;
}[] = [
  {
    mode: "tracking",
    label: "Monitor Only",
    desc: "Track everything, don't block. Good for observation.",
    color: "text-emerald-700",
    ring: "ring-emerald-400",
    bg: "bg-emerald-50",
  },
  {
    mode: "advisory",
    label: "Warn",
    desc: "Show warnings but allow access. Builds awareness.",
    color: "text-amber-700",
    ring: "ring-amber-400",
    bg: "bg-amber-50",
  },
  {
    mode: "enforcing",
    label: "Block",
    desc: "Full enforcement. Block distracting sites when budget is spent.",
    color: "text-red-700",
    ring: "ring-red-400",
    bg: "bg-red-50",
  },
];

// ── Enforcement Section ───────────────────────────────────────────

function EnforcementSection() {
  const queryClient = useQueryClient();
  const [password, setPassword] = useState("");
  const [showPwField, setShowPwField] = useState(false);
  const [pendingMode, setPendingMode] = useState<EnforcementMode | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const enforcementQ = useQuery({
    queryKey: ["settings-enforcement"],
    queryFn: settingsApi.getEnforcement,
    retry: 2,
  });

  const mutation = useMutation({
    mutationFn: settingsApi.setEnforcement,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings-enforcement"] });
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      setShowPwField(false);
      setPassword("");
      setPendingMode(null);
      setSuccessMsg("Protection level updated.");
    },
    onError: (error) => {
      if (
        error instanceof ApiClientError &&
        (error.message.toLowerCase().includes("password required") ||
          error.message.toLowerCase().includes("password_required"))
      ) {
        setShowPwField(true);
      }
    },
  });

  const currentMode = enforcementQ.data?.enforcement_mode ?? "enforcing";

  function handleSelect(mode: EnforcementMode) {
    if (mode === currentMode) return;
    setSuccessMsg(null);
    setPendingMode(mode);
    mutation.reset();
    mutation.mutate({ mode });
  }

  function handleConfirm() {
    if (!pendingMode) return;
    setSuccessMsg(null);
    mutation.mutate({ mode: pendingMode, password: password || undefined });
  }

  if (enforcementQ.isLoading) return <LoadingState label="protection level" />;

  const errorMsg =
    mutation.isError && !showPwField
      ? mutation.error instanceof ApiClientError
        ? mutation.error.message
        : "Failed to update protection level"
      : null;

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-display text-lg text-ink">Protection Level</h3>
        <p className="text-xs text-gray-500">How FocusGuard responds to distracting sites.</p>
      </div>

      <div className="grid gap-3 sm:grid-cols-3">
        {PROTECTION_LEVELS.map((lvl) => {
          const active = lvl.mode === currentMode;
          return (
            <button
              key={lvl.mode}
              type="button"
              disabled={mutation.isPending}
              onClick={() => handleSelect(lvl.mode)}
              className={`rounded-xl border-2 p-4 text-left transition ${
                active
                  ? `${lvl.bg} ${lvl.ring} border-transparent ring-2`
                  : "border-slate-200 hover:border-slate-300"
              }`}
            >
              <p className={`text-sm font-bold ${active ? lvl.color : "text-gray-800"}`}>
                {lvl.label}
              </p>
              <p className="mt-1 text-xs text-gray-600">{lvl.desc}</p>
              {active && (
                <span className="mt-2 inline-block rounded-full bg-white/80 px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-gray-500">
                  Active
                </span>
              )}
            </button>
          );
        })}
      </div>

      {showPwField && pendingMode && (
        <div className="flex items-end gap-2 rounded-lg border border-slate-200 bg-slate-50 p-3">
          <div className="flex-1">
            <label htmlFor="enforcement-pw" className="block text-xs font-medium text-gray-700">
              Admin password required to change to{" "}
              <strong>{PROTECTION_LEVELS.find((l) => l.mode === pendingMode)?.label}</strong>
            </label>
            <input
              id="enforcement-pw"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && handleConfirm()}
              className="mt-1 w-full rounded-md border border-slate-300 px-3 py-1.5 text-sm"
              placeholder="Enter admin password"
              autoFocus
            />
          </div>
          <button
            type="button"
            disabled={mutation.isPending || !password}
            onClick={handleConfirm}
            className="rounded-lg bg-ocean px-4 py-2 text-sm font-semibold text-white hover:bg-ocean/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Saving..." : "Confirm"}
          </button>
          <button
            type="button"
            onClick={() => {
              setShowPwField(false);
              setPendingMode(null);
              setPassword("");
              mutation.reset();
            }}
            className="rounded-lg border border-slate-300 px-3 py-2 text-sm text-gray-600 hover:bg-slate-100"
          >
            Cancel
          </button>
        </div>
      )}

      {errorMsg && <p className="text-xs text-red-600">{errorMsg}</p>}
      {successMsg && <p className="text-xs text-emerald-600">{successMsg}</p>}
    </section>
  );
}

// ── Budget Section ────────────────────────────────────────────────

const BUDGET_PRESETS = [
  { label: "15 min", seconds: 900 },
  { label: "30 min", seconds: 1800 },
  { label: "45 min", seconds: 2700 },
  { label: "1 hour", seconds: 3600 },
  { label: "1.5 hours", seconds: 5400 },
  { label: "2 hours", seconds: 7200 },
  { label: "3 hours", seconds: 10800 },
];

function BudgetSection() {
  const queryClient = useQueryClient();
  const [sliderValue, setSliderValue] = useState<number | null>(null);

  const budgetsQ = useQuery({
    queryKey: ["settings-budgets"],
    queryFn: settingsApi.getBudgets,
    retry: 2,
  });

  const masterMutation = useMutation({
    mutationFn: settingsApi.updateMasterBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings-budgets"] });
      setSliderValue(null);
    },
  });

  if (budgetsQ.isLoading) return <LoadingState label="budgets" />;
  if (budgetsQ.isError) {
    return (
      <section className="space-y-3">
        <h3 className="font-display text-lg text-ink">Time Budgets</h3>
        <ErrorState
          message={
            budgetsQ.error instanceof ApiClientError
              ? budgetsQ.error.message
              : "Unable to load budget data. The tab server may not be running."
          }
        />
      </section>
    );
  }

  const masterDaily = budgetsQ.data?.master_budget?.daily_seconds ?? 3600;
  const distractionUsed = budgetsQ.data?.distraction?.used_seconds ?? 0;
  const distractionBudget = budgetsQ.data?.distraction?.budget_seconds ?? masterDaily;
  const usedPct = distractionBudget > 0 ? Math.min(100, (distractionUsed / distractionBudget) * 100) : 0;

  const displayValue = sliderValue ?? masterDaily;

  const classificationBudgets = budgetsQ.data?.classification_budgets ?? {};

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-display text-lg text-ink">Time Budgets</h3>
        <p className="text-xs text-gray-500">Daily limits for entertainment and distracting sites.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <div className="flex items-center justify-between text-sm">
          <span className="font-medium text-gray-700">Today's Usage</span>
          <span className="text-gray-500">
            {formatMinutes(distractionUsed)} / {formatMinutes(distractionBudget)}
          </span>
        </div>
        <div className="mt-2 h-3 overflow-hidden rounded-full bg-slate-100">
          <div
            className={`h-full rounded-full transition-all ${
              usedPct > 80 ? "bg-red-500" : usedPct > 50 ? "bg-amber-500" : "bg-emerald-500"
            }`}
            style={{ width: `${usedPct}%` }}
          />
        </div>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4">
        <label className="block text-sm font-medium text-gray-700">
          Daily Distraction Budget: <strong>{formatMinutes(displayValue)}</strong>
        </label>
        <input
          type="range"
          min={900}
          max={14400}
          step={300}
          value={displayValue}
          onChange={(e) => setSliderValue(Number(e.target.value))}
          className="mt-2 w-full accent-ocean"
        />
        <div className="mt-1 flex justify-between text-[10px] text-gray-400">
          <span>15 min</span>
          <span>4 hours</span>
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {BUDGET_PRESETS.map((p) => (
            <button
              key={p.seconds}
              type="button"
              onClick={() => setSliderValue(p.seconds)}
              className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                displayValue === p.seconds
                  ? "bg-ocean text-white"
                  : "border border-slate-200 text-gray-600 hover:bg-slate-50"
              }`}
            >
              {p.label}
            </button>
          ))}
        </div>
        {sliderValue !== null && sliderValue !== masterDaily && (
          <div className="mt-3 flex items-center gap-2">
            <button
              type="button"
              disabled={masterMutation.isPending}
              onClick={() => masterMutation.mutate({ daily_seconds: sliderValue })}
              className="rounded-lg bg-ocean px-4 py-1.5 text-sm font-semibold text-white hover:bg-ocean/90 disabled:opacity-50"
            >
              {masterMutation.isPending ? "Saving..." : "Save"}
            </button>
            <button type="button" onClick={() => setSliderValue(null)} className="text-xs text-gray-500 hover:text-gray-700">
              Reset
            </button>
          </div>
        )}
        {masterMutation.isError && (
          <p className="mt-2 text-xs text-red-600">
            {masterMutation.error instanceof ApiClientError ? masterMutation.error.message : "Failed to update budget"}
          </p>
        )}
        {masterMutation.isSuccess && <p className="mt-2 text-xs text-emerald-600">Budget saved.</p>}
      </div>

      {Object.keys(classificationBudgets).length > 0 && (
        <div className="rounded-xl border border-slate-200 bg-white p-4">
          <p className="text-sm font-medium text-gray-700">Per-Category Budgets</p>
          <p className="text-[10px] text-gray-400">Adjust daily limits for each content category.</p>
          <div className="mt-3 space-y-4">
            {Object.entries(classificationBudgets).map(([cat, b]) => (
              <CategoryBudgetRow key={cat} classification={cat} currentSeconds={b?.daily_seconds ?? 0} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}

// ── Per-Category Budget Row ───────────────────────────────────────

function CategoryBudgetRow({ classification, currentSeconds }: { classification: string; currentSeconds: number }) {
  const queryClient = useQueryClient();
  const [value, setValue] = useState<number | null>(null);

  const mutation = useMutation({
    mutationFn: ({ classification, daily_seconds }: { classification: string; daily_seconds: number }) =>
      settingsApi.updateClassificationBudget(classification, daily_seconds),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings-budgets"] });
      setValue(null);
    },
  });

  const display = value ?? currentSeconds;
  const changed = value !== null && value !== currentSeconds;
  // Convert "ENTERTAINMENT:DISTRACTION" → "Entertainment"
  const rawLabel = classification.split(":")[0].replace(/_/g, " ");
  const label = rawLabel.charAt(0).toUpperCase() + rawLabel.slice(1).toLowerCase();

  return (
    <div>
      <div className="flex items-center justify-between text-sm">
        <span className="capitalize text-gray-700 font-medium">{label}</span>
        <span className="text-gray-500 font-semibold">{formatMinutes(display)}</span>
      </div>
      <input
        type="range"
        min={0}
        max={14400}
        step={300}
        value={display}
        onChange={(e) => setValue(Number(e.target.value))}
        className="mt-1 w-full accent-ocean"
      />
      <div className="flex justify-between text-[10px] text-gray-400">
        <span>Off</span>
        <span>4 hours</span>
      </div>
      {changed && (
        <div className="mt-1 flex items-center gap-2">
          <button
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ classification, daily_seconds: value! })}
            className="rounded-md bg-ocean px-3 py-1 text-xs font-semibold text-white hover:bg-ocean/90 disabled:opacity-50"
          >
            {mutation.isPending ? "Saving..." : "Save"}
          </button>
          <button type="button" onClick={() => setValue(null)} className="text-xs text-gray-500 hover:text-gray-700">
            Reset
          </button>
        </div>
      )}
      {mutation.isError && (
        <p className="mt-1 text-xs text-red-600">
          {mutation.error instanceof ApiClientError ? mutation.error.message : "Failed to update"}
        </p>
      )}
      {mutation.isSuccess && <p className="mt-1 text-xs text-emerald-600">Saved.</p>}
    </div>
  );
}

// ── Domain Management Section ─────────────────────────────────────

type StatusFilterValue = "all" | "allowed" | "blocked" | "budgeted" | "tracked";

function DomainSection() {
  const queryClient = useQueryClient();
  const online = useOnlineStatus();
  const [search, setSearch] = useState("");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState<StatusFilterValue>("all");

  const domainsQ = useQuery({
    queryKey: ["settings-domains"],
    queryFn: settingsApi.getDomains,
    refetchInterval: online ? 60000 : false,
    retry: 2,
  });

  const whitelistMut = useMutation({
    mutationFn: settingsApi.whitelistDomain,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings-domains"] }),
  });

  const categoryMut = useMutation({
    mutationFn: settingsApi.setDomainCategory,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings-domains"] }),
  });

  const budgetMut = useMutation({
    mutationFn: settingsApi.setDomainBudget,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["settings-domains"] }),
  });

  if (domainsQ.isLoading) return <LoadingState label="domains" />;
  if (domainsQ.isError) {
    const msg = domainsQ.error instanceof ApiClientError ? domainsQ.error.message : "Unable to load domains";
    return (
      <section className="space-y-3">
        <h3 className="font-display text-lg text-ink">Domain Management</h3>
        <ErrorState message={msg} />
      </section>
    );
  }

  const rawDomains: DomainEntry[] = domainsQ.data?.domains ?? [];
  const categories: string[] = domainsQ.data?.categories ?? [
    ...new Set(rawDomains.map((d) => d.category ?? "unknown").filter(Boolean)),
  ];

  const filtered = rawDomains.filter((d) => {
    if (search && !d.domain.toLowerCase().includes(search.toLowerCase())) return false;
    if (categoryFilter !== "all" && d.category !== categoryFilter) return false;
    if (statusFilter !== "all" && deriveStatus(d) !== statusFilter) return false;
    return true;
  });

  const statusCounts = rawDomains.reduce(
    (acc, d) => {
      const s = deriveStatus(d);
      acc[s] = (acc[s] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-display text-lg text-ink">Domain Management</h3>
        <p className="text-xs text-gray-500">View, search, and manage known domains.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <input
          type="text"
          placeholder="Search domains..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="min-w-[180px] flex-1 rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
        />
        <select
          value={categoryFilter}
          onChange={(e) => setCategoryFilter(e.target.value)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="all">All categories</option>
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
        <select
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value as StatusFilterValue)}
          className="rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
        >
          <option value="all">All statuses ({rawDomains.length})</option>
          <option value="allowed">Allowed ({statusCounts["allowed"] ?? 0})</option>
          <option value="blocked">Blocked ({statusCounts["blocked"] ?? 0})</option>
          <option value="budgeted">Budgeted ({statusCounts["budgeted"] ?? 0})</option>
          <option value="tracked">Tracked ({statusCounts["tracked"] ?? 0})</option>
        </select>
      </div>

      {filtered.length === 0 ? (
        <p className="text-sm text-gray-500">
          {rawDomains.length === 0 ? "No domains tracked yet." : "No domains match your filters."}
        </p>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-slate-200">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-slate-200 bg-slate-50 text-xs uppercase text-gray-500">
              <tr>
                <th className="px-3 py-2">Domain</th>
                <th className="px-3 py-2">Category</th>
                <th className="px-3 py-2">Status</th>
                <th className="px-3 py-2 text-right">Daily Budget</th>
                <th className="px-3 py-2 text-right">Usage Today</th>
                <th className="px-3 py-2 text-right">Visits</th>
                <th className="px-3 py-2 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {filtered.slice(0, 50).map((d) => (
                <DomainRow
                  key={d.domain}
                  entry={d}
                  onToggleWhitelist={(domain, add) => whitelistMut.mutate({ domain, action: add ? "add" : "remove" })}
                  onSetCategory={(domain, category) => categoryMut.mutate({ domain, category })}
                  onSetBudget={(domain, daily_seconds) => budgetMut.mutate({ domain, daily_seconds })}
                  categories={categories}
                  busy={whitelistMut.isPending || categoryMut.isPending || budgetMut.isPending}
                />
              ))}
            </tbody>
          </table>
          {filtered.length > 50 && (
            <p className="border-t border-slate-200 bg-slate-50 px-3 py-2 text-center text-xs text-gray-400">
              Showing 50 of {filtered.length} domains. Use search to narrow results.
            </p>
          )}
        </div>
      )}
    </section>
  );
}

function DomainRow({
  entry,
  onToggleWhitelist,
  onSetCategory,
  onSetBudget,
  categories,
  busy,
}: {
  entry: DomainEntry;
  onToggleWhitelist: (domain: string, add: boolean) => void;
  onSetCategory: (domain: string, category: string) => void;
  onSetBudget: (domain: string, daily_seconds: number) => void;
  categories: string[];
  busy: boolean;
}) {
  const [editingBudget, setEditingBudget] = useState(false);
  const [budgetValue, setBudgetValue] = useState(entry.budget_seconds ?? 0);
  const status = deriveStatus(entry);

  const statusBadge =
    status === "allowed"
      ? "bg-emerald-100 text-emerald-700"
      : status === "blocked"
        ? "bg-red-100 text-red-700"
        : status === "budgeted"
          ? "bg-blue-100 text-blue-700"
          : "bg-slate-100 text-slate-600";

  const statusLabel = status.charAt(0).toUpperCase() + status.slice(1);

  return (
    <tr className="hover:bg-slate-50/60">
      <td className="whitespace-nowrap px-3 py-2 font-medium text-gray-800">{entry.domain}</td>
      <td className="px-3 py-2">
        <select
          value={entry.category ?? ""}
          disabled={busy}
          onChange={(e) => onSetCategory(entry.domain, e.target.value)}
          className="rounded border border-slate-200 px-1.5 py-0.5 text-xs"
        >
          {!entry.category && <option value="">—</option>}
          {categories.map((c) => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </td>
      <td className="px-3 py-2">
        <span className={`inline-block rounded-full px-2 py-0.5 text-[10px] font-semibold ${statusBadge}`}>
          {statusLabel}
        </span>
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right text-gray-500">
        {editingBudget ? (
          <div className="flex items-center justify-end gap-1">
            <select
              value={budgetValue}
              onChange={(e) => setBudgetValue(Number(e.target.value))}
              className="rounded border border-slate-200 px-1 py-0.5 text-xs"
            >
              <option value={0}>No limit</option>
              <option value={900}>15 min</option>
              <option value={1800}>30 min</option>
              <option value={2700}>45 min</option>
              <option value={3600}>1 hour</option>
              <option value={7200}>2 hours</option>
            </select>
            <button
              type="button"
              disabled={busy}
              onClick={() => { onSetBudget(entry.domain, budgetValue); setEditingBudget(false); }}
              className="rounded bg-ocean px-1.5 py-0.5 text-[10px] font-semibold text-white hover:bg-ocean/90 disabled:opacity-40"
            >
              Set
            </button>
            <button
              type="button"
              onClick={() => setEditingBudget(false)}
              className="text-[10px] text-gray-400 hover:text-gray-600"
            >
              ✕
            </button>
          </div>
        ) : (
          <button
            type="button"
            onClick={() => { setBudgetValue(entry.budget_seconds ?? 0); setEditingBudget(true); }}
            className="text-gray-500 hover:text-ocean hover:underline"
            title="Click to set daily budget"
          >
            {entry.budget_seconds != null && entry.budget_seconds > 0 ? formatMinutes(entry.budget_seconds) : "—"}
          </button>
        )}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right text-gray-500">
        {entry.usage_seconds != null ? formatMinutes(entry.usage_seconds) : "—"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right text-gray-500">
        {entry.visit_count != null ? entry.visit_count : "—"}
      </td>
      <td className="whitespace-nowrap px-3 py-2 text-right">
        <button
          type="button"
          disabled={busy}
          onClick={() => onToggleWhitelist(entry.domain, status !== "allowed")}
          className={`rounded-md px-2 py-0.5 text-xs font-medium transition ${
            status === "allowed"
              ? "border border-red-200 text-red-600 hover:bg-red-50"
              : "border border-emerald-200 text-emerald-600 hover:bg-emerald-50"
          } disabled:opacity-40`}
        >
          {status === "allowed" ? "Remove Allow" : "Always Allow"}
        </button>
      </td>
    </tr>
  );
}

// ── Email Config Section ──────────────────────────────────────────

function EmailSection() {
  const queryClient = useQueryClient();
  const [editingRecipients, setEditingRecipients] = useState(false);
  const [recipientsInput, setRecipientsInput] = useState("");
  const [testStatus, setTestStatus] = useState<"idle" | "sending" | "sent" | "error">("idle");

  const emailQ = useQuery({
    queryKey: ["settings-email"],
    queryFn: settingsApi.getEmailConfig,
    retry: 1,
  });

  const mutation = useMutation({
    mutationFn: settingsApi.updateEmailConfig,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["settings-email"] });
      setEditingRecipients(false);
    },
  });

  const testMutation = useMutation({
    mutationFn: () => settingsApi.updateEmailConfig({ test: true } as any),
    onSuccess: () => setTestStatus("sent"),
    onError: () => setTestStatus("error"),
    onMutate: () => setTestStatus("sending"),
  });

  if (emailQ.isLoading) return <LoadingState label="email settings" />;
  if (emailQ.isError) {
    return (
      <section className="space-y-3">
        <h3 className="font-display text-lg text-ink">Email Reports</h3>
        <ErrorState
          message={emailQ.error instanceof ApiClientError ? emailQ.error.message : "Unable to load email config"}
        />
      </section>
    );
  }

  const cfg = emailQ.data!;

  function startEditRecipients() {
    setRecipientsInput(cfg.recipients.join(", "));
    setEditingRecipients(true);
  }

  function saveRecipients() {
    const parsed = recipientsInput
      .split(",")
      .map((r) => r.trim())
      .filter((r) => r.length > 0 && r.includes("@"));
    mutation.mutate({ recipients: parsed });
  }

  return (
    <section className="space-y-3">
      <div>
        <h3 className="font-display text-lg text-ink">Email Reports</h3>
        <p className="text-xs text-gray-500">Receive activity reports by email.</p>
      </div>

      <div className="rounded-xl border border-slate-200 bg-white p-4 space-y-4">
        {/* Enable toggle */}
        <div className="flex items-center justify-between">
          <div>
            <p className="text-sm font-medium text-gray-700">Email reports</p>
            <p className="text-[10px] text-gray-400">
              {cfg.is_configured ? "Configured and ready" : "Not fully configured — check SMTP settings"}
            </p>
          </div>
          <button
            type="button"
            onClick={() => mutation.mutate({ enabled: !cfg.enabled })}
            disabled={mutation.isPending}
            className={`relative inline-flex h-6 w-11 items-center rounded-full transition ${
              cfg.enabled ? "bg-ocean" : "bg-slate-300"
            }`}
          >
            <span
              className={`inline-block h-4 w-4 transform rounded-full bg-white transition ${
                cfg.enabled ? "translate-x-6" : "translate-x-1"
              }`}
            />
          </button>
        </div>

        {/* Recipients — editable */}
        <div>
          <div className="flex items-center justify-between">
            <p className="text-xs font-medium text-gray-600">Recipients</p>
            {!editingRecipients && (
              <button
                type="button"
                onClick={startEditRecipients}
                className="text-[10px] font-medium text-ocean hover:underline"
              >
                Edit
              </button>
            )}
          </div>
          {editingRecipients ? (
            <div className="mt-1 space-y-2">
              <input
                type="text"
                value={recipientsInput}
                onChange={(e) => setRecipientsInput(e.target.value)}
                placeholder="parent@email.com, guardian@email.com"
                className="w-full rounded-lg border border-slate-300 px-3 py-1.5 text-sm"
              />
              <p className="text-[10px] text-gray-400">Separate multiple emails with commas</p>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  disabled={mutation.isPending}
                  onClick={saveRecipients}
                  className="rounded-md bg-ocean px-3 py-1 text-xs font-semibold text-white hover:bg-ocean/90 disabled:opacity-50"
                >
                  {mutation.isPending ? "Saving..." : "Save Recipients"}
                </button>
                <button
                  type="button"
                  onClick={() => setEditingRecipients(false)}
                  className="text-xs text-gray-500 hover:text-gray-700"
                >
                  Cancel
                </button>
              </div>
            </div>
          ) : (
            <p className="mt-0.5 text-sm text-gray-800">
              {cfg.recipients.length > 0 ? cfg.recipients.join(", ") : "No recipients configured"}
            </p>
          )}
        </div>

        {/* Schedule summary */}
        <div className="flex flex-wrap gap-3">
          <div className="rounded-lg bg-slate-50 px-3 py-1.5">
            <span className="text-[10px] uppercase tracking-wide text-gray-400">Hourly</span>
            <p className="text-xs font-semibold text-gray-700">
              {cfg.schedule.hourly_enabled ? `Every ${cfg.schedule.hourly_interval_minutes} min` : "Off"}
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-1.5">
            <span className="text-[10px] uppercase tracking-wide text-gray-400">Daily</span>
            <p className="text-xs font-semibold text-gray-700">
              {cfg.schedule.daily_enabled ? `At ${cfg.schedule.daily_hour}:00` : "Off"}
            </p>
          </div>
          <div className="rounded-lg bg-slate-50 px-3 py-1.5">
            <span className="text-[10px] uppercase tracking-wide text-gray-400">SMTP</span>
            <p className="text-xs font-semibold text-gray-700">{cfg.smtp_server}:{cfg.smtp_port}</p>
          </div>
        </div>

        {/* Quick toggles for schedule */}
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ schedule: { hourly_enabled: !cfg.schedule.hourly_enabled } })}
            className={`rounded-md px-3 py-1 text-xs font-medium transition ${
              cfg.schedule.hourly_enabled
                ? "bg-ocean text-white"
                : "border border-slate-200 text-gray-600 hover:bg-slate-50"
            }`}
          >
            {cfg.schedule.hourly_enabled ? "Hourly: On" : "Hourly: Off"}
          </button>
          <button
            type="button"
            disabled={mutation.isPending}
            onClick={() => mutation.mutate({ schedule: { daily_enabled: !cfg.schedule.daily_enabled } })}
            className={`rounded-md px-3 py-1 text-xs font-medium transition ${
              cfg.schedule.daily_enabled
                ? "bg-ocean text-white"
                : "border border-slate-200 text-gray-600 hover:bg-slate-50"
            }`}
          >
            {cfg.schedule.daily_enabled ? "Daily: On" : "Daily: Off"}
          </button>
          <button
            type="button"
            disabled={testMutation.isPending || !cfg.is_configured}
            onClick={() => testMutation.mutate()}
            className="rounded-md border border-slate-200 px-3 py-1 text-xs font-medium text-gray-600 hover:bg-slate-50 disabled:opacity-40"
          >
            {testStatus === "sending" ? "Sending..." : "Send Test Email"}
          </button>
        </div>

        {testStatus === "sent" && <p className="text-xs text-emerald-600">Test email sent! Check your inbox.</p>}
        {testStatus === "error" && <p className="text-xs text-red-600">Failed to send test email. Check SMTP settings.</p>}

        {mutation.isError && (
          <p className="text-xs text-red-600">
            {mutation.error instanceof ApiClientError ? mutation.error.message : "Failed to update email settings"}
          </p>
        )}
        {mutation.isSuccess && <p className="text-xs text-emerald-600">Email settings updated.</p>}
      </div>
    </section>
  );
}

// ── Main Settings Page ────────────────────────────────────────────

export function Settings() {
  const online = useOnlineStatus();

  return (
    <div className="space-y-8">
      <h2 className="font-display text-2xl text-ink">Settings</h2>

      {!online && <OfflineState message="You are offline. Changes will fail until reconnected." />}

      <EnforcementSection />

      <hr className="border-slate-200" />

      <BudgetSection />

      <hr className="border-slate-200" />

      <DomainSection />

      <hr className="border-slate-200" />

      <EmailSection />
    </div>
  );
}
