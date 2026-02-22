import { requestJson } from "./client";

export type GatewayMetaResponse = {
  service: string;
  version: string;
  capabilities: {
    auth: string[];
    dashboard: boolean;
    exceptions: string[];
    devices: string[];
    origin_protection: boolean;
    request_id: boolean;
  };
  readiness: {
    gateway: "online" | "offline";
    tab_server: "online" | "offline";
    enforcement: "active" | "degraded";
  };
};

export function getMeta(): Promise<GatewayMetaResponse> {
  return requestJson<GatewayMetaResponse>("/meta");
}
