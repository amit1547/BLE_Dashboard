from flask import Flask, render_template, request, jsonify
import pandas as pd, json, os
import mqtt_handler

app = Flask(__name__)
devices = []

mqtt_client = mqtt_handler.mqtt_client
statuses = mqtt_handler.statuses
responses = mqtt_handler.responses
MQTT_CONFIG = mqtt_handler.MQTT_CONFIG

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
            except Exception as e:
                print("[Upload] Button parse error:", e)
                buttons.append({"name": f"{b} (Invalid)", "topic": "", "payload": ""})
        devices.append({"MAC": mac, "SerialNo": serial, "buttons": buttons})
        mqtt_client.subscribe(f"{mac}/status")
        mqtt_client.subscribe(f"{mac}/action/response")
    return jsonify({"status": "ok"})

@app.route("/action", methods=["POST"])
def action():
    global mqtt_client

    mac = request.json["mac"]
    action = request.json["action"]
    topic = f"{mac}/action"
    payload = json.dumps({"action": action})

    print(f"[MQTT] Publishing to {topic}: {payload}")
    result = mqtt_client.publish(topic, payload, qos=0, retain=False)
    print(f"[MQTT] Publish result code: {result.rc}")

    if result.rc != 0:
        print("[MQTT] Publish failed, reconnecting...")
        mqtt_client = mqtt_handler.reconnect(mqtt_client)

    return jsonify({"status": "sent", "topic": topic, "payload": payload, "result": result.rc})

@app.route("/mqtt", methods=["POST"])
def update_mqtt():
    global mqtt_client

    MQTT_CONFIG["host"] = request.form["host"]
    MQTT_CONFIG["port"] = int(request.form["port"])
    MQTT_CONFIG["username"] = request.form["username"]
    MQTT_CONFIG["password"] = request.form["password"]
    mqtt_client = mqtt_handler.reconnect(mqtt_client)
    return jsonify({"status": "updated"})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)