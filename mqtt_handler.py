import os, json
import paho.mqtt.client as mqtt

# Global state
statuses = {}
responses = {}

# MQTT config from environment variables or defaults
MQTT_CONFIG = {
    "host": os.getenv("MQTT_HOST", "broker.hivemq.com"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "username": os.getenv("MQTT_USER"),
    "password": os.getenv("MQTT_PASS")
}

def on_connect(client, userdata, flags, reason_code, properties=None):
    print("[MQTT] Connected with reason code:", reason_code)

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
        print("[MQTT] Message parse error:", e)

def create_client():
    client = mqtt.Client(client_id="ble_dashboard", protocol=mqtt.MQTTv5)
    client.clean_start = False
    if MQTT_CONFIG["username"] and MQTT_CONFIG["password"]:
        client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.reconnect_delay_set(min_delay=1, max_delay=120)
        client.loop_start()
        print("[MQTT] Connected to", MQTT_CONFIG["host"], MQTT_CONFIG["port"])
    except Exception as e:
        print("[MQTT] Initial connection failed:", e)
    return client

def reconnect(client):
    try:
        client.loop_stop()
        client.disconnect()
        if MQTT_CONFIG["username"] and MQTT_CONFIG["password"]:
            client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.loop_start()
        print("[MQTT] Reconnected")
    except Exception as e:
        print("[MQTT] Reconnect failed:", e)

mqtt_client = create_client()