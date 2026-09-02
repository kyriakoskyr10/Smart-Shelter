import paho.mqtt.client as mqtt

def on_message(client, userdata, msg):
    print(f"\n[TOPIC]: {msg.topic}")
    print(f"[DATA] : {msg.payload.decode()}")

client = mqtt.Client()
client.on_message = on_message
client.connect("150.140.186.118", 1883, 60)
client.subscribe("json/Room monitoring/mclimate-co2-sensor:1")

print("Listening for live sensor data on 150.140.186.118...")
client.loop_forever()