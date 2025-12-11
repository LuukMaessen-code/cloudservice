import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { buildWsUrl, fetchHistory, ChatMessage, MessageEnvelope } from "./api";

type Status = "disconnected" | "connecting" | "connected";

export default function App() {
  const [user, setUser] = useState("guest");
  const [room, setRoom] = useState("general");
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [status, setStatus] = useState<Status>("disconnected");
  const socketRef = useRef<WebSocket | null>(null);

  const canConnect = useMemo(
    () => user.trim().length > 0 && room.trim().length > 0,
    [user, room],
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
    if (!canConnect || status === "connecting" || status === "connected") return;
    setStatus("connecting");
    try {
      const history = await fetchHistory(room);
      setMessages(history);
    } catch (err) {
      console.error("Failed to fetch history", err);
    }

    const ws = new WebSocket(buildWsUrl(room, user));
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
  }, [addMessage, canConnect, room, status, user]);

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
            <input
              value={user}
              onChange={(e) => setUser(e.target.value)}
              placeholder="your name"
            />
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

