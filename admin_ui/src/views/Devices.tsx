import { useQuery } from "@tanstack/react-query";

import { ApiClientError, devicesApi } from "../api";
import { useOnlineStatus } from "../hooks/useOnlineStatus";
import { EmptyState, ErrorState, LoadingState, OfflineState } from "../ui/QueryStates";

export function Devices() {
  const online = useOnlineStatus();

  const devicesQuery = useQuery({
    queryKey: ["devices"],
    queryFn: () => devicesApi.listDevices(),
    refetchInterval: online ? 30000 : false,
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

  const devices = devicesQuery.data?.devices ?? [];

  return (
    <div className="space-y-4">
      {!online ? <OfflineState message="You are offline. Device polling will resume once connected." /> : null}
      <h2 className="font-display text-2xl text-ink">Devices</h2>
      <p className="text-sm text-gray-600">Single-device MVP with 30s polling cadence for status monitoring.</p>

      {devices.length === 0 ? (
        <EmptyState message="No devices are currently available." />
      ) : (
        <ul className="space-y-2">
          {devices.map((device) => (
            <li key={device.id} className="rounded-xl border border-slate-300 bg-white px-4 py-3">
              <p className="text-sm font-semibold text-ink">{device.name}</p>
              <p className="mt-1 text-xs text-gray-500">
                {device.status} • {device.enforcement_mode} • browsers {device.browser_status?.connected_browsers ?? 0}
              </p>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
