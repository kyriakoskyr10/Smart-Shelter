import os
import json
import requests
import paho.mqtt.client as mqtt

# --- Config ---
ORION = os.getenv("ORION_URL", "http://orion:1026")
FIWARE_SERVICE = os.getenv("FIWARE_SERVICE", "smart_shelter")
FIWARE_SERVICEPATH = os.getenv("FIWARE_SERVICEPATH", "/")
MQTT_HOST = os.getenv("MQTT_HOST", "150.140.186.118")
MQTT_PORT = int(os.getenv("MQTT_PORT", "1883"))
TOPIC = os.getenv("ANIMALS_TOPIC", "smart_shelter/animals")

session = requests.Session()
session.headers.update({
    "Content-Type": "application/json",
    "Fiware-Service": FIWARE_SERVICE,
    "Fiware-ServicePath": FIWARE_SERVICEPATH,
})

def on_message(client, userdata, msg):
    try:
        p = json.loads(msg.payload.decode("utf-8"))
        aid = p.get("animalId")
        if not aid: return

        # --- SAFE UPDATE ---
        # 1. We ONLY send sensor data.
        # 2. We NEVER send 'name' or 'animalType'.
        attrs = {
            "heartRate": {"type": "Number", "value": p.get("heartRate", 0)},
            "activityLevel": {"type": "Number", "value": p.get("activityLevel", 0)},
            "bodyTemp": {"type": "Number", "value": p.get("bodyTemp", 0)},
            "soundLevel": {"type": "Number", "value": p.get("soundLevel", 0)},
        }
        
        # 3. Send PATCH to Orion
        url = f"{ORION}/v2/entities/{aid}/attrs"
        r = session.patch(url, json=attrs)
        
        if r.status_code == 204:
            print(f"[Bridge] Updated {aid} sensors OK.")
        elif r.status_code == 404:
            print(f"[Bridge] Ignored unknown animal {aid} (Dashboard must create it first).")
        else:
            print(f"[Bridge] Error {r.status_code}: {r.text}")

    except Exception as e:
        print(f"[Bridge] Error: {e}")

def main():
    c = mqtt.Client()
    c.on_message = on_message
    c.connect(MQTT_HOST, MQTT_PORT, 60)
    c.subscribe(TOPIC, 0)
    print("[Bridge] Connected. SAFE MODE active.")
    c.loop_forever()

if __name__ == "__main__":
    main()