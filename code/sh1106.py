import framebuf

class SH1106(framebuf.FrameBuffer):
    def __init__(self, width, height, i2c, res=None, addr=0x3c):
        self.width = width
        self.height = height
        self.i2c = i2c
        self.res = res
        self.addr = addr
        self.pages = self.height // 8
        self.buffer = bytearray(self.pages * self.width)
        super().__init__(self.buffer, self.width, self.height, framebuf.MONO_VLSB)
        self.init_display()

    def write_cmd(self, cmd):
        self.i2c.writeto(self.addr, bytes([0x80, cmd]))

    def show(self):
        for page in range(self.height // 8):
            self.write_cmd(0xB0 + page)
            self.write_cmd(0x02) # Kompenzace posunu pro 1.3" displeje
            self.write_cmd(0x10)
            
            # Odeslání dat
            start = self.width * page
            end = self.width * (page + 1)
            self.i2c.writeto(self.addr, b'\x40' + self.buffer[start:end])

    def init_display(self):
        for cmd in (
            0xAE,       # Display OFF
            0xA1,       # Segment remap
            0xC8,       # COM scan direction
            0x81, 0xFF, # Kontrast MAX
            0xA4, 0xA6, # Normal display
            0xD5, 0x80, # Clock divide ratio
            0x8D, 0x14, # Charge pump
            0xAF):      # Display ON
            self.write_cmd(cmd)

    def poweroff(self):
        self.write_cmd(0xAE)

    def poweron(self):
        self.write_cmd(0xAF)