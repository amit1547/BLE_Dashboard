from flask import Flask, render_template, request, jsonify
import pandas as pd, json, os
import paho.mqtt.client as mqtt

app = Flask(__name__)
devices = []
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
    except:
        pass

mqtt_client = mqtt.Client()
mqtt_client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"])
mqtt_client.loop_start()

@app.route("/")
def index():
    return render_template("index.html", devices=devices, statuses=statuses, responses=responses, mqtt=MQTT_CONFIG)

@app.route("/upload", methods=["POST"])
def upload():
    file = request.files["excel"]
    df = pd.read_excel(file)
    devices.clear()
    for _, row in df.iterrows():
        mac = row["MAC"]
        serial = row["SerialNo"]
        buttons = []
        for b in ["B1_Settings", "B2_Settings", "B3_Settings"]:
            try:
                config = json.loads(row[b])
                topic = config["publish Topic"].replace("{mac}", mac)
                payload = config["payload"].replace("{mac}", mac)
                buttons.append({"name": config["name"], "topic": topic, "payload": payload})
            except:
                buttons.append({"name": f"{b} (Invalid)", "topic": "", "payload": ""})
        devices.append({"MAC": mac, "SerialNo": serial, "buttons": buttons})
        mqtt_client.subscribe(f"{mac}/status")
        mqtt_client.subscribe(f"{mac}/action/response")
    return jsonify({"status": "ok"})

@app.route("/action", methods=["POST"])
def action():
    mac = request.json["mac"]
    action = request.json["action"]
    topic = f"{mac}/action"
    payload = json.dumps({"action": action})
    mqtt_client.publish(topic, payload)
    return jsonify({"status": "sent"})

@app.route("/mqtt", methods=["POST"])
def update_mqtt():
    MQTT_CONFIG["host"] = request.form["host"]
    MQTT_CONFIG["port"] = int(request.form["port"])
    MQTT_CONFIG["username"] = request.form["username"]
    MQTT_CONFIG["password"] = request.form["password"]
    mqtt_client.loop_stop()
    mqtt_client.disconnect()
    mqtt_client.username_pw_set(MQTT_CONFIG["username"], MQTT_CONFIG["password"])
    mqtt_client.connect(MQTT_CONFIG["host"], MQTT_CONFIG["port"])
    mqtt_client.loop_start()
    return jsonify({"status": "updated"})

if __name__ == "__main__":
    app.run(debug=True)