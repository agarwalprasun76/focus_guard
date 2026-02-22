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
