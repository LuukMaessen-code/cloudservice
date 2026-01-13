import os
import random
import json
import time
from uuid import uuid4
from itertools import cycle

import requests
from websocket import create_connection

from locust import User, task, between, events


def _load_tokens():
    tokens_file = os.getenv("LOCUST_TOKENS_FILE")
    single = os.getenv("LOCUST_TOKEN")
    disable = os.getenv("DISABLE_KEYCLOAK", "false").lower() in ("1", "true", "yes")
    if disable:
        # When Keycloak is disabled we don't need tokens; return a cycle of None
        return cycle([None])
    if tokens_file and os.path.exists(tokens_file):
        with open(tokens_file, "r", encoding="utf-8") as fh:
            tokens = [l.strip() for l in fh if l.strip()]
            if tokens:
                return cycle(tokens)
    if single:
        return cycle([single])
    raise RuntimeError("No tokens provided. Set LOCUST_TOKEN or LOCUST_TOKENS_FILE")


TOKENS = _load_tokens()


def _ws_base():
    base = os.getenv("LOCUST_GATEWAY_URL", "http://localhost:8000")
    if base.startswith("http://"):
        return base.replace("http://", "ws://")
    if base.startswith("https://"):
        return base.replace("https://", "wss://")
    return base


class BaseWSUser(User):
    # This base user is not a concrete user class for Locust to run.
    abstract = True
    wait_time = between(0.5, 2)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.token = next(TOKENS)
        # If Keycloak is disabled, use a username instead of token
        self.disable = os.getenv("DISABLE_KEYCLOAK", "false").lower() in ("1", "true", "yes")
        if self.disable:
            self.username = os.getenv("LOCUST_USERNAME") or f"locust-{uuid4().hex[:8]}"
        self.base = os.getenv("LOCUST_GATEWAY_URL", "http://localhost:8000").rstrip("/")
        self.ws_base = _ws_base().rstrip("/")
        self.ws = None

    def connect_ws(self, room: str):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
        if getattr(self, "disable", False):
            url = f"{self.ws_base}/gateway/ws/{room}?user={self.username}"
        else:
            url = f"{self.ws_base}/gateway/ws/{room}?token={self.token}"
        self.ws = create_connection(url, timeout=5)

    def send_message(self, room: str, text: str):
        if not self.ws:
            self.connect_ws(room)
        start = time.time()
        if not self.ws:
            # failed to connect earlier
            try:
                self.environment.events.request_failure.fire(request_type="websocket", name="send_message", response_time=0, response_length=0, exception=RuntimeError("no websocket"))
            except Exception:
                try:
                    self.environment.events.request.fire(request_type="websocket", name="send_message", response_time=0, response_length=0, exception=RuntimeError("no websocket"))
                except Exception:
                    pass
            return
        try:
            self.ws.send(text)
            # non-blocking try to receive any incoming message
            try:
                self.ws.settimeout(1)
                _ = self.ws.recv()
            except Exception:
                pass
            elapsed = int((time.time() - start) * 1000)
            try:
                self.environment.events.request_success.fire(request_type="websocket", name="send_message", response_time=elapsed, response_length=len(text))
            except Exception:
                try:
                    self.environment.events.request.fire(request_type="websocket", name="send_message", response_time=elapsed, response_length=len(text), exception=None)
                except Exception:
                    pass
        except Exception as e:
            elapsed = int((time.time() - start) * 1000)
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None
            try:
                self.environment.events.request_failure.fire(request_type="websocket", name="send_message", response_time=elapsed, response_length=0, exception=e)
            except Exception:
                try:
                    self.environment.events.request.fire(request_type="websocket", name="send_message", response_time=elapsed, response_length=0, exception=e)
                except Exception:
                    pass

    def on_stop(self):
        try:
            if self.ws:
                self.ws.close()
        except Exception:
            pass
        # Always attempt to delete user data/account
        try:
            start = time.time()
            if getattr(self, "disable", False):
                # send username either as header or query param
                headers = {"X-Username": self.username}
                resp = requests.delete(f"{self.base}/account", headers=headers, params={"user": self.username}, timeout=5)
            else:
                headers = {"Authorization": f"Bearer {self.token}"}
                resp = requests.delete(f"{self.base}/account", headers=headers, timeout=5)
            elapsed = int((time.time() - start) * 1000)
            try:
                length = len(resp.content) if resp is not None else 0
            except Exception:
                length = 0
            if resp is not None and 200 <= getattr(resp, "status_code", 0) < 300:
                try:
                    self.environment.events.request_success.fire(request_type="http", name="delete_account", response_time=elapsed, response_length=length)
                except Exception:
                    try:
                        self.environment.events.request.fire(request_type="http", name="delete_account", response_time=elapsed, response_length=length, exception=None)
                    except Exception:
                        pass
            else:
                try:
                    self.environment.events.request_failure.fire(request_type="http", name="delete_account", response_time=elapsed, response_length=length, exception=RuntimeError(f"status={getattr(resp, 'status_code', None)}"))
                except Exception:
                    try:
                        self.environment.events.request.fire(request_type="http", name="delete_account", response_time=elapsed, response_length=length, exception=RuntimeError(f"status={getattr(resp, 'status_code', None)}"))
                    except Exception:
                        pass
        except Exception as e:
            try:
                self.environment.events.request_failure.fire(request_type="http", name="delete_account", response_time=0, response_length=0, exception=e)
            except Exception:
                try:
                    self.environment.events.request.fire(request_type="http", name="delete_account", response_time=0, response_length=0, exception=e)
                except Exception:
                    pass


class OneRoomUser(BaseWSUser):
    """Always sends messages in a single room."""

    def on_start(self):
        self.room = os.getenv("LOCUST_ROOM", "loadtest-room-1")
        self.connect_ws(self.room)

    @task
    def send(self):
        text = f"msg:{uuid4()}"
        self.send_message(self.room, text)


class SwitchingRoomUser(BaseWSUser):
    """Sends a message then switches room for next message."""

    def on_start(self):
        rooms = os.getenv("LOCUST_ROOMS", "loadtest-room-A,loadtest-room-B").split(",")
        self.rooms = [r.strip() for r in rooms if r.strip()]
        self.current = 0
        self.connect_ws(self.rooms[self.current])

    @task
    def send_and_switch(self):
        room = self.rooms[self.current]
        text = f"switch-msg:{uuid4()}"
        self.send_message(room, text)
        # switch
        self.current = (self.current + 1) % len(self.rooms)
        # reconnect to new room on next request
        try:
            self.connect_ws(self.rooms[self.current])
        except Exception:
            self.ws = None


class MultiRoomUser(BaseWSUser):
    """Picks a random room from a larger set for each message."""

    def on_start(self):
        seed = os.getenv("LOCUST_MULTI_ROOMS", "room1,room2,room3,room4,room5")
        self.rooms = [r.strip() for r in seed.split(",") if r.strip()]

    @task
    def send_random(self):
        room = random.choice(self.rooms)
        text = f"multi-msg:{uuid4()}"
        self.send_message(room, text)
