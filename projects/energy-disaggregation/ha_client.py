"""
Minimal Home Assistant REST API client for history queries.
"""

import json
import os
import urllib.request
from datetime import datetime, timedelta


def _get_config():
    base_url = os.environ["HA_URL"].rstrip("/")
    token = os.environ["HA_TOKEN"]
    return base_url, token


def _request(url: str, token: str) -> any:
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

    Returns dict mapping entity_id -> list of state records,
    each with 'state', 'last_changed' keys.
    """
    base_url, token = _get_config()

    start_str = start.isoformat()
    params = f"filter_entity_id={','.join(entity_ids)}"
    if minimal_response:
        params += "&minimal_response&no_attributes"
    if end:
        params += f"&end_time={end.isoformat()}"

    url = f"{base_url}/api/history/period/{start_str}?{params}"
    raw = _request(url, token)

    # HA returns list of lists; each inner list is one entity's history
    result = {}
    for entity_history in raw:
        if not entity_history:
            continue
        eid = entity_history[0].get("entity_id", "")
        result[eid] = entity_history

    return result


def list_entities(domain: str | None = None) -> list[dict]:
    """List all entities, optionally filtered by domain (e.g. 'switch', 'sensor')."""
    base_url, token = _get_config()
    states = _request(f"{base_url}/api/states", token)
    if domain:
        states = [s for s in states if s["entity_id"].startswith(f"{domain}.")]
    return states
