import axios from "axios";

const gatewayUrl =
  import.meta.env.VITE_GATEWAY_URL ?? "/gateway";
const historyUrl =
  import.meta.env.VITE_HISTORY_URL ?? "/history";

export type ChatMessage = {
  room: string;
  user: string;
  text: string;
  timestamp: string;
};

export type MessageEnvelope = {
  type: string;
  payload: ChatMessage;
};

export const buildWsUrl = (room: string, token?: string, _user?: string) => {
  const base = gatewayUrl.replace(/^http/, "ws").replace(/\/+$/, "");
  // Ensure /gateway prefix for WebSocket endpoint
  let url = base.endsWith("/gateway")
    ? `${base}/ws/${encodeURIComponent(room)}`
    : `${base}/gateway/ws/${encodeURIComponent(room)}`;
  if (token) {
    url += `?token=${encodeURIComponent(token)}`;
  }
  return url;
};

export async function fetchHistory(
  room: string,
  limit = 50,
): Promise<ChatMessage[]> {
  // Ensure /history/{room} endpoint
  const url = `${historyUrl.replace(/\/+$/, "")}/history/${encodeURIComponent(room)}`;
  const resp = await axios.get<ChatMessage[]>(
    url,
    { params: { limit } },
  );
  return resp.data;
}

