"""
Minimal Home Assistant REST API client for history queries.
"""

import json
import os
import urllib.parse
import urllib.request
from datetime import datetime


def _get_config():
    base_url = os.environ["HA_URL"].rstrip("/")
    token = os.environ["HA_TOKEN"]
    return base_url, token


def _request(url: str, token: str):
    req = urllib.request.Request(url, headers={
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
    })
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read())


def get_state(entity_id: str) -> dict:
    """Get current state of an entity."""
    base_url, token = _get_config()
    return _request(f"{base_url}/api/states/{entity_id}", token)


def get_history(
    entity_ids: list[str],
    start: datetime,
    end: datetime | None = None,
    minimal_response: bool = True,
) -> dict[str, list[dict]]:
    """
    Fetch state history for a list of entities.
    Returns dict mapping entity_id -> list of state records.
    """
    base_url, token = _get_config()

    start_str = urllib.parse.quote(start.isoformat())
    params = f"filter_entity_id={','.join(entity_ids)}"
    if minimal_response:
        params += "&minimal_response&no_attributes"
    if end:
        params += f"&end_time={urllib.parse.quote(end.isoformat())}"

    url = f"{base_url}/api/history/period/{start_str}?{params}"
    raw = _request(url, token)

    result = {}
    for entity_history in raw:
        if not entity_history:
            continue
        eid = entity_history[0].get("entity_id", "")
        result[eid] = entity_history

    return result
