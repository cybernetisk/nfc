#!/bin/python3
import sys
import time
import string
import configparser
import curses
import RPi.GPIO as GPIO

import nfc
from constants import *
from api import CybApi
from lcd import LcdDisplay, write, menu

# Host address of the LCD display
bar_lcd = LcdDisplay(0x28, BUS_ID) # Large display
customer_lcd = LcdDisplay(0x27, BUS_ID) # Small display
# API for internsystem
api = None


class Customer:
    def __init__(self, username, is_intern, vouchers, coffee_vouchers):
        self.username = username
        self.intern = is_intern
        self.vouchers = vouchers
        self.coffee_vouchers = coffee_vouchers


def setup():
    # Get the LCD screen ready
    for lcd in bar_lcd, customer_lcd:
        lcd.tick_off()
        lcd.clean()
        lcd.write("Laster systemet!")

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

    # Get the bong amount inputs ready
    GPIO.setmode(GPIO.BOARD)
    for pin in CANCEL_BUTTON, ENTER_BUTTON, PLUSS_BUTTON, MINUS_BUTTON:
        GPIO.setup(pin, GPIO.IN)

    # Initialize the NFC reader
    nfc.open()


def get_card_id():
    for lcd in bar_lcd, customer_lcd:
        time.sleep(0.05) # If there was a loop previously, this prevents the screen from becomming blank
        write(lcd, "Venter pa kort")

    return nfc.getid()


def get_keyboard_input(prompt):
    screen = curses.initscr()
    screen.nodelay(True) # Prevents getch() from blocking
    output = prompt + "\n> "
    value = ""
    prev_value = None

    for lcd in bar_lcd, customer_lcd:
        lcd.clean()
        lcd.tick_on()
    while not GPIO.input(ENTER_BUTTON):
        if value is not prev_value:
            prev_value = value
            for lcd in bar_lcd, customer_lcd:
                write(lcd, output + value)

        char = screen.getch()
        if GPIO.input(CANCEL_BUTTON) or char == 27: # Escape Key
            value = None
            break
        elif char == 10: # Enter Key
            break
        elif char == 127: # Backspace
            value = value[:-1]
        elif char is not curses.ERR and str(chr(char)) in "".join([string.ascii_letters, string.digits, ".-_"]):
            value += str.lower(str(chr(char)))

    # Cleanup
    for lcd in bar_lcd, customer_lcd:
        lcd.tick_off()
    curses.endwin()

    return value


def register_customer(card_uid):
    username = ""
    user_id = ""
    is_intern = False

    choice = menu(
            bar_lcd,
            "Er personen intern?",
            ("Ja", "Nei")
    )
    if choice is "Ja":
        # TODO: Check if username actually exists
        is_intern = True
        user = None
        while True:
            username = get_keyboard_input("Brukernavn")
            if not username:
                return (None, None) # Empty username means cancel

            user = api.get_user(username)
            if "detail" in user: # If there is a detail, it means that we didn't get a match.
                for lcd in bar_lcd, customer_lcd:
                    write(lcd, "Brukeren finnes ikke")
                time.sleep(2) # Give user some time to read
            else:
                user_id = user["id"]
                break
    elif choice is None:
        return (None, None)

    for lcd in bar_lcd, customer_lcd:
        write(lcd, "Registerer kort")
    if api.register_card(card_uid, user_id, is_intern):
        for lcd in bar_lcd, customer_lcd:
            write(lcd, "Kort registrert!")
        time.sleep(2)

    return (username, is_intern)


def get_customer(card_uid):
    username, is_intern = api.get_card_info(card_uid)

    if username is None:
        write(customer_lcd, "Ikke gjenkjent")
        choice = menu(
                bar_lcd,
                "Kort ikke gjenkjent",
                ("Register", "Avbryt")
        )
        if choice is "Kanseler" or None:
            return None

        username, is_intern = register_customer(card_uid)
        if username is None:
            return None

    vouchers = 0
    # A NFC card might only be used as a coffee card.
    if username:
        vouchers = api.get_voucher_balance(username)
    coffee_vouchers = api.get_coffee_voucher_balance(card_uid)

    return Customer(username, is_intern, vouchers, coffee_vouchers)


def display_info(customer):
    output = ""

    if customer.intern:
        output += "Name: %s\n" % customer.username
        output += "Bonger: %2d\n" % customer.vouchers
    output += "Kaffe: %2d" % customer.coffee_vouchers

    write(bar_lcd, output)
    # We don't want to display the username on the customer screen
    if customer.intern:
        output = output[output.find("\n")+1:]
    write(customer_lcd, output)


# TODO: Figure out a way to make this function use lcd.menu(), since they're more or less the same thing.
def get_amount():
    amount = 0
    prev_amount = None
    active_button = None # To avoid adding/removing multiple bong in one press.

    while not GPIO.input(ENTER_BUTTON):
        if amount is not prev_amount:
            time.sleep(0.05)
            prev_amount = amount
            write(bar_lcd, "Antall a fjerne: %2d" % amount, clean=False, start_position=3)
        
        if GPIO.input(CANCEL_BUTTON):
            return 0
        elif GPIO.input(PLUSS_BUTTON):
            if active_button is not PLUSS_BUTTON:
                amount += 1
            active_button = PLUSS_BUTTON
        elif GPIO.input(MINUS_BUTTON) and amount > 0:
            if active_button is not MINUS_BUTTON:
                amount -= 1
            active_button = MINUS_BUTTON
        else:
            active_button = None
        
    return amount


def register_use(customer, amount):
    for lcd in bar_lcd, customer_lcd:
        write(lcd, "Trekker %d bonger" % amount)

    if api.use_vouchers(customer.username, amount):
        for lcd in bar_lcd, customer_lcd:
            write(lcd, "%d bonger trukket" % amount)
    else:
        write(customer_lcd, "Du har ikke nok bonger")
        write(bar_lcd, "Kunden har ikke nok bonger")


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
        time.sleep(5)
