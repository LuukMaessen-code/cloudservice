from fastapi import FastAPI
from faststream.nats import NatsMessage
from .natsapp import broker
import logfire
import json
from contextlib import asynccontextmanager
import os
from typing import Any, Dict

# List of sensitive keys to scrub from logs
def scrub_sensitive_data(data: Any) -> Any:
    SENSITIVE_KEYS = {"password", "token", "secret", "api_key", "access_token", "refresh_token"}
    if isinstance(data, dict):
        return {k: ("***" if k.lower() in SENSITIVE_KEYS else scrub_sensitive_data(v)) for k, v in data.items()}
    elif isinstance(data, list):
        return [scrub_sensitive_data(item) for item in data]
    return data

# ───────────────────────────────
# GLOBAL NATS MESSAGE LOGGING
# ───────────────────────────────
@broker.subscriber(">")
async def on_any_message(msg: NatsMessage):
    """Capture and log ANY message published on the NATS bus, with scrubbing and correct log level."""
    subject = getattr(msg, "subject", None) or getattr(
        msg.raw_message, "subject", "unknown"
    )
    payload = msg.body.decode() if isinstance(msg.body, bytes) else msg.body
    headers = dict(msg.headers or {})

    # Parse and scrub payload
    try:
        payload_as_dict = json.loads(payload)
    except Exception:
        payload_as_dict = {"raw": payload}
    scrubbed_payload = scrub_sensitive_data(payload_as_dict)

    # Determine log level
    log_type = payload_as_dict.get("type", "info").lower()
    if log_type in ("error", "exception", "fail", "critical"):  # error types
        log_level = "error"
    elif log_type in ("warn", "warning"):  # warning types
        log_level = "warning"
    else:
        log_level = "info"

    logfire.log(
        log_level,
        tags=[log_type],
        msg_template=f"[Logging] Received message on {subject}",
        attributes={"payload": scrubbed_payload, "headers": headers},
    )

    # Trace
    trace_id = headers.get("trace-id")
    if trace_id:
        logfire.trace(
            trace_id,
            stage="received",
            metadata={"subject": subject},
        )

# ───────────────────────────────
# LIFESPAN HANDLER FOR STARTUP / SHUTDOWN
# ───────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    print("────────────────────────────────────────────")
    print("[Logging] ✅ Logging service starting...")
    print("────────────────────────────────────────────")

    LOGFIRE_TOKEN = os.getenv("LOGFIRE_TOKEN")
    logfire.configure(
        token=LOGFIRE_TOKEN,
        service_name="Cloudservice Logging Service",
        environment="Full Nats Message Bus",
    )
    logfire.instrument_system_metrics()
    logfire.info("Logging service starting")

    try:
        await broker.start()
        print("[Logging] Connected to NATS successfully")
    except Exception as e:
        print(f"[Logging] Failed to connect to NATS: {e}")

    yield

    print("[Logging] Shutting down...")
    await broker.stop()

# ───────────────────────────────
# CREATE FASTAPI APP WITH LIFESPAN
# ───────────────────────────────
app = FastAPI(title="Cloudservice Logging Service", lifespan=lifespan)
