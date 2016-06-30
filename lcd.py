import time
import smbus

class LcdDisplay:
    def __init__(self, addr, bus_id):
        self.addr = addr
        self.bus = smbus.SMBus(1)

    def raw(self, data):
        for c in data:
            self.bus.write_byte(self.addr, ord(c))

    def clean(self):
        self.raw("CL")

    def write(self, text):
        self.raw("TT%s\x00" % text)
        time.sleep(0.05)

    def set_pointer(self, x, y):
        self.raw("TP%c%c" % (x, y))

    def set_size(self, x, y):
        self.raw("STCR%c%c\x80\xC0\x94\xd4" % (x, y))

    def tick_off(self):
        self.raw("CS%c" % 0)

    def tick_on(self):
        self.raw("CS%c" % 1)

    def new_i2c_addr(self, new_addr):
        # new_addr e.g. 0x28
        self.raw("SI2CA%c" % new_addr)
