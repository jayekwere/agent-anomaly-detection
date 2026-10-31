"""Privacy bounded audit-event normalization and session correlation."""

import re
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Event:
    tenant: str
    actor: str
    session: str
    event_id: str
    at: datetime
    tool: str
    outcome: str


def normalize(raw: dict) -> Event:
    """Accept only version 1 fixtures; discard payloads before correlation."""
    if (
        not isinstance(raw, dict)
        or type(raw.get("schema_version")) is not int
        or raw.get("schema_version") != 1
    ):
        raise ValueError("unsupported schema version")
    fields = ("tenant", "actor", "session", "event_id", "tool", "outcome")
    for field in fields:
        value = raw.get(field)
        if not isinstance(value, str) or not re.fullmatch(r"[a-zA-Z0-9_.:-]{1,128}", value):
            raise ValueError(f"invalid {field}")
    if raw["outcome"] not in {"allowed", "denied", "pending", "approved", "error"}:
        raise ValueError("invalid outcome")
    try:
        at = datetime.fromisoformat(raw["at"].replace("Z", "+00:00"))
        if at.tzinfo is None:
            raise ValueError("timezone required")
    except (KeyError, TypeError, AttributeError, ValueError) as exc:
        raise ValueError("invalid timestamp") from exc
    return Event(*(raw[k] for k in fields[:4]), at, raw["tool"], raw["outcome"])


def correlate(
    events: list[dict], max_events: int = 100000, max_session: int = 10000
) -> dict[tuple[str, str, str], list[Event]]:
    """Bound memory; reject duplicate identities and isolate tenant/actor sessions."""
    groups, seen = {}, set()
    for index, raw in enumerate(events):
        if index >= max_events:
            raise ValueError("event limit exceeded")
        event = normalize(raw)
        identity = (event.tenant, event.event_id)
        if identity in seen:
            raise ValueError("duplicate event")
        seen.add(identity)
        key = (event.tenant, event.actor, event.session)
        group = groups.setdefault(key, [])
        if len(group) >= max_session:
            raise ValueError("session limit exceeded")
        group.append(event)
    return {key: sorted(group, key=lambda e: (e.at, e.event_id)) for key, group in groups.items()}
