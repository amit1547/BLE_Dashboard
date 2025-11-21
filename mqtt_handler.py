import os, json
import paho.mqtt.client as mqtt

statuses = {}
responses = {}

MQTT_CONFIG = {
    "host": os.getenv("MQTT_HOST", "broker.hivemq.com"),
    "port": int(os.getenv("MQTT_PORT", 1883)),
    "username": os.getenv("MQTT_USER"),
    "password": os.getenv("MQTT_PASS")
}

def on_connect(client, userdata, flags, rc, properties=None):
    print(f"[MQTT] Connected with result code {rc}")

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
    client = mqtt.Client(client_id="ble_dashboard", protocol=mqtt.MQTTv311, clean_session=True)
    if MQTT_CONFIG["username"] and MQTT_CONFIG["password"]:
        client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    client.on_connect = on_connect
    client.on_message = on_message
    try:
        client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"], keepalive=60)
        client.loop_start()
        print(f"[MQTT] Connected to {MQTT_CONFIG['host']}:{MQTT_CONFIG['port']}")
    except Exception as e:
        print("[MQTT] Connection failed:", e)
    return client

def reconnect(client):
    try:
        client.loop_stop()
        client.disconnect()
        client = create_client()
        print("[MQTT] Reconnected")
        return client
    except Exception as e:
        print("[MQTT] Reconnect failed:", e)
        return client

mqtt_client = create_client()