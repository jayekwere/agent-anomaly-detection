"""Bounded JSONL and explicitly versioned Sentinel export adapter."""

import json

from . import normalize


def read_jsonl(path: str, max_bytes: int = 32_000_000) -> list[dict]:
    with open(path, "rb") as stream:
        data = stream.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise ValueError("input byte limit exceeded")
    try:
        rows = [json.loads(line) for line in data.splitlines() if line.strip()]
        for row in rows:
            normalize(row)
    except (ValueError, TypeError, AttributeError) as exc:
        raise ValueError("invalid audit input") from exc
    return rows


def sentinel_v1(wrapper: dict, session: str) -> dict:
    """Caller supplies correlation; source exports have no session identifier.

    No hash authenticity claim is made. Ingestion never verifies a gateway chain.
    """
    if not isinstance(wrapper, dict) or wrapper.get("provider") != "sentinel":
        raise ValueError("unsupported provider")
    r = wrapper.get("record")
    if not isinstance(r, dict) or type(r.get("seq")) is not int or r["seq"] <= 0:
        raise ValueError("invalid source sequence")
    detail = r.get("detail")
    if not isinstance(detail, dict):
        raise ValueError("invalid detail")
    tool = detail.get("tool", r.get("action"))
    projected = dict(
        schema_version=1,
        tenant=r.get("tenant"),
        actor=r.get("actor"),
        session=session,
        event_id=str(r["seq"]),
        at=r.get("at"),
        tool=tool,
        outcome=r.get("outcome"),
    )
    normalize(projected)
    return projected
