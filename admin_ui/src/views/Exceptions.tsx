import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClientError, exceptionsApi } from "../api";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import type { CreateExceptionResponse, ExceptionListItem, ExceptionType } from "../api/exceptions";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

type FormState = {
  domain: string;
  type: ExceptionType;
  durationSeconds: string;
  budgetSecondsPerDay: string;
  reason: string;
  emergency: boolean;
};

const INITIAL_FORM: FormState = {
  domain: "",
  type: "temporary",
  durationSeconds: "300",
  budgetSecondsPerDay: "1800",
  reason: "",
  emergency: false,
};

type StatusFilter = "active" | "all";

function formatRelativeSeconds(value: number | null): string {
  if (value === null || value <= 0) {
    return "--";
  }
  const mins = Math.floor(value / 60);
  const secs = value % 60;
  return `${mins}m ${secs}s`;
}

function rowSubtitle(item: ExceptionListItem): string {
  const remaining = formatRelativeSeconds(item.remaining_seconds);
  const reason = item.reason ? ` • ${item.reason}` : "";
  return `${item.status} • remaining ${remaining}${reason}`;
}

export function Exceptions() {
  const queryClient = useQueryClient();
  const online = useOnlineStatus();
  const domainInputRef = useRef<HTMLInputElement | null>(null);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [form, setForm] = useState<FormState>(INITIAL_FORM);
  const [successItem, setSuccessItem] = useState<CreateExceptionResponse | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("active");

  const exceptionsQuery = useQuery({
    queryKey: ["exceptions", statusFilter],
    queryFn: () => exceptionsApi.listExceptions({ status: statusFilter, limit: 50, offset: 0 }),
    refetchInterval: online ? (statusFilter === "active" ? 10000 : 30000) : false,
  });

  const createMutation = useMutation({
    mutationFn: async () => {
      const domain = form.domain.trim().toLowerCase();
      if (!domain) {
        throw new Error("Domain is required.");
      }

      if (form.type === "temporary") {
        const duration = Number(form.durationSeconds);
        if (!Number.isFinite(duration) || duration <= 0) {
          throw new Error("Temporary mode requires duration_seconds > 0.");
        }
      }

      if (form.type === "budgeted") {
        const budget = Number(form.budgetSecondsPerDay);
        if (!Number.isFinite(budget) || budget < 0) {
          throw new Error("Budgeted mode requires budget_seconds_per_day >= 0.");
        }
      }

      return exceptionsApi.createException({
        domain,
        type: form.type,
        reason: form.reason,
        emergency: form.emergency,
        duration_seconds: form.type === "temporary" ? Number(form.durationSeconds) : undefined,
        budget_seconds_per_day: form.type === "budgeted" ? Number(form.budgetSecondsPerDay) : undefined,
      });
    },
    onSuccess: (result) => {
      setSuccessItem(result);
      setValidationError(null);
      setIsModalOpen(false);
      setForm(INITIAL_FORM);
      void queryClient.invalidateQueries({ queryKey: ["exceptions"] });
    },
    onError: (error) => {
      if (error instanceof Error && !(error instanceof ApiClientError)) {
        setValidationError(error.message);
      }
    },
  });

  const requestError =
    createMutation.error instanceof ApiClientError
      ? `${createMutation.error.code}: ${createMutation.error.message}`
      : null;

  const revokeMutation = useMutation({
    mutationFn: (exceptionId: string) => exceptionsApi.revokeException(exceptionId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["exceptions"] });
    },
  });

  const revokeError =
    revokeMutation.error instanceof ApiClientError
      ? `${revokeMutation.error.code}: ${revokeMutation.error.message}`
      : null;

  useEffect(() => {
    if (isModalOpen) {
      domainInputRef.current?.focus();
    }
  }, [isModalOpen]);

  return (
    <div className="space-y-4">
      {!online ? <OfflineState message="You are offline. Exception list polling will resume once network is restored." /> : null}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h2 className="font-display text-2xl text-ink">Exceptions</h2>
          <p className="text-sm text-gray-600">Create temporary, permanent, budgeted, or block actions from one modal.</p>
        </div>
        <button
          type="button"
          aria-haspopup="dialog"
          aria-expanded={isModalOpen}
          aria-controls="create-exception-dialog"
          className="rounded-lg bg-ocean px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700"
          onClick={() => {
            setValidationError(null);
            createMutation.reset();
            setIsModalOpen(true);
          }}
        >
          Add Exception
        </button>
      </div>

      {successItem ? (
        <div className="rounded-xl border border-emerald-300 bg-emerald-50 px-4 py-3 text-sm text-emerald-800">
          Created {successItem.type} exception for <strong>{successItem.domain}</strong> ({successItem.status})
        </div>
      ) : null}

      {requestError && !isModalOpen ? <ErrorState message={requestError} /> : null}

      <div className="rounded-xl border border-slate-300 p-4 text-sm text-gray-600">
        Manage live exceptions below. You can revoke active items directly from the list.
      </div>

      <section className="rounded-xl border border-slate-300 p-4">
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-display text-lg text-ink">Override List</h3>
          <div className="flex items-center gap-2">
            <label htmlFor="status_filter" className="text-xs font-semibold uppercase tracking-wide text-gray-500">
              Status
            </label>
            <select
              id="status_filter"
              className="rounded-lg border border-slate-300 px-2 py-1 text-sm"
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}
            >
              <option value="active">active</option>
              <option value="all">all</option>
            </select>
          </div>
        </div>

        {exceptionsQuery.isLoading ? <LoadingState label="exceptions" /> : null}
        {exceptionsQuery.isError ? (
          <ErrorState
            message={
              exceptionsQuery.error instanceof ApiClientError
                ? `${exceptionsQuery.error.code}: ${exceptionsQuery.error.message}`
                : "Unable to load exceptions"
            }
          />
        ) : null}
        {revokeError ? <ErrorState message={revokeError} /> : null}

        {!exceptionsQuery.isLoading && !exceptionsQuery.isError ? (
          exceptionsQuery.data && exceptionsQuery.data.exceptions.length > 0 ? (
            <ul className="space-y-2">
              {exceptionsQuery.data.exceptions.map((item) => (
                <li key={`${item.id}-${item.status}`} className="flex flex-wrap items-center justify-between gap-3 rounded-lg bg-slate-50 px-3 py-2">
                  <div>
                    <p className="text-sm font-semibold text-ink">{item.domain}</p>
                    <p className="text-xs text-gray-500">{rowSubtitle(item)}</p>
                  </div>
                  <button
                    type="button"
                    aria-label={`Revoke exception for ${item.domain}`}
                    className="rounded-lg border border-amber-300 bg-amber-50 px-3 py-1 text-xs font-semibold text-amber-800 hover:bg-amber-100 disabled:opacity-50"
                    disabled={item.status !== "active" || revokeMutation.isPending}
                    onClick={() => {
                      void revokeMutation.mutateAsync(item.id);
                    }}
                  >
                    {item.status === "active" ? "Revoke" : "Not Active"}
                  </button>
                </li>
              ))}
            </ul>
          ) : (
            <EmptyState message="No exceptions found for this filter." />
          )
        ) : null}
      </section>

      {isModalOpen ? (
        <div className="fixed inset-0 z-20 grid place-items-center bg-black/30 px-4">
          <div
            id="create-exception-dialog"
            role="dialog"
            aria-modal="true"
            aria-labelledby="create-exception-title"
            aria-describedby="create-exception-desc"
            className="w-full max-w-lg rounded-2xl border border-slate-300 bg-white p-5 shadow-xl"
          >
            <h3 id="create-exception-title" className="font-display text-xl text-ink">Create Exception</h3>
            <p id="create-exception-desc" className="mt-1 text-xs text-gray-500">Modes: temporary, permanent, budgeted, block</p>

            <div className="mt-4 space-y-3">
              <label className="block text-sm font-medium text-gray-700" htmlFor="domain">
                Domain
              </label>
              <input
                id="domain"
                ref={domainInputRef}
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                value={form.domain}
                onChange={(event) => setForm((prev) => ({ ...prev, domain: event.target.value }))}
                placeholder="youtube.com"
                required
              />

              <label className="block text-sm font-medium text-gray-700" htmlFor="type">
                Type
              </label>
              <select
                id="type"
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                value={form.type}
                onChange={(event) => setForm((prev) => ({ ...prev, type: event.target.value as ExceptionType }))}
              >
                <option value="temporary">temporary</option>
                <option value="permanent">permanent</option>
                <option value="budgeted">budgeted</option>
                <option value="block">block</option>
              </select>

              {form.type === "temporary" ? (
                <>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="duration_seconds">
                    Duration (seconds)
                  </label>
                  <input
                    id="duration_seconds"
                    type="number"
                    min={1}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2"
                    value={form.durationSeconds}
                    onChange={(event) => setForm((prev) => ({ ...prev, durationSeconds: event.target.value }))}
                  />
                </>
              ) : null}

              {form.type === "budgeted" ? (
                <>
                  <label className="block text-sm font-medium text-gray-700" htmlFor="budget_seconds_per_day">
                    Daily Budget (seconds)
                  </label>
                  <input
                    id="budget_seconds_per_day"
                    type="number"
                    min={0}
                    className="w-full rounded-lg border border-slate-300 px-3 py-2"
                    value={form.budgetSecondsPerDay}
                    onChange={(event) => setForm((prev) => ({ ...prev, budgetSecondsPerDay: event.target.value }))}
                  />
                </>
              ) : null}

              <label className="block text-sm font-medium text-gray-700" htmlFor="reason">
                Reason (optional)
              </label>
              <input
                id="reason"
                className="w-full rounded-lg border border-slate-300 px-3 py-2"
                value={form.reason}
                onChange={(event) => setForm((prev) => ({ ...prev, reason: event.target.value }))}
                placeholder="school assignment"
              />

              {form.type === "temporary" ? (
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input
                    type="checkbox"
                    checked={form.emergency}
                    onChange={(event) => setForm((prev) => ({ ...prev, emergency: event.target.checked }))}
                  />
                  Mark as emergency
                </label>
              ) : null}

              {validationError ? <p className="text-sm text-red-600">{validationError}</p> : null}
              {requestError ? <ErrorState message={requestError} /> : null}
            </div>

            <div className="mt-5 flex justify-end gap-2">
              <button
                type="button"
                className="rounded-lg border border-slate-300 px-4 py-2 text-sm font-semibold text-gray-700 hover:bg-slate-50"
                onClick={() => {
                  setIsModalOpen(false);
                  setValidationError(null);
                  createMutation.reset();
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                className="rounded-lg bg-ocean px-4 py-2 text-sm font-semibold text-white hover:bg-teal-700"
                disabled={createMutation.isPending}
                onClick={() => {
                  setValidationError(null);
                  void createMutation.mutateAsync();
                }}
              >
                {createMutation.isPending ? "Creating..." : "Create"}
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
