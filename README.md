# Filament DryBox Monitor

**Autor:** Jindřich Zeman
**Předmět:** ZPI (Základy programování IoT)
**Semestr:** Zima 2025

Monitorovací IoT zařízení pro sledování podmínek při skladování a sušení 3D tiskových filamentů. Systém měří teplotu a vlhkost, vypočítává rosný bod a data zpřístupňuje lokálně na OLED displeji, v síti přes webové rozhraní a vzdáleně v cloudu pomocí protokolu MQTT.

## Hardware

* **Mikrokontrolér:** Raspberry Pi Pico 2 W
* **Senzor:** SHT40 (Teplota a Vlhkost)
* **Displej:** OLED 1.3" řadič SH1106 (rozhraní I2C)
* 3D tištěné šasi

### Zapojení pinů

| Komponenta | Pin na Pico | Funkce |
| :--- | :--- | :--- |
| **OLED Displej** | GP0 | SDA (I2C0) |
| | GP1 | SCL (I2C0) |
| **Senzor SHT40** | GP2 | SDA (I2C1) |
| | GP3 | SCL (I2C1) |

## Funkce softwaru

1. **Lokální monitoring:** Zobrazuje aktuální naměřené hodnoty a IP adresu zařízení na OLED displeji.
2. **Webové rozhraní:** Poskytuje dashboard v tmavém režimu běžící na portu 80, přístupný v lokální síti.
3. **MQTT Klient:** Odesílá data do služby HiveMQ Cloud přes zabezpečené SSL spojení (port 8883).
4. **Výpočet rosného bodu:** Implementace Magnusova vzorce pro určení teploty kondenzace.
5. **Správa paměti:** Integrovaný Garbage Collector pro prevenci chyb při alokaci paměti během SSL komunikace.

## Instalace

1. Nahrajte firmware MicroPython na Raspberry Pi Pico 2 W.
2. Nahrajte následující soubory do kořenového adresáře zařízení:
   * `main.py` (Hlavní aplikační logika a asynchronní smyčka)
   * `simple.py` (Knihovna umqtt.simple pro MQTT komunikaci)
   * `sh1106.py` (Ovladač pro OLED displej)
   * `sht40.py` (Ovladač pro senzor teploty a vlhkosti)
3. Vytvořte konfigurační soubor `secrets.py` (viz sekce Konfigurace).

## Konfigurace

Pro správnou funkčnost Wi-Fi a MQTT připojení je nutné vytvořit soubor `secrets.py`, který obsahuje citlivé údaje. Tento soubor není součástí repozitáře.

Příklad obsahu `secrets.py`:

```python
secrets = {
   'ssid': 'NAZEV_WIFI_SITE',
   'password': 'HESLO_WIFI_SITE',
   'mqtt_broker': 'ADRESA_BROKERU.hivemq.cloud',
   'mqtt_port': 8883,
   'mqtt_user': 'UZIVATELSKE_JMENO',
   'mqtt_pass': 'HESLO_K_MQTT',
}