import { useQuery } from "@tanstack/react-query";

import { ApiClientError, dashboardApi } from "../api";
import { EmptyState, ErrorState, LoadingState } from "../ui/QueryStates";

function formatSavedAt(value: string): string {
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) {
    return value;
  }
  return parsed.toLocaleString();
}

function toSafeHref(rawUrl: string): string {
  const trimmed = rawUrl.trim();
  if (!trimmed) {
    return "#";
  }
  const hasScheme = /^[a-zA-Z][a-zA-Z\d+\-.]*:/.test(trimmed);
  return hasScheme ? trimmed : `https://${trimmed}`;
}

export function SavedLinks() {
  const dashboardQuery = useQuery({
    queryKey: ["saved-links", "default-device"],
    queryFn: () => dashboardApi.getDashboard({ deviceId: "default-device" }),
    refetchInterval: 20000,
    retry: 2,
    retryDelay: (attempt) => Math.min(3000, 500 * 2 ** attempt),
  });

  if (dashboardQuery.isLoading) {
    return <LoadingState label="saved links" />;
  }

  if (dashboardQuery.isError && !dashboardQuery.data) {
    const message =
      dashboardQuery.error instanceof ApiClientError
        ? `${dashboardQuery.error.code}: ${dashboardQuery.error.message}${
            dashboardQuery.error.requestId ? ` (request ${dashboardQuery.error.requestId})` : ""
          }`
        : "Unable to load saved links";
    return <ErrorState message={message} />;
  }

  const savedLinks = dashboardQuery.data?.saved_links;
  if (!savedLinks) {
    return <EmptyState message="Saved links are not available in this runtime profile." />;
  }

  return (
    <div className="space-y-4">
      <h2 className="font-display text-2xl text-ink">Saved Links</h2>
      <p className="text-sm text-gray-600">
        Links captured from blocked pages so they can be reviewed during break windows.
      </p>

      <div className="grid gap-3 md:grid-cols-3">
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Unviewed</p>
          <p className="mt-2 text-xl font-semibold text-ink">{savedLinks.unviewed}</p>
        </div>
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Total Saved</p>
          <p className="mt-2 text-xl font-semibold text-ink">{savedLinks.total}</p>
        </div>
        <div className="rounded-xl border border-slate-300 p-4">
          <p className="text-xs uppercase tracking-wide text-gray-500">Top Domains</p>
          <p className="mt-2 text-sm font-semibold text-ink">
            {savedLinks.top_domains.length > 0
              ? savedLinks.top_domains
                  .slice(0, 2)
                  .map((item) => `${item.domain} (${item.count})`)
                  .join(", ")
              : "No domain data yet"}
          </p>
        </div>
      </div>

      {savedLinks.recent.length === 0 ? (
        <EmptyState message="No saved links yet. Use Save for Later from blocked pages." />
      ) : (
        <section className="rounded-xl border border-slate-300 p-4">
          <h3 className="font-display text-lg text-ink">Recent Saved Links</h3>
          <ul className="mt-3 space-y-2">
            {savedLinks.recent.map((item) => (
              <li key={item.id} className="rounded-lg bg-slate-50 px-3 py-3">
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-sm font-semibold text-ink">{item.domain || item.title || "Saved link"}</p>
                  <span className="text-xs text-gray-500">{formatSavedAt(item.saved_at)}</span>
                </div>
                <a
                  className="mt-1 block break-all text-xs text-ocean underline decoration-ocean/40 underline-offset-2 hover:text-teal-700"
                  href={toSafeHref(item.url)}
                  target="_blank"
                  rel="noopener noreferrer"
                >
                  {item.url}
                </a>
                {item.comment ? <p className="mt-1 text-xs text-gray-700">Note: {item.comment}</p> : null}
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}
