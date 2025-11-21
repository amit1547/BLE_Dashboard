import os, json
import paho.mqtt.client as mqtt

# Global state dictionaries
statuses = {}
responses = {}

# MQTT configuration from environment variables
MQTT_CONFIG = {
    "host": os.getenv("MQTT_HOST", "broker.hivemq.com"),  # default public broker
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "username": os.getenv("MQTT_USER"),
    "password": os.getenv("MQTT_PASS")
}

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("Connected to MQTT broker with code:", reason_code)

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
    if MQTT_CONFIG["username"] and MQTT_CONFIG["password"]:
        client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    client.on_connect = on_connect
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
        if MQTT_CONFIG["username"] and MQTT_CONFIG["password"]:
            client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.loop_start()
        print("MQTT reconnected")
    except Exception as e:
        print("MQTT reconnect failed:", e)

# Initialize client once
mqtt_client = create_client()