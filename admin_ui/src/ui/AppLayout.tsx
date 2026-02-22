import { NavLink, Outlet, useNavigate } from "react-router-dom";

import { useAuth } from "../auth/AuthProvider";

const NAV_ITEMS = [
  { to: "/", label: "Dashboard" },
  { to: "/exceptions", label: "Exceptions" },
  { to: "/devices", label: "Devices" },
  { to: "/settings", label: "Settings" },
];

export function AppLayout() {
  const navigate = useNavigate();
  const { user, logout } = useAuth();

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-4 py-4 md:px-6 md:py-6">
      <a href="#main-content" className="sr-only focus:not-sr-only focus:fixed focus:left-3 focus:top-3 focus:z-50 focus:rounded-md focus:bg-white focus:px-3 focus:py-2 focus:text-sm focus:font-semibold focus:text-ink">
        Skip to main content
      </a>
      <div className="grid min-h-[calc(100vh-2rem)] gap-4 md:grid-cols-[240px_1fr] md:gap-6">
        <aside className="hidden rounded-2xl border border-slate-300/70 bg-white/85 p-4 shadow-sm backdrop-blur md:flex md:flex-col">
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocean">FocusGuard Admin</p>
          <h1 className="mt-2 font-display text-2xl text-ink">Parent Console</h1>
          {user ? <p className="mt-2 text-xs text-gray-500">Signed in as {user.username}</p> : null}

          <nav aria-label="Primary" className="mt-6 flex flex-1 flex-col gap-2">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === "/"}
                className={({ isActive }) =>
                  `rounded-lg px-3 py-2 text-sm font-semibold transition ${
                    isActive ? "bg-ocean text-white" : "text-gray-700 hover:bg-slate-100"
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <button
            type="button"
            aria-label="Sign out"
            className="mt-2 rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm font-semibold text-gray-700 hover:bg-slate-50"
            onClick={async () => {
              await logout();
              navigate("/login", { replace: true });
            }}
          >
            Sign out
          </button>
        </aside>

        <section id="main-content" className="rounded-2xl border border-slate-300/70 bg-white/85 p-5 pb-24 shadow-sm backdrop-blur md:p-6 md:pb-6">
          <header className="mb-5 border-b border-slate-200 pb-4 md:hidden">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-ocean">FocusGuard Admin</p>
            <h1 className="mt-1 font-display text-2xl text-ink">Parent Console</h1>
            {user ? <p className="mt-1 text-xs text-gray-500">Signed in as {user.username}</p> : null}
          </header>
          <Outlet />
        </section>
      </div>

      <nav aria-label="Primary mobile" className="fixed inset-x-0 bottom-0 z-10 border-t border-slate-300 bg-white/95 p-2 backdrop-blur md:hidden">
        <div className="mx-auto grid max-w-6xl grid-cols-4 gap-2">
          {NAV_ITEMS.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `rounded-lg px-2 py-2 text-center text-xs font-semibold transition ${
                  isActive ? "bg-ocean text-white" : "text-gray-700 hover:bg-slate-100"
                }`
              }
            >
              {item.label}
            </NavLink>
          ))}
        </div>
      </nav>
    </main>
  );
}
