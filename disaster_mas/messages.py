"""Typed message envelope used by all agents."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from itertools import count
from typing import Any


_IDS = count(1)


def _next_message_id() -> str:
    return f"msg-{next(_IDS):04d}"


@dataclass(frozen=True)
class Message:
    """Common envelope for agent-to-agent communication."""

    sender: str
    recipient: str
    type: str
    payload: dict[str, Any]
    trace_id: str
    priority: int = 3
    ttl: int = 8
    requires_ack: bool = False
    msg_id: str = field(default_factory=_next_message_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def route_key(self) -> tuple[str, str]:
        return self.recipient, self.type

    def compact(self) -> str:
        return (
            f"{self.msg_id} {self.sender}->{self.recipient} "
            f"{self.type} p{self.priority} trace={self.trace_id}"
        )


class MessageBus:
    """Simple in-memory bus with audit hooks and type validation."""

    allowed_types = {
        "task.created",
        "hazard.update",
        "task.announce",
        "bid.submit",
        "route.propose",
        "route.veto",
        "decision.award",
        "decision.blocked",
        "escalation.request",
        "approval.grant",
        "approval.deny",
    }

    def __init__(self) -> None:
        self.messages: list[Message] = []

    def publish(self, message: Message) -> None:
        if message.type not in self.allowed_types:
            raise ValueError(f"Unsupported message type: {message.type}")
        if not 1 <= message.priority <= 5:
            raise ValueError("priority must be between 1 and 5")
        if message.ttl < 1:
            raise ValueError("ttl must be positive")
        self.messages.append(message)

    def to(self, recipient: str, *types: str) -> list[Message]:
        selected = [m for m in self.messages if m.recipient == recipient]
        if types:
            selected = [m for m in selected if m.type in types]
        return selected

    def by_trace(self, trace_id: str) -> list[Message]:
        return [m for m in self.messages if m.trace_id == trace_id]
