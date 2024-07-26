import json
import requests
import streamlit as st
from pymongo import MongoClient
import pandas as pd
from urllib.parse import quote_plus
import paho.mqtt.client as mqtt
import logging
from flask import Flask, request, jsonify
from datetime import datetime
import threading
from bson.objectid import ObjectId

# Fungsi mengatur latar belakang
def set_bg(url: str):
    '''
    URL: Link atau alamat website untuk gambar latar belakang
    '''
    st.markdown(
         f"""
         <style>
         .stApp {{
             background: url({url});
             background-size: cover;
             background-repeat: no-repeat;
         }}
         </style>
         """,
         unsafe_allow_html=True
     )
    return

set_bg("https://images.unsplash.com/photo-1534274988757-a28bf1a57c17?w=500&auto=format&fit=crop&q=60&ixlib=rb-4.0.3&ixid=M3wxMjA3fDB8MHxzZWFyY2h8N3x8cmFpbnxlbnwwfHwwfHx8MA%3D%3D") # Gambar

# Fungsi rekomendasi
def get_recommendation(temp, weather):
    if weather == "Rain":
        return "Gunakan pakaian tahan air, payung, dan jaket hujan."
    elif weather == "Clouds":
        return "Gunakan pakaian yang nyaman, mungkin perlu jaket ringan."
    elif temp <= 0:
        return "Pakai pakaian yang sangat tebal, seperti jaket tebal dan lapisan pakaian berlapis."
    elif 0 < temp <= 10:
        return "Gunakan jaket atau sweater yang hangat dan mungkin topi serta sarung tangan."
    elif 10 < temp <= 20:
        return "Pakai jaket ringan atau sweater, dan pastikan tetap nyaman."
    elif 20 < temp <= 30:
        return "Kenakan pakaian ringan dan nyaman, seperti kaos dan celana pendek."
    elif 30 < temp:
        return "Gunakan pakaian yang sangat ringan dan tetap terhidrasi. Hindari sinar matahari langsung."
    else:
        return "Tidak ada rekomendasi yang tersedia."

# REQUESTS
r = requests.Session()

# MongoDB connection
mongo_uri = f"mongodb+srv://user:12345@cluster0.2hhxgtt.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0"

client = MongoClient(mongo_uri)
db = client.get_database('team21')
collection = db.get_collection('datasensor')

# Function to fetch data from MongoDB
def fetch_data():
    results = collection.find()
    data = []
    for result in results:
        data.append({
            'peringatan': result.get('peringatan'),
            'jarak': result.get('jarak'),
            'timestamp': result.get('timestamp')
        })
    df = pd.DataFrame.from_records(data)
    return df

# MQTT setup
mqtt_broker = "broker.hivemq.com"
mqtt_port = 1883
mqtt_username = "Gacorr48"
mqtt_password = "8989,Rifzee"
mqtt_topic = "/test/SIC21/SensorUltrasonic"

# Callback for when the client receives a message
def on_message(client, userdata, message):
    msg = json.loads(message.payload.decode())
    st.write("Message received:", msg)

# Set up MQTT client
client = mqtt.Client()
client.username_pw_set(mqtt_username, mqtt_password)
client.on_message = on_message
client.connect(mqtt_broker, mqtt_port, 60)
client.subscribe(mqtt_topic)
client.loop_start()

# Streamlit app layout
st.title("SFLOODS")
tab1, tab2, tab3 = st.tabs(["Laporan Cuaca", "Prediksi Banjir", "Data Sensor"])

st.markdown(
    """
    <style>
    .weather-list {
        font-size: 14px;
    }
    .weather-list-item {
        margin-bottom: 10px;
    }
    .weather-icon {
        margin-right: 10px;
        vertical-align: middle;
    }
    .custom-column {
        border: 2px solid #b0b5bb;
        border-radius: 2%;
        padding: 10px;
        margin: 5px;
        text-align: center; /* Pusatkan teks */
        background-color: rgba(0, 0, 0, 0.8); /* Tambahkan background putih transparan untuk meningkatkan keterbacaan */
    }
    .stApp {
        color: white; /* Ganti warna teks menjadi putih untuk kontras yang lebih baik */
    }
    </style>
    """,
    unsafe_allow_html=True
)

with tab1:
    _con_cuaca = st.container()
    _con_cuaca.header("Laporan Cuaca")

    kota = _con_cuaca.text_input("Masukkan nama kota", value="Pekanbaru", key="cuaca")

    # OpenWeather
    API = "a0cb4aad9823a209a6512bc72ad21633"

    url = f"https://api.openweathermap.org/data/2.5/weather?q={kota.replace(' ', '+')}&appid={API}&units=metric&lang=id"
    t_hour = f"https://api.openweathermap.org/data/2.5/forecast?q={kota.replace(' ', '+')}&cnt=3&appid={API}&units=metric&lang=id"

    # Reqp
    geturl = r.get(url)
    thur = r.get(t_hour)
    statuscode = geturl.status_code

    # Check status code
    if statuscode == 200:
        js = json.loads(geturl.content)
        suhu = float(js["main"]["temp"])
        awan = [js['weather'][0]['main'], js['weather'][0]['description']]
        awan_string = ", ".join(awan)
        kota = str(js["name"]).replace("+", " ")
        
        # Menarik data yang diinginkan
        extracted_data = []
        if 'list' not in js:
            js = json.loads(thur.content)
        for entry in js['list']:
            temp = entry['main']['temp']
            humidity = entry['main']['humidity']
            weather_main = entry['weather'][0]['main']
            weather_description = entry['weather'][0]['description']
            dt_txt = entry['dt_txt']
            rain = entry['rain']['3h'] if 'rain' in entry and '3h' in entry['rain'] else 0  # Jika data hujan tidak ada, set 0
            
            extracted_data.append({
                'temp': temp,
                'humidity': humidity,
                'weather_main': weather_main,
                'weather_description': weather_description,
                'dt_txt': dt_txt,
                'rain': rain
            })
            
        tanda = f"""Suhu: {suhu} C\nJenis awan: {awan_string}"""

        _con_cuaca.text_area("Cuaca di " + kota + " Saat ini", tanda)
        _con_cuaca.text_area(label="Saran", value=f"Rekomendasi berdasarkan cuaca hari ini, {get_recommendation(suhu, awan[0])}")
        _con_cuaca.subheader("Prediksi 3 jam")

        col = _con_cuaca.columns(3, gap="small")
        
        if extracted_data:
            for i, item in enumerate(extracted_data):
                with col[i % 3]:  # Distribute across 3 columns
                    if item['weather_main'] == "Rain":
                        icon = "☔"
                    elif item['weather_main'] == "Clouds":
                        icon = "🌥️"
                    else:
                        icon = "☁️"

                    col[i % 3].markdown(f"""
                        <div class=custom-column>
                        <div class=weather-list>
                        <div class=weather-icon>{icon}</div>
                        <div class=weather-list-item>Waktu: {item['dt_txt']}
                        <br>Suhu: {item['temp']}°C
                        <br>Kelembapan: {item['humidity']}%
                        <br>Cuaca: {item['weather_main']}
                        <br>Deskripsi: {item['weather_description']}
                        <br>Curah Hujan: {item['rain']} mm</div>
                        </div>
                        </div>""", unsafe_allow_html=True)
    else:
        st.warning("Tidak ada data terkait kota")

with tab2:
    _pred_banjir = st.container()
    _pred_banjir.subheader("Prediksi Banjir")
    col_banj = _pred_banjir.columns(3, gap="small")
    expander_banjir = _pred_banjir.expander("Rumus perhitungan")
    
    with expander_banjir:
        st.latex("\\%R = (H\\times 0.4) + (C\\times 0.5) + (W\\times 0.1)")
        st.write("""H: Kelembapan\n\n C: Curah Hujan\n\n W: Kondisi Cuaca (Jika kondisi adalah "Clear", W = 0
                    Jika kondisi adalah "Clouds", W = 0.3
                    Jika kondisi adalah "Rain", W = 1)""")
    try:
        if extracted_data:
            for i, item in enumerate(extracted_data):
                with col_banj[i % 3]:  # Distribute across 3 columns
                    cuaca_w = 0 if item['weather_main'] == "Clear" else 0.3 if item['weather_main'] == "Clouds" else 1
                    percent = (item['humidity'] * 0.4) + (item['rain'] * 0.5) + (cuaca_w * 0.1)
                    if percent > 100:  # Ensure the value doesn't exceed 100%
                        percent = 100
                    col_banj[i % 3].markdown(f"""
                        <div class=custom-column>
                        <div class=weather-list>
                        <div class=weather-list-item>Waktu: {item['dt_txt']}
                        <br>Persentase Risiko Banjir: {percent}%
                        <br>Suhu: {item['temp']}°C
                        <br>Kelembapan: {item['humidity']}%
                        <br>Cuaca: {item['weather_main']}
                        <br>Deskripsi: {item['weather_description']}
                        <br>Curah Hujan: {item['rain']} mm</div>
                        </div>
                        </div>""", unsafe_allow_html=True)
    except:
        st.warning("Tidak ada data terkait prediksi banjir")

with tab3:
    _data_sensor = st.container()
    _data_sensor.subheader("Data Sensor")

    # Fetch and display data from MongoDB
    data = fetch_data()
    if not data.empty:
        _data_sensor.write(data)
    else:
        st.warning("Tidak ada data sensor yang tersedia.")
