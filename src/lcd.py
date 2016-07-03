import time
import smbus
import RPi.GPIO as GPIO

import nfc
from constants import *

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


def write(lcd, text, clean=True, start_position=0):
    if clean:
        lcd.clean()

    text = text.splitlines()
    for i in range(len(text)):
        lcd.set_pointer(0, i+start_position)
        lcd.write(text[i])

def menu(lcd, description, choices):
    active_choice = 0

    lcd.clean()
    while not GPIO.input(ENTER_BUTTON):
        # Write current output to LCD
        output = description
        for i in range(len(choices)):
            output += "\n"
            if active_choice == i:
                output += "*"
            else:
                output += " "
            output += choices[i]
        write(lcd, output, clean=False)

        if GPIO.input(CANCEL_BUTTON):
            return None
        elif GPIO.input(PLUSS_BUTTON) and active_button is not PLUSS_BUTTON:
            active_button = PLUSS_BUTTON
            if active_choice < len(choices):
                active_choice += 1
            else:
                # Wrap to the start
                active_choice = 0
        elif GPIO.input(MINUS_BUTTON) and active_button is not MINUS_BUTTON:
            active_button = MINUS_BUTTON
            if active_choice > 0:
                active_choice -= 1
            else:
                # Wrap to end
                active_choice = len(choices) - 1
        else:
            active_button = None

    # The enter button is usually held for a few more ms, causing later options to get automatically selected.
    while GPIO.input(ENTER_BUTTON):
        pass
    return choices[active_choice]
