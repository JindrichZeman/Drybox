import network
import uasyncio as asyncio
from machine import Pin, I2C
import time
import math
import sh1106
import sht40
from simple import MQTTClient
from secrets import secrets
import ubinascii
import machine
import gc

# --- 1. KONFIGURACE ---
SSID = secrets['ssid']
PASS = secrets['password']
MQTT_BROKER = secrets['mqtt_broker']
MQTT_PORT   = secrets['mqtt_port']
MQTT_USER   = secrets['mqtt_user']
MQTT_PASS   = secrets['mqtt_pass']

CLIENT_ID = ubinascii.hexlify(machine.unique_id())

# Intervaly
MEASURE_INTERVAL = 3    
MQTT_INTERVAL = 30      

data_store = {"temp": 0.0, "hum": 0.0, "dew": 0.0, "ip": "0.0.0.0"}

# --- 2. VÝPOČTY ---
def calculate_dew_point(T, RH):
    if RH <= 0: return T
    try:
        a = 17.27
        b = 237.7
        alpha = ((a * T) / (b + T)) + math.log(RH / 100.0)
        return (b * alpha) / (a - alpha)
    except: return T

async def connect_wifi():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    wlan.config(pm=0xa11140)
    wlan.connect(SSID, PASS)
    print("[INFO] Pripojuji k WiFi...")
    for _ in range(30):
        if wlan.status() == 3: break
        await asyncio.sleep(1)
    if wlan.status() == 3:
        ip = wlan.ifconfig()[0]
        data_store["ip"] = ip
        print(f"[INFO] WiFi Pripojeno. IP: {ip}")
        return True
    return False

# --- 3. ÚLOHY (TASKS) ---

# A) Webserver
async def handle_web(reader, writer):
    try:
        req = str(await reader.readline())
        while await reader.readline() != b"\r\n": pass

        html = f"""<!DOCTYPE html>
        <html lang="cs">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <meta http-equiv="refresh" content="3">
            <title>DryBox</title>
            <style>
                body {{ background: #121212; color: #e0e0e0; font-family: sans-serif; padding: 20px; text-align: center; }}
                h1 {{ font-weight: 300; margin-bottom: 20px; }}
                .card {{ background: #1e1e1e; border-radius: 12px; padding: 15px; margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center; border: 1px solid #333; }}
                .val {{ font-size: 1.8rem; font-weight: bold; }}
                .temp {{ color: #ff6b6b; }} .hum {{ color: #4ecdc4; }} .dew {{ color: #ffe66d; }}
            </style>
        </head>
        <body>
            <h1>DryBox Monitor</h1>
            <div class="card"><span>Teplota</span><span class="val temp">{data_store['temp']:.1f}°C</span></div>
            <div class="card"><span>Vlhkost</span><span class="val hum">{data_store['hum']:.1f}%</span></div>
            <div class="card"><span>Rosný bod</span><span class="val dew">{data_store['dew']:.1f}°C</span></div>
            <p style="color: #666; margin-top: 30px;">IP: {data_store['ip']}</p>
        </body>
        </html>"""
        
        writer.write("HTTP/1.0 200 OK\r\nContent-type: text/html\r\n\r\n".encode())
        writer.write(html.encode())
        await writer.drain()
        writer.close()
    except: pass

# B) Displej a Senzor (UPRAVENÝ DESIGN)
async def task_sensor_display(display, sensor):
    while True:
        try:
            t, rh = sensor.measure()
            dp = calculate_dew_point(t, rh)
            
            data_store["temp"] = t
            data_store["hum"] = rh
            data_store["dew"] = dp
            
            display.fill(0)
            
            # --- Řádek 1: TEPLOTA ---
            # Posunuto nahoru (y=0), roztaženo
            display.text("Teplota", 0, 0, 1)
            display.text(f"{t:.1f} C", 75, 0, 1)
            
            # --- Řádek 2: VLHKOST ---
            # Větší mezera (y=16)
            display.text("Vlhkost", 0, 16, 1)
            display.text(f"{rh:.1f} %", 75, 16, 1)
            
            # --- Řádek 3: ROSNÝ BOD ---
            # Větší mezera (y=32)
            display.text("Rosny b.", 0, 32, 1)
            display.text(f"{dp:.1f} C", 75, 32, 1)
            
            # --- Řádek 4: ČÁRA a IP ---
            display.hline(0, 48, 128, 1)
            
            # Vycentrování IP adresy
            ip_str = data_store['ip']
            # Výpočet: (Šířka displeje - Šířka textu) děleno 2
            x_pos = (128 - (len(ip_str) * 8)) // 2
            if x_pos < 0: x_pos = 0 # Pojistka
            
            # Zobrazíme JEN čísla IP adresy (bez textu "IP:" a bez Cloudu)
            # Tím se to vejde celé.
            display.text(ip_str, x_pos, 54, 1)
            
            display.show()
        except Exception as e:
            print(f"[ERROR] Senzor: {e}")
        await asyncio.sleep(MEASURE_INTERVAL)

# C) MQTT Cloud
async def task_mqtt_cloud():
    print("[INFO] Cekam na WiFi pro MQTT...")
    await asyncio.sleep(10)
    
    ssl_params = {'server_hostname': MQTT_BROKER}
    
    while True:
        if data_store["ip"] != "0.0.0.0":
            try:
                gc.collect()
                client = MQTTClient(CLIENT_ID, MQTT_BROKER, port=MQTT_PORT, 
                                  user=MQTT_USER, password=MQTT_PASS, 
                                  keepalive=60, ssl=True, ssl_params=ssl_params)
                
                client.set_last_will("drybox/status", "offline", retain=True)
                client.connect()
                client.publish("drybox/status", "online", retain=True)
                
                # Odeslání hodnot
                client.publish("drybox/teplota", "{:.2f}".format(data_store["temp"]))
                client.publish("drybox/vlhkost", "{:.2f}".format(data_store["hum"]))
                client.publish("drybox/rosny_bod", "{:.2f}".format(data_store["dew"]))
                
                print(f"[INFO] MQTT Odeslano.")
                await asyncio.sleep(2)
                client.disconnect()
                client = None
                gc.collect()
                
            except Exception as e:
                print(f"[ERROR] MQTT: {e}")
        
        await asyncio.sleep(MQTT_INTERVAL)

# --- 4. START ---
async def main():
    i2c0 = I2C(0, scl=Pin(1), sda=Pin(0), freq=100000)
    display = sh1106.SH1106(128, 64, i2c0)
    i2c1 = I2C(1, scl=Pin(3), sda=Pin(2), freq=100000)
    sensor = sht40.SHT40(i2c1)

    display.fill(0)
    display.text("START SYSTEMU...", 0, 25, 1)
    display.show()
    
    await connect_wifi()
    
    print("[INFO] Spoustim system...")
    gc.collect()
    
    asyncio.create_task(asyncio.start_server(handle_web, "0.0.0.0", 80))
    asyncio.create_task(task_mqtt_cloud())
    await task_sensor_display(display, sensor)

try:
    asyncio.run(main())
except KeyboardInterrupt:
    print("Ukonceno.")