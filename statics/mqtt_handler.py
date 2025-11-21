import os, json
import paho.mqtt.client as mqtt

# Global state
statuses = {}
responses = {}

MQTT_CONFIG = {
    "host": os.getenv("MQTT_HOST", "test-2-mqtt.syookinsite.com"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "username": os.getenv("MQTT_USER", "tnt"),
    "password": os.getenv("MQTT_PASS", "syook2018")
}

def on_message(client, userdata, msg):
    mac = msg.topic.split("/")[0]
    try:
        payload = json.loads(msg.payload.decode())
        if msg.topic.endswith("/status"):
            statuses[mac] = payload.get("isAlive")
        elif msg.topic.endswith("/action/response"):
            code = payload.get("code")
            message = payload.get("message")
            responses[mac] = "success" if code == 200 and message == "success" else "fail"
    except Exception as e:
        print("MQTT message error:", e)

def create_client():
    client = mqtt.Client(protocol=mqtt.MQTTv5)
    client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    client.on_message = on_message
    try:
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.loop_start()
        print("MQTT connected to", MQTT_CONFIG["host"], MQTT_CONFIG["port"])
    except Exception as e:
        print("MQTT connection failed:", e)
    return client

def reconnect(client):
    try:
        client.loop_stop()
        client.disconnect()
        client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.loop_start()
        print("MQTT reconnected")
    except Exception as e:
        print("MQTT reconnect failed:", e)

# Initialize client
mqtt_client = create_client()