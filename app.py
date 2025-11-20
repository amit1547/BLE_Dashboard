import streamlit as st
import pandas as pd
import json
import uuid
import time
from mqtt_handler import MQTTHandler

st.set_page_config(layout="wide")
st.title("📡 MQTT Dashboard — Excel + Global Status Check")

# Initialize session state
for key in ["devices", "statuses", "mqtt", "response_codes", "uploaded_file"]:
    if key not in st.session_state:
        st.session_state[key] = {} if key in ["devices", "statuses", "response_codes"] else None

# Thread-safe log initialization
if "mqtt_logs" not in st.session_state:
    st.session_state.mqtt_logs = []

# MQTT message handler
def on_message(client, userdata, msg):
    mac = msg.topic.split("/")[0]
    try:
        payload = json.loads(msg.payload.decode())
        try:
            st.session_state.mqtt_logs.append(f"[{msg.topic}] {json.dumps(payload)}")
        except:
            pass

        if msg.topic.endswith("/status"):
            is_alive = payload.get("isAlive")
            st.session_state.statuses[mac] = True if is_alive is True else False if is_alive is False else None
        elif msg.topic.endswith("/action/response"):
            code = payload.get("code")
            message = payload.get("message")
            if code == 200 and message == "success":
                st.session_state.response_codes[mac] = "success"
            else:
                st.session_state.response_codes[mac] = "fail"
    except Exception as e:
        try:
            st.session_state.mqtt_logs.append(f"[{msg.topic}] Failed to decode: {e}")
        except:
            pass

# Sidebar: MQTT Configuration
with st.sidebar:
    st.header("🔐 MQTT Broker Settings")
    host = st.text_input("Broker Host", "test-2-mqtt.syookinsite.com")
    port = st.number_input("Port", 1883)
    use_ssl = st.checkbox("Use SSL/TLS", value=False)
    use_auth = st.checkbox("Use Username/Password", value=True)
    username = st.text_input("Username", "tnt") if use_auth else ""
    password = st.text_input("Password", "syook2018", type="password") if use_auth else ""
    client_id = st.text_input("Client ID", str(uuid.uuid4()))

    ca_cert = st.text_input("CA Cert Path", "") if use_ssl else ""
    client_cert = st.text_input("Client Cert Path", "") if use_ssl else ""
    client_key = st.text_input("Client Key Path", "") if use_ssl else ""

    connect_btn = st.button("Connect")

if connect_btn:
    config = {
        "host": host,
        "port": port,
        "client_id": client_id,
        "use_ssl": use_ssl,
        "use_auth": use_auth,
        "username": username,
        "password": password,
        "ca_cert": ca_cert,
        "client_cert": client_cert,
        "client_key": client_key,
    }
    st.session_state.mqtt = MQTTHandler(config, on_message)
    st.success(f"Connected to MQTT broker on port {port} {'with SSL' if use_ssl else 'without SSL'}")

# MQTT Logs
with st.expander("📜 MQTT Logs"):
    for log in reversed(st.session_state.mqtt_logs[-50:]):
        st.text(log)

# Excel Upload
uploaded = st.file_uploader("📤 Upload Excel (SerialNo, MAC, B1_Settings, B2_Settings, B3_Settings)", type=["xlsx"])
if uploaded:
    st.session_state.uploaded_file = uploaded
    st.session_state.devices = []

if st.session_state.uploaded_file and not st.session_state.devices:
    df = pd.read_excel(st.session_state.uploaded_file)
    devices = []
    for _, row in df.iterrows():
        mac = row["MAC"]
        serial = row["SerialNo"]
        buttons = []
        for b in ["B1_Settings", "B2_Settings", "B3_Settings"]:
            try:
                config = json.loads(row[b])
                topic = config["publish Topic"].replace("{mac}", mac)
                payload = config["payload"].replace("{mac}", mac)
                buttons.append({
                    "name": config["name"],
                    "topic": topic,
                    "payload": payload
                })
            except:
                buttons.append({
                    "name": f"{b} (Invalid)",
                    "topic": "",
                    "payload": ""
                })
        devices.append({"SerialNo": serial, "MAC": mac, "buttons": buttons})
        if st.session_state.mqtt:
            st.session_state.mqtt.subscribe(f"{mac}/status")
            st.session_state.mqtt.subscribe(f"{mac}/action/response")
    st.session_state.devices = devices
    st.success("Devices loaded and subscribed!")

# Global Check Status Button
if st.session_state.devices and st.button("🔄 Check Status (All Devices)"):
    for device in st.session_state.devices:
        mac = device["MAC"]
        topic = f"{mac}/action"
        payload = json.dumps({"action": "heartbeat"})
        st.session_state.response_codes[mac] = None
        st.session_state.mqtt.publish(topic, payload)

    st.info("Heartbeat requests sent. Polling for responses for 2 seconds...")
    start_time = time.time()
    while time.time() - start_time < 2:
        time.sleep(0.1)

# Pagination
per_page = st.selectbox("Devices per page", [10, 20, 30, 40, 0], index=0)
page = st.number_input("Page", min_value=1, value=1)

# Dashboard Tiles
if st.session_state.devices:
    devices = st.session_state.devices
    if per_page != 0:
        start = (page - 1) * per_page
        end = start + per_page
        devices = devices[start:end]

    for device in devices:
        mac = device["MAC"]
        serial = device["SerialNo"]
        status = st.session_state.statuses.get(mac)
        response_code = st.session_state.response_codes.get(mac)

        if response_code == "success":
            color = "#00cc66"
        elif response_code == "fail":
            color = "#cc3333"
        elif status is True:
            color = "#00cc66"
        elif status is False:
            color = "#cc3333"
        else:
            color = "#cccc00"

        st.markdown("---")
        tile = st.columns([2, 1, 1, 1])
        tile[0].markdown(
            f"<div style='background-color:{color};padding:10px;border-radius:5px;color:white;font-weight:bold;'>"
            f"{serial} - {mac}</div>", unsafe_allow_html=True
        )

        for i in range(3):
            btn = device["buttons"][i]
            if tile[i+1].button(btn["name"], key=f"{mac}_btn_{i}"):
                if st.session_state.mqtt:
                    st.session_state.mqtt.publish(btn["topic"], btn["payload"])
                    st.toast(f"Published to `{btn['topic']}`")
                else:
                    st.error("MQTT not connected")