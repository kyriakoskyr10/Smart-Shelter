import os
import json
import time
import random
import requests
from datetime import datetime, timezone
import paho.mqtt.client as mqtt
from influxdb_client import InfluxDBClient, Point, WritePrecision
from influxdb_client.client.write_api import SYNCHRONOUS

# --- Config ---
MQTT_HOST = os.getenv("MQTT_HOST", "150.140.186.118")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("ANIMALS_TOPIC", "smart_shelter/animals")
ORION_URL = os.getenv("ORION_URL", "http://orion:1026")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "smart_shelter")
FIWARE_SERVICEPATH = os.getenv("FIWARE_SERVICEPATH", "/")

INFLUX_URL = os.getenv("INFLUX_URL", "http://influxdb:8086")
INFLUX_TOKEN = os.getenv("INFLUX_TOKEN", "super-secret-token")
INFLUX_ORG = os.getenv("INFLUX_ORG", "smart_shelter")
INFLUX_BUCKET = os.getenv("INFLUX_BUCKET", "vitals")

PERIOD = int(os.getenv("PERIOD_SEC", "5"))

client_influx = InfluxDBClient(url=INFLUX_URL, token=INFLUX_TOKEN, org=INFLUX_ORG)
write_api = client_influx.write_api(write_options=SYNCHRONOUS)

def headers():
    return {
        "Fiware-Service": FIWARE_SERVICE,
        "Fiware-ServicePath": FIWARE_SERVICEPATH,
    }

def clamp(x, lo, hi):
    return max(lo, min(hi, x))

def get_active_animals():
    try:
        url = f"{ORION_URL}/v2/entities?type=Animal&attrs=id&limit=1000"
        r = requests.get(url, headers=headers(), timeout=3)
        if r.status_code == 200:
            data = r.json()
            return [e["id"] for e in data if "id" in e]
    except Exception:
        pass
    return []

def gen_animal(animal_id: str):
    activity = clamp(int(random.gauss(35, 20)), 0, 100)
    hr_base = 80 + (activity * 0.7)
    hr = clamp(int(random.gauss(hr_base, 8)), 55, 180)
    bt = clamp(round(random.gauss(38.7, 0.35), 2), 37.5, 40.2)
    sound = clamp(int(random.gauss(45, 12)), 30, 90)
    if random.random() < 0.06:
        sound = clamp(sound + random.randint(15, 35), 30, 110)

    return {
        "animalId": animal_id,
        "heartRate": float(hr),
        "activityLevel": float(activity),
        "bodyTemp": float(bt),
        "soundLevel": float(sound),
        "ts": time.time()
    }

def write_animal_to_influx(payload):
    try:
        aid = payload["animalId"]
        p = Point("animal_vitals") \
            .tag("animalId", aid) \
            .tag("roomId", "Room:1") \
            .field("heartRate", payload["heartRate"]) \
            .field("activityLevel", payload["activityLevel"]) \
            .field("bodyTemp", payload["bodyTemp"]) \
            .field("soundLevel", payload["soundLevel"]) \
            .time(datetime.now(timezone.utc), WritePrecision.NS)
        write_api.write(bucket=INFLUX_BUCKET, record=p)
    except Exception:
        pass

def update_orion_direct(payload):
    try:
        aid = payload["animalId"]
        attrs = {
            "heartRate": {"type": "Number", "value": payload["heartRate"]},
            "activityLevel": {"type": "Number", "value": payload["activityLevel"]},
            "bodyTemp": {"type": "Number", "value": payload["bodyTemp"]},
            "soundLevel": {"type": "Number", "value": payload["soundLevel"]}
        }
        requests.patch(f"{ORION_URL}/v2/entities/{aid}/attrs", json=attrs, headers=headers(), timeout=2)
    except Exception:
        pass

def main():
    mqtt_client = mqtt.Client()
    try:
        mqtt_client.connect(MQTT_HOST, MQTT_PORT, 60)
        mqtt_client.loop_start()
    except Exception:
        pass

    print("[Simulator] Live Animal Simulation started.", flush=True)

    while True:
        active_ids = get_active_animals()

        for aid in active_ids:
            payload = gen_animal(aid)
            update_orion_direct(payload)
            write_animal_to_influx(payload)
            try:
                mqtt_client.publish(TOPIC, json.dumps(payload), qos=0, retain=False)
            except Exception:
                pass
            
        time.sleep(PERIOD)

if __name__ == "__main__":
    main()