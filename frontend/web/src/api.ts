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

export const buildWsUrl = (room: string, user: string) => {
  const base = gatewayUrl.replace(/^http/, "ws").replace(/\/+$/, "");
  return `${base}/ws/${encodeURIComponent(room)}?user=${encodeURIComponent(user)}`;
};

export async function fetchHistory(
  room: string,
  limit = 50,
): Promise<ChatMessage[]> {
  const resp = await axios.get<ChatMessage[]>(
    `${historyUrl.replace(/\/+$/, "")}/${encodeURIComponent(room)}`,
    { params: { limit } },
  );
  return resp.data;
}

