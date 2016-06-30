#!/bin/python3
import time
import RPi.GPIO as GPIO

import nfc
from lcd import LcdDisplay

# Input pins
cancel_button = 37
enter_button = 35
pluss_button = 33
minus_button = 31
# The i2c bus id
bus_id = 1
# Host address of the LCD display
bar_lcd = LcdDisplay(0x28, bus_id) # Large display
customer_lcd = LcdDisplay(0x27,bus_id) # Small display
# Internsystem authentication stuff
# TODO: Make it use a config
username = "tmp"
password = "tmp"


class Customer:
    def __init__(self, name, vouchers, coffee):
        self.name = name
        self.vouchers = vouchers
        self.coffee = coffee


def setup():
    # Get the LCD screen ready
    for lcd in bar_lcd, customer_lcd:
        lcd.clean()
        lcd.tick_off()
        lcd.write("Laster systemet...")

    # Get the bong amount inputs ready
    GPIO.setmode(GPIO.BOARD)
    for pin in cancel_button, enter_button, pluss_button, minus_button:
        GPIO.setup(pin, GPIO.IN)

    # Initialize the NFC reader
    nfc.open()


def get_card_id():
    bar_lcd.clean()
    bar_lcd.write("Venter pa kort")
    customer_lcd.clean()
    customer_lcd.write("Venter pa kort")

    return nfc.getid()


def get_customer(card_id):
    # TODO: Interact with internsystem
    return Customer("Nicolas", 10, 2)


def display_info(customer):
    customer_output = "Du har %2d bonger" % customer.vouchers
    if customer.coffee != 0:
        customer_output += " og %2d kaffer" % customer.coffee

    customer_lcd.clean()
    customer_lcd.write(customer_output)

    bar_lcd.clean()
    bar_lcd.write("Navn: %s" % customer.name)
    bar_lcd.set_pointer(0, 1)
    bar_lcd.write("Bonger: %s" % customer.vouchers)
    bar_lcd.set_pointer(0, 2)
    bar_lcd.write("Kaffe: %s" % customer.coffee)


def get_amount():
    amount = 0

    while not GPIO.input(enter_button):
        bar_lcd.set_pointer(0, 3)
        bar_lcd.write("Antall bonger: %2d" % amount)
        
        if GPIO.input(cancel_button):
            return 0
        elif GPIO.input(pluss_button):
            amount += 1
        elif GPIO.input(minus_button) and amount > 0:
            amount -= 1
        
        # FIXME: Buttons sometimes register double, or not at all.
        # Sleep to not register buttons multiple times
        time.sleep(0.1)

    return amount


def register_use(customer, amount):
    # TODO: Registrer bonger
    customer_lcd.clean()
    customer_lcd.write("%2d bonger har blitt trukket" % amount)


def countdown(seconds):
    for i in reversed(range(1, seconds+1)):
        customer_lcd.set_pointer(14, 1)
        customer_lcd.write("%2d" % i)
        bar_lcd.set_pointer(18, 0)
        bar_lcd.write("%2d" % i)
        time.sleep(1)

if __name__ == "__main__":
    setup()

    while True:
        # Get customer info
        customer = get_customer(get_card_id())
        if customer is None:
            continue
        display_info(customer)

        amount = get_amount()
        if amount is 0:
            continue

        register_use(customer, amount)

        # Give people some time to read
        countdown(5)
