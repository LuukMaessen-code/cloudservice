from faststream.nats import NatsBroker
import os

NATS_URL = os.getenv("NATS_URL", "nats://nats:4222")
broker = NatsBroker(NATS_URL)
