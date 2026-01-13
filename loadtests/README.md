# Locust load tests for Cloudservice

Overview
- Three Locust user classes are provided in `locustfile.py`:
  - `OneRoomUser`: sends messages in a single room.
  - `SwitchingRoomUser`: sends a message then switches between two (or more) rooms.
  - `MultiRoomUser`: picks a random room from a configured list each message.

Important notes
- These tests use the Gateway WebSocket endpoint at `/gateway/ws/{room}` and require a valid Keycloak JWT for each simulated user.
- Provide tokens either via a single token environment variable `LOCUST_TOKEN` (reused for every simulated user) or a file with one token per line and set `LOCUST_TOKENS_FILE=/path/to/tokens.txt`.
- These tests use the Gateway WebSocket endpoint at `/gateway/ws/{room}`.

Running without Keycloak (quick local testing)
- Set `DISABLE_KEYCLOAK=true` in the environment for the services and Locust. When disabled the Gateway and History services accept an explicit username instead of a JWT.
- For Locust, either set `LOCUST_USERNAME` to a fixed username (each simulated user will append a random suffix), or leave it unset and the loader will generate unique usernames.
- In this mode you do NOT need `LOCUST_TOKEN` or `LOCUST_TOKENS_FILE` — the Locust script will use the query param `?user=` for WebSocket connections and send `X-Username` when requesting account deletion.
- Set `LOCUST_GATEWAY_URL` (default `http://localhost:8000`) to point at the running gateway. The script will convert `http(s)` to `ws(s)` for websocket connections.

Environment variables
- `LOCUST_GATEWAY_URL` — base URL for gateway (default: `http://localhost:8000`).
- `LOCUST_TOKEN` — single JWT to use for all users (optional).
- `LOCUST_TOKENS_FILE` — path to a file with one JWT per line (preferred for many unique users).

- `LOCUST_ROOM` — room name for `OneRoomUser` (default: `loadtest-room-1`).
- `LOCUST_ROOMS` — comma-separated rooms for `SwitchingRoomUser` (default: `loadtest-room-A,loadtest-room-B`).
- `LOCUST_MULTI_ROOMS` — comma-separated rooms for `MultiRoomUser` (default: `room1,room2,room3,room4,room5`).

Run Locust
1. Install dependencies (recommended in a virtualenv):

```bash
python -m pip install -r cloudservice/loadtests/requirements.txt
```

2. Start Locust pointing to the locustfile folder:

```bash
LOCUST_GATEWAY_URL=http://localhost:8000 LOCUST_TOKENS_FILE=./tokens.txt locust -f cloudservice/loadtests/locustfile.py
```

3. Open the Locust UI (default `http://localhost:8089`) and start the desired user class and spawn rate.

Cleanup behavior
- After each simulated user stops, the test will attempt an HTTP `DELETE` to `/account` on the gateway using the same JWT. That endpoint will remove the Keycloak user and instruct the history service to delete the user's messages.

Troubleshooting
- Ensure the provided JWTs are valid and issued by your Keycloak instance the gateway trusts.
- If Keycloak is not available, the websocket connections will be rejected by the gateway unless you run a test-only gateway variant.
