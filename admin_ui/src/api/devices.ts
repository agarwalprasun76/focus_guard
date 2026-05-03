import { requestJson } from "./client";

export type DeviceItem = {
  id: string;
  name: string;
  status: string;
  enforcement_mode: string;
  last_seen: string | null;
  browser_status?: {
    connected_browsers?: number;
  };
};

export type DevicesResponse = {
  devices: DeviceItem[];
};

export function listDevices(): Promise<DevicesResponse> {
  return requestJson<DevicesResponse>("/devices");
}

export type SetDeviceEnforcementInput = {
  mode: "tracking" | "advisory" | "enforcing";
  password?: string;
};

export type SetDeviceEnforcementResponse = {
  updated: boolean;
  device_id: string;
  mode: "tracking" | "advisory" | "enforcing";
};

export function setDeviceEnforcement(
  deviceId: string,
  input: SetDeviceEnforcementInput,
): Promise<SetDeviceEnforcementResponse> {
  return requestJson<SetDeviceEnforcementResponse>(`/devices/${encodeURIComponent(deviceId)}/enforcement`, {
    method: "PUT",
    body: input,
  });
}
