#!/bin/python3
import sys
import time
import configparser
import RPi.GPIO as GPIO

import nfc
from api import CybApi
from lcd import LcdDisplay, write

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
# API for internsystem
api = None


class Customer:
    def __init__(self, username, name, vouchers, coffee_vouchers):
        self.username = username
        self.name = name
        self.vouchers = vouchers
        self.coffee_vouchers = coffee_vouchers


def setup():
    # Get the config
    config = configparser.ConfigParser()
    config.read(sys.argv[1])

    # Get the API ready
    global api
    api_config = config._sections["api"]
    api = CybApi(
            api_config["username"], api_config["password"],
            api_config["client_id"], api_config["client_secret"]
    )

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
    for lcd in bar_lcd, customer_lcd:
        write(lcd, "Venter pa kort")

    return nfc.getid()


def get_customer(card_id):
    username, name = api.get_card_owner(card_id)

    vouchers = 0
    # A NFC card might only be used as a coffee card.
    if username:
        vouchers = api.get_voucher_balance(username)
    coffee_vouchers = api.get_coffee_voucher_balance(card_id)

    return Customer(username, name, vouchers, coffee_vouchers)


def display_info(customer):
    output = []
    if customer.name:
        output += ["Name: %s" % customer.name]
    if customer.vouchers != 0:
        output += ["Bonger: %2d" % customer.vouchers]
    if customer.coffee != 0:
        output += ["Kaffe: %2d" % customer.coffee_vouchers]

    write(bar_lcd, output)
    # We don't want to display the name on the customer screen
    if customer.name:
        output.pop(0)
    write(customer_lcd, output)


def get_amount():
    amount = 0
    active_button = None # To avoid adding/removing multiple bong in one press.

    while not GPIO.input(enter_button):
        write(bar_lcd, "Antall a fjerne: %2d" % amount, start_position=3)
        
        if GPIO.input(cancel_button):
            return 0
        elif GPIO.input(pluss_button) and active_button is not pluss_button:
            amount += 1
            active_button = pluss_button
        elif GPIO.input(minus_button) and active_button is not minus_button and amount > 0:
            amount -= 1
            active_button = minus_button
        else:
            active_button = None
        
    return amount


def register_use(customer, amount):
    for lcd in bar_lcd, customer_lcd:
        write(lcd, "Trekker %2d bonger" % amount)

    if use_vouchers(customer.username, amount):
        for lcd in bar_lcd, customer_lcd:
            write(lcd, "%2d bonger trukket" % amount)
    else:
        write(customer_lcd, "Du har ikke nok bonger")
        write(bar_lcd, "Kunden har ikke nok bonger")


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

        # Display info about the customer
        display_info(customer)

        # Get amount of bongs to remove
        amount = get_amount()
        if amount is 0:
            continue

        # Remove x amount of bongs from customer
        register_use(customer, amount)

        # Give people some time to read
        countdown(5)
