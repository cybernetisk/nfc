import nfc
import smbus
import time

# the i2c bus id
busid = 1

# host address of the LCD-displays
addr_lg = 0x28
addr_sm = 0x27


class LcdDisplay:
    def __init__(self, addr):
        self.addr = addr

    def raw(self, data):
        for c in data:
            bus.write_byte(self.addr, ord(c))

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


def countDown(x):
    lcd_sm.set_pointer(14, 1)
    lcd_sm.write("%2d" % x)


if __name__ == "__main__":
    bus = smbus.SMBus(1)

    # stor LCD-skjerm
    lcd_lg = LcdDisplay(addr_lg)

    # liten LCD-skjerm
    lcd_sm = LcdDisplay(addr_sm)

    #lcd_lg.set_size(20, 4)
    #lcd_sm.set_size(16, 2)

    for lcd in lcd_lg, lcd_sm:
        lcd.clean()
        lcd.tick_off()
        lcd.write("Laster systemet ..")

    nfc.open()

    while True:
        lcd_lg.clean()
        lcd_lg.write("Vente, vente, vente ...")
        lcd_sm.clean()
        lcd_sm.write("Venter pa kort..")

        id = nfc.getid()

        lcd_sm.clean()
        lcd_sm.set_pointer(0, 0)
        lcd_sm.write("Fant ID:")
        lcd_sm.set_pointer(0, 1)
        lcd_sm.write(id)

        lcd_lg.clean()

        # testkort
        if id == "fe633b01":
            lcd_lg.write("Hei Henrik!")
            lcd_lg.set_pointer(0, 1)
            lcd_lg.write("Du har:")
            lcd_lg.set_pointer(0, 2)
            lcd_lg.write("        Bonger: %2d" % 5)
            lcd_lg.set_pointer(0, 3)
            lcd_lg.write("         Kaffe: %2d" % 2)
        else:
            lcd_lg.write("Vet ikke hvem dette er :(")

        i = 5
        while i > 0:
            countDown(i)
            i -= 1
            if i >= 0:
                time.sleep(1)

    nfc.close()
