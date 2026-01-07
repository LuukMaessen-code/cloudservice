import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildWsUrl, fetchHistory, ChatMessage, MessageEnvelope } from "./api";
import { useAuth } from "./auth";

type Status = "disconnected" | "connecting" | "connected";

export default function App() {
  const { authenticated, username, token, initialized } = useAuth();
  const [room, setRoom] = useState("general");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<Status>("disconnected");
  const socketRef = useRef<WebSocket | null>(null);

  // State for delete user messages
  const [deleting, setDeleting] = useState(false);
  const [deleteResult, setDeleteResult] = useState<boolean>(false);

  const handleDeleteUserMessages = async () => {
    if (!token) return;
    setDeleting(true);
    setDeleteResult(false);
    try {
      const { deleteUserMessages } = await import("./api");
      await deleteUserMessages(token);
      setDeleteResult(true);
      setMessages((prev) => prev.filter((msg) => msg.user !== username));
    } catch (err) {
      setDeleteResult(false);
    } finally {
      setDeleting(false);
    }
  };

  const canConnect = useMemo(
    () => initialized && authenticated && username && room.trim().length > 0,
    [initialized, authenticated, username, room],
  );

  const addMessage = useCallback((msg: ChatMessage) => {
    setMessages((prev) => [...prev, msg].slice(-200));
  }, []);

  const disconnect = useCallback(() => {
    socketRef.current?.close();
    socketRef.current = null;
    setStatus("disconnected");
  }, []);

  const connect = useCallback(async () => {
    if (!canConnect || status === "connecting" || status === "connected" || !token || !username) return;
    setStatus("connecting");
    // Only fetch history if token is present
    if (token) {
      try {
        const history = await fetchHistory(room, 50, token);
        setMessages(history);
      } catch (err: any) {
        if (err && typeof err === "object" && "isAxiosError" in err && err.isAxiosError && err.response) {
        }
      }
    } else {
      console.warn("[DEBUG] Skipping fetchHistory: token is missing");
    }

    // Pass token as query parameter in WebSocket URL
    const wsUrl = buildWsUrl(room, token, username);
    const ws = new WebSocket(wsUrl);
    socketRef.current = ws;

    ws.onopen = () => setStatus("connected");
    ws.onclose = () => setStatus("disconnected");
    ws.onerror = () => setStatus("disconnected");
    ws.onmessage = (event) => {
      try {
        const envelope = JSON.parse(event.data) as MessageEnvelope;
        addMessage(envelope.payload);
      } catch (err) {
        console.warn("Bad payload", err);
      }
    };
  }, [addMessage, canConnect, room, status, token, username]);

  const sendMessage = useCallback(() => {
    if (!socketRef.current || status !== "connected" || !input.trim()) return;
    socketRef.current.send(input.trim());
    setInput("");
  }, [input, status]);

  useEffect(() => {
    return () => {
      disconnect();
    };
  }, [disconnect]);

  if (!initialized) {
    return <div className="page"><div className="card"><p>Loading authentication...</p></div></div>;
  }
  if (!authenticated) {
    return <div className="page"><div className="card"><p>Redirecting to login...</p></div></div>;
  }
  return (
    <div className="page">
      <div className="card">
        <h1>Cloudservice Demo Chat</h1>
        <p className="subtle">
          React + NATS JetStream. Each message is sent over the bus and persisted by the
          history service.
        </p>

        <div className="row">
          <div>
            <label>User</label>
            <input value={username} disabled readOnly />
          </div>
          <div>
            <label>Room</label>
            <input
              value={room}
              onChange={(e) => setRoom(e.target.value)}
              placeholder="room name"
            />
          </div>
        </div>

        <div className="footer-row" style={{ marginTop: "1rem" }}>
          <button onClick={connect} disabled={!canConnect || status === "connected"}>
            {status === "connected" ? "Connected" : "Connect"}
          </button>
          <button className="secondary" onClick={disconnect} disabled={status === "disconnected"}>
            Disconnect
          </button>
          <button
            className="danger"
            onClick={handleDeleteUserMessages}
            disabled={deleting}
            style={{ marginLeft: "1rem" }}
          >
            {deleting ? "Deleting..." : "Delete All My Messages"}
          </button>
          {deleteResult && (
            <span style={{ marginLeft: "1rem", color: "green" }}>
              Messages deleted.
            </span>
          )}
        </div>

        <div className="messages">
          {messages.map((msg, idx) => (
            <div className="message" key={`${msg.timestamp}-${idx}`}>
              <div className="meta">
                <strong>{msg.user}</strong> • {msg.room} •{" "}
                {new Date(msg.timestamp).toLocaleTimeString()}
              </div>
              <p className="body">{msg.text}</p>
            </div>
          ))}
          {messages.length === 0 && <p className="subtle">No messages yet.</p>}
        </div>

        <div className="footer-row">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type a message and hit send"
            onKeyDown={(e) => {
              if (e.key === "Enter") sendMessage();
            }}
          />
          <button onClick={sendMessage} disabled={status !== "connected"}>
            Send
          </button>
        </div>
      </div>
    </div>
  );
}


