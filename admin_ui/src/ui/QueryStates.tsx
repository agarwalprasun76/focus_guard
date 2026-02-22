export function LoadingState({ label }: { label: string }) {
  return (
    <p
      role="status"
      aria-live="polite"
      className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-gray-700"
    >
      Loading {label}...
    </p>
  );
}

export function ErrorState({ message }: { message: string }) {
  return (
    <p role="alert" className="rounded-xl border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
      {message}
    </p>
  );
}

export function EmptyState({ message }: { message: string }) {
  return (
    <p
      role="status"
      aria-live="polite"
      className="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-sm text-gray-700"
    >
      {message}
    </p>
  );
}

export function OfflineState({ message }: { message: string }) {
  return (
    <p
      role="status"
      aria-live="polite"
      className="rounded-xl border border-amber-300 bg-amber-50 px-4 py-3 text-sm text-amber-800"
    >
      {message}
    </p>
  );
}
