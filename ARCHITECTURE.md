# Cloudservice Demo — Event-Driven Architecture

This document captures the event-driven design of the chat demo (gateway + history + frontend) on NATS JetStream. It also suggests visualizations (C4 and sequence/flow views) you can render in your tool of choice.

## Components
- **Frontend (React)**: Web UI that opens a WebSocket to Gateway and fetches history via REST.
- **Gateway (FastAPI)**: WebSocket bridge. Publishes chat messages to NATS JetStream (`chat.room.<room>`), subscribes to the same subjects to fan-out to clients.
- **History Service (FastAPI)**: JetStream durable consumer that appends messages to JSONL files and serves REST history.
- **NATS JetStream**: Message bus + persistence (stream `CHAT`, subjects `chat.room.*`).

## Event Flow (Text)
1. User connects WebSocket to `Gateway /ws/{room}?user=...`.
2. Gateway subscribes to `chat.room.<room>` (deliver new messages) and streams them to the socket.
3. When user sends text, Gateway wraps as `MessageEnvelope{type="chat.message", payload=ChatMessage}` and publishes to `chat.room.<room>`.
4. JetStream stores the message (stream `CHAT`).
5. History Service durable consumer receives the message, appends to `/data/history/room_<room>.jsonl`.
6. Other clients with live sockets receive the message from Gateway subscription.
7. On page load, Frontend calls `History GET /history/{room}?limit=N` to render recent messages.

## Visuals to Make
- **C4 Context (Level 1)**: Show User → Frontend → Gateway ↔ NATS ↔ History; optional external dependencies (browser, storage path).
- **C4 Container (Level 2)**: Containers: `frontend/web`, `services/gateway`, `services/history_service`, `NATS`; interactions via HTTP/WebSocket and NATS subjects.
- **C4 Component (Level 3)**: Within Gateway (WebSocket handler, NATS client) and History (worker, storage, API). Keep lightweight.
- **Sequence Diagram**: For “send chat message” and “load history on join”.
- **Deployment Diagram**: Docker Compose (nats/gateway/history/frontend) and Kubernetes (deployments + svc).

## Deployment Views (Text)
- **Local / Docker Compose**
  - Services: `nats`, `gateway`, `history`, `frontend`.
  - Ports: 4222 (NATS), 8222 (NATS monitor), 8000 (Gateway), 9000 (History), 5173 (Frontend).
  - Volumes: `./data` → `/data` for history JSONL files.
- **Kubernetes (namespace `cloudservice-demo`)**
  - Deployments: `nats`, `gateway`, `history`, `frontend`.
  - Services: `nats` (4222/8222), `gateway` (8000), `history` (9000), `frontend` (80). Ingress/port-forward as needed.
  - Images: `cloudservice-gateway`, `cloudservice-history`, `cloudservice-frontend` (configurable via Makefile variables).

## Message Contracts (summary)
- **ChatMessage**: `{ room, user, text, timestamp }`
- **MessageEnvelope**: `{ type: "chat.message", payload: ChatMessage }`

## Operational Notes
- JetStream stream `CHAT` with subjects `chat.room.*`; delivery policies set to new for Gateway fan-out and durable consumer (`history-service`) for persistence.
- History files stored at `/data/history/room_<id>.jsonl`; mount a volume to persist.
- Configure endpoints via envs: Gateway `NATS_URL`, `HISTORY_API_URL`; History `NATS_URL`, `STORAGE_PATH`.

This will function as a basis for generating diagrams in tools like Structurizr, PlantUML, or Mermaid (C4 variants). Keep the model synced with actual env var names and subjects.***

