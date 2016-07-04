import time
import string
import curses
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


class _Menu:
    def __init__(self, lcd, clean=True, position=0):
        self.lcd = lcd
        self.clean = clean
        self.position = position

        if clean:
            self.lcd.clean()
        else:
            # If we're not cleaning, then we'll need a delay to not accidentially clean the screen
            time.sleep(0.05)

    def _clean_up(self):
        pass

    def _lcd_output(self, active_choice):
        return active_choice

    def _pluss_action(self, active_choice):
        return active_choice

    def _minus_action(self, active_choice):
        return active_choice

    def _alternative_action(self, active_choice):
        return active_choice

    def _return_action(self, active_choice):
        return active_choice

    def menu(self):
        active_choice = 0
        active_button = None
        prev_output = None

        while not GPIO.input(ENTER_BUTTON):
            output = self._lcd_output(active_choice)
            if output != prev_output:
                prev_output = output
                write(self.lcd, output, self.clean, self.position)

            if GPIO.input(CANCEL_BUTTON):
                return None
            elif GPIO.input(PLUSS_BUTTON):
                if active_button is PLUSS_BUTTON:
                    continue
                active_button = PLUSS_BUTTON
                active_choice = self._pluss_action(active_choice)
            elif GPIO.input(MINUS_BUTTON):
                if active_button is MINUS_BUTTON:
                    continue
                active_button = MINUS_BUTTON
                active_choice = self._minus_action(active_choice)
            else:
                active_button = None
                active_choice = self._alternative_action(active_choice)

        self._clean_up()
        # The enter button is usually held for a few more ms, causing later options to get automatically selected.
        while GPIO.input(ENTER_BUTTON):
            pass
        return self._return_action(active_choice)


class ChoiceMenu(_Menu):
    def __init__(self, lcd, description, choices, clean=True, position=0):
        super().__init__(lcd, clean, position)
        self.description = description
        self.choices = choices

    def _lcd_output(self, active_choice):
        output = self.description
        for i in range(len(self.choices)):
            output += "\n"
            if active_choice == i:
                output += "*"
            else:
                output += " "
            output += self.choices[i]
        return output

    def _pluss_action(self, active_choice):
        if active_choice < len(self.choices) - 1:
            return active_choice + 1
        else:
            return 0

    def _minus_action(self, active_choice):
        if active_choice > 0:
            return active_choice - 1
        else:
            return len(self.choices) - 1 # Wrap to end

    def _return_action(self, active_choice):
        return self.choices[active_choice]


class AmountMenu(_Menu):
    def _lcd_output(self, amount):
        return "Antall a fjerne: %2d" % amount

    def _pluss_action(self, amount):
        return amount + 1

    def _minus_action(self, amount):
        if amount > 0:
            return amount - 1
        return amount


class KeyboardMenu(_Menu):
    def __init__(self, lcd, prompt, clean=True, position=0):
        super().__init__(lcd, clean, position)
        self.prompt = prompt + "\n> "

        self.screen = curses.initscr()
        self.screen.nodelay(True) # Makes getch() non-blocking
        lcd.tick_on()

    def _lcd_output(self, current_value):
        return self.prompt + str(current_value)

    def _alternative_action(self, current_value):
        char = self.screen.getch()

        if current_value is 0:
            return ""
        elif char == 127: # Backspace
            return current_value[:-1]
        elif char is not curses.ERR and str(chr(char)) in "".join([string.ascii_letters, string.digits, ".-_"]):
            return current_value + str.lower(str(chr(char)))
        else:
            return current_value

    def _clean_up(self):
        self.lcd.tick_off()
        curses.endwin()
