import os
import json
from datetime import datetime, timezone
import requests
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Config ---
ORION = os.getenv("ORION_URL", "http://orion:1026")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "smart_shelter")
FIWARE_SERVICEPATH = "/"
MQTT_HOST = os.getenv("MQTT_HOST", "150.140.186.118")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
ROOM_ID = os.getenv("ROOM_ID", "Room:1")

REAL_ROOM_TOPIC = os.getenv("REAL_ROOM_TOPIC", "json/Room monitoring/mclimate-co2-sensor:1")
AMMONIA_TOPIC = os.getenv("AMMONIA_TOPIC", "smart_shelter/room/ammonia")
CO_TOPIC = os.getenv("CO_TOPIC", "smart_shelter/room/co")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "super-secret-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "smart_shelter")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vitals")

client_influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_influx.write_api(write_options=SYNCHRONOUS)

def headers():
    return {
        "Content-Type": "application/json",
        "Fiware-Service": FIWARE_SERVICE,
        "Fiware-ServicePath": FIWARE_SERVICEPATH,
    }

def ensure_room():
    payload = {
        "id": ROOM_ID,
        "type": "Room",
        "co2": {"type": "Number", "value": 435.0},
        "temperature": {"type": "Number", "value": 23.0},
        "humidity": {"type": "Number", "value": 37.0},
        "ammonia": {"type": "Number", "value": 8.5},
        "co": {"type": "Number", "value": 1.2}
    }
    try:
        requests.post(f"{ORION}/v2/entities", headers=headers(), json=payload, timeout=3)
    except Exception:
        pass

def patch_attrs(attrs):
    url = f"{ORION}/v2/entities/{ROOM_ID}/attrs"
    try:
        r = requests.patch(url, headers=headers(), json=attrs, timeout=3)
        if r.status_code == 404:
            ensure_room()
            requests.patch(url, headers=headers(), json=attrs, timeout=3)
    except Exception:
        pass

def write_to_influx(field_name, value):
    try:
        p = Point("room_env").tag("roomId", ROOM_ID).field(field_name, float(value)).time(datetime.now(timezone.utc), WritePrecision.NS)
        write_api.write(bucket=INFLUX_BUCKET, record=p)
    except Exception as e:
        print(f"[InfluxDB Error] {e}", flush=True)

def seed_startup_points():
    """Seeds baseline points so graphs immediately populate without waiting 15 mins"""
    write_to_influx("temperature", 23.2)
    write_to_influx("humidity", 38.0)
    write_to_influx("co2", 435.0)
    write_to_influx("ammonia", 8.5)
    write_to_influx("co", 1.2)

def on_message(client, userdata, msg):
    try:
        attrs = {}
        payload = json.loads(msg.payload.decode())
        data = payload.get("object", payload)

        if msg.topic == REAL_ROOM_TOPIC:
            co2 = data.get("CO2") or data.get("co2")
            temp = data.get("sensorTemperature") or data.get("temperature") or data.get("temp")
            hum = data.get("relativeHumidity") or data.get("humidity") or data.get("hum")

            if co2 is not None:
                attrs["co2"] = {"type": "Number", "value": float(co2)}
                write_to_influx("co2", co2)
            if temp is not None:
                attrs["temperature"] = {"type": "Number", "value": float(temp)}
                write_to_influx("temperature", temp)
            if hum is not None:
                attrs["humidity"] = {"type": "Number", "value": float(hum)}
                write_to_influx("humidity", hum)

            print(f"[Real Room MQTT] Ingested -> Temp: {temp}, Hum: {hum}, CO2: {co2}", flush=True)

        if attrs:
            patch_attrs(attrs)

    except Exception as e:
        print(f"[Room] Error processing message: {e}", flush=True)

def main():
    ensure_room()
    seed_startup_points()
    c = mqtt.Client()
    c.on_message = on_message
    c.connect(MQTT_HOST, MQTT_PORT, 60)
    c.subscribe([
        (REAL_ROOM_TOPIC, 0),
        (AMMONIA_TOPIC, 0),
        (CO_TOPIC, 0)
    ])
    print(f"[Room Bridge] Running on {MQTT_HOST}:{MQTT_PORT}", flush=True)
    c.loop_forever()

if __name__ == "__main__":
    main()