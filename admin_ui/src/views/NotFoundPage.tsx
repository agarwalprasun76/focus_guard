import { Link } from "react-router-dom";

export function NotFoundPage() {
  return (
    <main className="grid min-h-screen place-items-center px-4">
      <div className="rounded-2xl border border-slate-300 bg-white/90 p-8 text-center shadow-md">
        <h1 className="font-display text-3xl text-ink">Page not found</h1>
        <p className="mt-2 text-sm text-gray-600">This route does not exist in the current MVP scaffold.</p>
        <Link
          to="/"
          className="mt-5 inline-block rounded-lg bg-ember px-4 py-2 font-semibold text-white hover:bg-amber-700"
        >
          Return Home
        </Link>
      </div>
    </main>
  );
}
