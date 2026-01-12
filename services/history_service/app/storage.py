import json
from collections import deque
from pathlib import Path
from typing import Iterable, List

from packages.common import ChatMessage


class HistoryStorage:
    """Append-only JSONL storage per room."""

    def __init__(self, base_path: Path):
        self.base_path = base_path
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _file_for_room(self, room: str) -> Path:
        safe_room = room.replace("/", "_")
        return self.base_path / f"room_{safe_room}.jsonl"

    def append(self, message: ChatMessage) -> None:
        path = self._file_for_room(message.room)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            f.write(message.model_dump_json())
            f.write("\n")

    def read_latest(self, room: str, limit: int = 50) -> List[ChatMessage]:
        path = self._file_for_room(room)
        if not path.exists():
            return []
        buffer: deque[str] = deque(maxlen=limit)
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                buffer.append(line.rstrip("\n"))
        return list(self._parse_messages(buffer))

    @staticmethod
    def _parse_messages(lines: Iterable[str]) -> Iterable[ChatMessage]:
        for line in lines:
            if not line:
                continue
            try:
                data = json.loads(line)
                yield ChatMessage(**data["payload"]) if "payload" in data else ChatMessage(**data)
            except Exception:
                # Skip malformed lines
                continue

    def remove_messages_by_username(self, username: str) -> int:
        """
        Remove all messages posted by the given username from all rooms.
        Returns the number of messages deleted.
        """
        deleted_count = 0
        for room_file in self.base_path.glob("room_*.jsonl"):
            with room_file.open("r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                try:
                    data = json.loads(line)
                    msg = ChatMessage(**data["payload"]) if "payload" in data else ChatMessage(**data)
                    # Use 'user' field for matching, not 'username'
                    if getattr(msg, "user", None) != username:
                        new_lines.append(line)
                    else:
                        deleted_count += 1
                except Exception:
                    new_lines.append(line)  # keep malformed lines
            with room_file.open("w", encoding="utf-8") as f:
                f.writelines(new_lines)
        return deleted_count

