#!/bin/python3
import sys
import configparser
import RPi.GPIO as GPIO

import main
from api import CybApi
from lcd import *

# Host address of the LCD display
bar_lcd = LcdDisplay(0x28, BUS_ID)  # Large display
customer_lcd = LcdDisplay(0x27, BUS_ID)  # Small display
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
        lcd.write("Loading system!")

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
    main.open()


def get_card_id():
    write((bar_lcd, customer_lcd), "Waiting for card")

    return main.getid()


def register_customer(card_uid):
    username = ""
    user_id = ""
    is_intern = False

    choice = ChoiceMenu((bar_lcd,), "Is the person an intern?", ("Yes", "No")).menu()
    if choice is "Yes":
        is_intern = True
        while not user_id:
            username = KeyboardMenu((bar_lcd, customer_lcd), "Username").menu()
            if not username:
                return (None, None)  # Empty username means cancel

            user = api.get_user(username)
            if "detail" in user:  # If there is a detail, it means that we didn't get a match.
                write((bar_lcd, customer_lcd), "User not found")
                time.sleep(2)  # Give user some time to read
            else:
                user_id = user["id"]
    elif choice is None:
        return (None, None)

    write((bar_lcd, customer_lcd), "Registrating card")
    if api.register_card(card_uid, user_id, is_intern):
        write((bar_lcd, customer_lcd), "Card registerd!")
        time.sleep(2)  # Give the user some time to read

    return (username, is_intern)


def get_customer(card_uid):
    username, is_intern = api.get_card_info(card_uid)

    # The card is not in the database
    if username is None:
        write((customer_lcd,), "Not accepted")
        choice = ChoiceMenu((bar_lcd,), "Unknown card", ("Register", "Cancle")).menu()
        if choice is "Cancle" or choice is None:
            return None

        username, is_intern = register_customer(card_uid)
        if username is None:
            return None

    vouchers = 0
    # A NFC card might only be used as a coffee card.
    if is_intern:
        vouchers = api.get_voucher_balance(username)
    coffee_vouchers = api.get_coffee_voucher_balance(card_uid)

    return Customer(username, is_intern, vouchers, coffee_vouchers)


def display_info(customer):
    output = ""

    if customer.intern:
        output += "Name: %s\n" % customer.username
        output += "Vouchers: %2d\n" % customer.vouchers
    output += "Coffee: %2d" % customer.coffee_vouchers

    write((bar_lcd,), output)
    # We don't want to display the username on the customer screen
    if customer.intern:
        output = output[output.find("\n") + 1:]
    write((customer_lcd,), output)


def register_use(identifier, amount, api_method):
    write((bar_lcd, customer_lcd), "Witdrawing %d vouchers" % amount)

    if api_method(identifier, amount):
        write((bar_lcd, customer_lcd), "%d vouchers withdrawn" % amount)
    else:
        write((bar_lcd, customer_lcd), "Not enough vouchers")


def register_vouchers(card_uid, amount):
    write((bar_lcd, customer_lcd), "Adding %d vouchers" % amount)

    if api.register_coffee_vouchers(card_uid, amount):
        write((bar_lcd, customer_lcd), "%d vouchers added" % amount)
    else:
        write((bar_lcd, customer_lcd), "Wrong D:")


def buy_action():
    # Get customer info
    card_uid = get_card_id()
    customer = get_customer(card_uid)
    if customer is None:
        return

    # Display info about the customer
    display_info(customer)

    # Get amount of bongs to remove
    amount = AmountMenu((bar_lcd,), "Amount to withdraw", clean=False, position=3).menu()
    if not amount:
        return

    # Remove x amount of bongs from customer
    voucher_type = None
    if customer.intern:
        voucher_type = ChoiceMenu((bar_lcd,), "What type?", ("Internvoucher", "Coffeevoucher")).menu()
    if voucher_type is "Internvoucher":
        register_use(customer.username, amount, api.use_vouchers)
    else:
        register_use(card_uid, amount, api.use_coffee_vouchers)

    # Give people some time to read
    time.sleep(5)


def register_action():
    COFFEE_CARD_AMOUNT = 10

    card_uid = get_card_id()
    customer = get_customer(card_uid)  # TODO: Rewrite to get rid of useless actions

    register_vouchers(card_uid, COFFEE_CARD_AMOUNT)

    # Give people some time to read
    time.sleep(5)


if __name__ == "__main__":
    setup()

    while True:
        choice = ChoiceMenu(
            (bar_lcd,),
            "What do you want to do?",
            ("Withdraw", "Buy coffee vouchers")
        ).menu()

        if choice is "Withdraw":
            buy_action()
        elif choice is "Buy coffee vouchers":
            register_action()
