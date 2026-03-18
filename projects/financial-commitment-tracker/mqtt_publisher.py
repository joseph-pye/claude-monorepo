"""MQTT publisher for Home Assistant integration via auto-discovery."""

import json
import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)

MQTT_HOST = os.getenv("MQTT_HOST", "")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME", "")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD", "")

_STATE_TOPIC = "commitment_tracker/telegram/state"
_ATTR_TOPIC = "commitment_tracker/telegram/attributes"
_DISCOVERY_TOPIC = "homeassistant/binary_sensor/commitment_tracker_telegram/config"


def _publish(messages: list[dict]):
    """Publish a batch of MQTT messages. No-ops silently if MQTT_HOST is unset."""
    if not MQTT_HOST:
        return
    try:
        import paho.mqtt.client as mqtt  # needed for MQTTv311 constant
        import paho.mqtt.publish as publish

        auth = {"username": MQTT_USERNAME, "password": MQTT_PASSWORD} if MQTT_USERNAME else None
        publish.multiple(
            messages,
            hostname=MQTT_HOST,
            port=MQTT_PORT,
            auth=auth,
            protocol=mqtt.MQTTv311,
        )
    except Exception as e:
        logger.error("MQTT publish failed: %s", e)


def publish_discovery():
    """Publish HA MQTT auto-discovery config. Call once on app startup.

    This registers a binary_sensor in HA that appears automatically under the
    'Commitment Tracker' device. No manual HA config required beyond MQTT setup.

    expire_after=7200 means HA marks the sensor unavailable if no heartbeat
    is received within 2 hours — catching crashes automatically.
    """
    config = {
        "name": "Commitment Tracker Bot",
        "unique_id": "commitment_tracker_telegram_bot",
        "state_topic": _STATE_TOPIC,
        "json_attributes_topic": _ATTR_TOPIC,
        "payload_on": "ON",
        "expire_after": 7200,
        "device_class": "connectivity",
        "device": {
            "identifiers": ["commitment_tracker"],
            "name": "Commitment Tracker",
        },
    }
    _publish([
        {"topic": _DISCOVERY_TOPIC, "payload": json.dumps(config), "retain": True, "qos": 1},
    ])
    logger.info("Published MQTT discovery config for HA")


def publish_status():
    """Publish a heartbeat after the scheduler runs.

    Publishes ON to the state topic and a timestamp to the attributes topic.
    HA's expire_after will flip the sensor to unavailable if this stops arriving.
    """
    attrs = {"last_check": datetime.now().isoformat(timespec="seconds")}
    _publish([
        {"topic": _STATE_TOPIC, "payload": "ON", "retain": True, "qos": 1},
        {"topic": _ATTR_TOPIC, "payload": json.dumps(attrs), "retain": True, "qos": 1},
    ])
    logger.debug("Published MQTT heartbeat")
