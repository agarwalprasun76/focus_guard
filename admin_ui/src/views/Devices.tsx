import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { ApiClientError, devicesApi } from "../api";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

export function Devices() {
  const online = useOnlineStatus();
  const queryClient = useQueryClient();
  const [pendingMode, setPendingMode] = useState<{
    deviceId: string;
    mode: "tracking" | "advisory" | "enforcing";
  } | null>(null);
  const [password, setPassword] = useState("");
  const [showPasswordPrompt, setShowPasswordPrompt] = useState(false);

  const devicesQuery = useQuery({
    queryKey: ["devices"],
    queryFn: () => devicesApi.listDevices(),
    refetchInterval: online ? 30000 : false,
  });

  const setModeMutation = useMutation({
    mutationFn: ({ deviceId, mode }: { deviceId: string; mode: "tracking" | "advisory" | "enforcing" }) =>
      devicesApi.setDeviceEnforcement(deviceId, {
        mode,
        password: password || undefined,
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["devices"] });
      queryClient.invalidateQueries({ queryKey: ["settings-enforcement"] });
      setPendingMode(null);
      setPassword("");
      setShowPasswordPrompt(false);
    },
    onError: (error) => {
      if (
        error instanceof ApiClientError &&
        (error.message.toLowerCase().includes("password required") ||
          error.message.toLowerCase().includes("password_required"))
      ) {
        setShowPasswordPrompt(true);
      }
    },
  });

  if (devicesQuery.isLoading) {
    return <LoadingState label="devices" />;
  }

  if (devicesQuery.isError) {
    const message =
      devicesQuery.error instanceof ApiClientError
        ? `${devicesQuery.error.code}: ${devicesQuery.error.message}`
        : "Unable to load devices";
    return <ErrorState message={message} />;
  }

  const raw = devicesQuery.data?.devices;
  const devices = Array.isArray(raw) ? raw : [];

  return (
    <div className="space-y-4">
      {!online ? <OfflineState message="You are offline. Device polling will resume once connected." /> : null}
      <h2 className="font-display text-2xl text-ink">Devices</h2>
      <p className="text-sm text-gray-600">Single-device MVP with 30s polling cadence for status monitoring.</p>

      {devices.length === 0 ? (
        <EmptyState message="No devices are currently available." />
      ) : (
        <ul className="space-y-2">
          {devices.map((device) => {
            const id = device?.id ?? "unknown";
            const name = device?.name ?? "Unnamed device";
            const status = device?.status ?? "unknown";
            const mode = device?.enforcement_mode ?? "enforcing";
            const browsers = device?.browser_status?.connected_browsers ?? 0;
            return (
              <li key={id} className="rounded-xl border border-slate-300 bg-white px-4 py-3">
                <p className="text-sm font-semibold text-ink">{name}</p>
                <p className="mt-1 text-xs text-gray-500">
                  {status} • {mode} • browsers {browsers}
                </p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  {(["tracking", "advisory", "enforcing"] as const).map((candidateMode) => (
                    <button
                      key={`${id}-${candidateMode}`}
                      type="button"
                      disabled={setModeMutation.isPending}
                      onClick={() => {
                        if (candidateMode !== mode) {
                          setPendingMode({ deviceId: id, mode: candidateMode });
                          setShowPasswordPrompt(false);
                          setPassword("");
                          setModeMutation.mutate({ deviceId: id, mode: candidateMode });
                        }
                      }}
                      className={`rounded-md px-2.5 py-1 text-xs font-medium transition ${
                        candidateMode === mode
                          ? "bg-ocean text-white"
                          : "border border-slate-200 text-gray-600 hover:bg-slate-50"
                      } disabled:opacity-50`}
                    >
                      {candidateMode}
                    </button>
                  ))}
                </div>
              </li>
            );
          })}
        </ul>
      )}
      {showPasswordPrompt && pendingMode ? (
        <div className="rounded-lg border border-slate-200 bg-slate-50 p-3">
          <p className="text-xs text-gray-700">
            Admin password required to set <strong>{pendingMode.deviceId}</strong> to{" "}
            <strong>{pendingMode.mode}</strong>.
          </p>
          <div className="mt-2 flex items-center gap-2">
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded border border-slate-300 px-2 py-1 text-sm"
              placeholder="Admin password"
            />
            <button
              type="button"
              disabled={setModeMutation.isPending || !password}
              onClick={() => setModeMutation.mutate(pendingMode)}
              className="rounded bg-ocean px-3 py-1 text-xs font-semibold text-white disabled:opacity-50"
            >
              Confirm
            </button>
            <button
              type="button"
              onClick={() => {
                setShowPasswordPrompt(false);
                setPendingMode(null);
                setPassword("");
              }}
              className="text-xs text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        </div>
      ) : null}
      {setModeMutation.isError ? (
        <p className="text-xs text-red-600">
          {setModeMutation.error instanceof ApiClientError
            ? setModeMutation.error.message
            : "Failed to update device enforcement mode"}
        </p>
      ) : null}
      {setModeMutation.isSuccess ? (
        <p className="text-xs text-emerald-600">Device enforcement mode updated.</p>
      ) : null}
    </div>
  );
}
