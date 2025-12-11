import time
from machine import I2C

class SHT40:
    def __init__(self, i2c, addr=0x44):
        self.i2c = i2c
        self.addr = addr

    def measure(self):
        # 1. Příkaz k měření (High precision)
        self.i2c.writeto(self.addr, b'\xFD')
        
        # 2. Čekání na změření (cca 10ms, dáme 20ms pro jistotu)
        time.sleep_ms(20)
        
        # 3. Přečtení 6 bytů (Temp MSB, LSB, CRC, Hum MSB, LSB, CRC)
        data = self.i2c.readfrom(self.addr, 6)
        
        # --- Výpočet teploty ---
        t_ticks = data[0] * 256 + data[1]
        temp = -45 + (175 * t_ticks / 65535)
        
        # --- Výpočet vlhkosti ---
        rh_ticks = data[3] * 256 + data[4]
        rh = -6 + (125 * rh_ticks / 65535)
        
        # Oříznutí na 0-100%
        if rh > 100: rh = 100
        if rh < 0: rh = 0
            
        return temp, rh