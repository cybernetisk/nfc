import time
import smbus
import RPi.GPIO as GPIO

from constants import *


class LcdDisplay:
    def __init__(self, addr, bus_id):
        self.addr = addr
        self.bus = smbus.SMBus(bus_id)

    def _raw(self, data):
        for c in data:
            self.bus.write_byte(self.addr, ord(c))

    def clean(self):
        self._raw("CL")

    def write(self, text):
        self._raw("TT%s\x00" % text)

    def newline(self):
        self._raw("TRT")

    def set_pointer(self, x, y):
        self._raw("TP%c%c" % (x, y))

    def set_size(self, x, y):
        self._raw("STCR%c%c\x80\xC0\x94\xd4" % (x, y))

    def tick_off(self):
        self._raw("CS%c" % 0)

    def tick_on(self):
        self._raw("CS%c" % 1)

    def new_i2c_addr(self, new_addr):
        # new_addr e.g. 0x28
        self._raw("SI2CA%c" % new_addr)


def write(lcds, text, clean=True, start_position=0):
    """
    Handles writing to lcd displays

    :param lcds: Lcd(s) to write to
    :param text: What to write to the display
    :param clean: If the display should clean before writing
    :param start_position: What y-possition to write to.
    """
    if clean:
        for lcd in lcds:
            lcd.clean()

    text = text.splitlines()
    for lcd in lcds:
        if start_position != 0:
            lcd.set_pointer(0, start_position)
            # These displays are shit, so we need to wait a bit before writing. If not we'll get a blank screen
            time.sleep(0.1)
        for i in range(len(text)):
            lcd.write(text[i])
            lcd.newline()


class _Menu:
    """
    Menu base class. Used for creating a menu on the LCD panel.
    """
    active_button = None  # The button that is currently pressed
    active_choice = None  # Current choice
    running = True  # If the menu is still running

    def __init__(self, lcds, clean=True, position=0):
        """
        :param lcds: lcd(s) to write to
        :param clean: If the lcd(s) should clean before runnin
        :param position: Starting y-position of the cursor
        """
        self.lcds = lcds
        self.clean = clean
        self.position = position

        if clean:
            for lcd in lcds:
                lcd.clean()

    def _clean_up(self):
        """
        Cleans up after the main loop is finished.
        """
        pass

    def _lcd_output(self):
        """
        Processor for what the LCD should output based on the current choice

        :return: Text to display on the LCD
        """
        return self.active_choice

    def _enter_action(self):
        """
        Defines what should happen when the enter button is pressed
        """
        self.running = False

    def _cancel_action(self):
        """
        Defines what should happen when the enter button is pressed
        """
        self.running = False
        self.active_choice = None

    def _plus_action(self):
        """
        Defines what should happen when the plus button is pressed
        """
        pass

    def _minus_action(self):
        """
        Defines what should happen when the minus button is pressed
        """
        pass

    def _return_action(self):
        """
        Processes the active choice and returns the proper return value.

        :return: Return value
        """
        return self.active_choice

    def _use_button(self, button, function):
        """
        Logic for button presses

        :param button: Button that is pressed
        :param function: Corresponding function for that button
        """
        if self.active_choice is CANCEL_BUTTON:
            return

        self.active_button = button
        function()

    def menu(self):
        """
        Actual menu loop
        """
        prev_output = None

        while self.running:
            output = self._lcd_output()
            if output != prev_output:
                prev_output = output
                write(self.lcds, output, self.clean, self.position)

            if GPIO.input(CANCEL_BUTTON):
                if self.active_choice is CANCEL_BUTTON:
                    continue
                self.active_choice = CANCEL_BUTTON
                self._use_button(CANCEL_BUTTON, self._cancel_action)
            elif GPIO.input(ENTER_BUTTON):
                if self.active_choice is ENTER_BUTTON:
                    continue
                self.active_choice = ENTER_BUTTON
                self._use_button(ENTER_BUTTON, self._enter_action)
            elif GPIO.input(PLUSS_BUTTON):
                if self.active_choice is PLUSS_BUTTON:
                    continue
                self.active_choice = PLUSS_BUTTON
                self._use_button(PLUSS_BUTTON, self._plus_action)
            elif GPIO.input(MINUS_BUTTON):
                if self.active_choice is MINUS_BUTTON:
                    continue
                self.active_choice = MINUS_BUTTON
                self._use_button(MINUS_BUTTON, self._minus_action)
            else:
                self.active_button = None

        self._clean_up()
        # The enter button is usually held for a few more ms, causing later options to get automatically selected.
        while GPIO.input(ENTER_BUTTON) or GPIO.input(CANCEL_BUTTON):
            pass
        return self._return_action()


class ChoiceMenu(_Menu):
    """
    Menu with menu items
    Typically used for yes and no answers, etc.
    """
    def __init__(self, lcds, description, choices, clean=True, position=0):
        super().__init__(lcds, clean, position)
        self.active_choice = 0
        self.description = description
        self.choices = choices

    def _lcd_output(self):
        output = self.description
        for i in range(len(self.choices)):
            output += "\n"
            if self.active_choice == i:
                output += "*"
            else:
                output += " "
            output += self.choices[i]
        return output

    def _plus_action(self):
        if self.active_choice < len(self.choices) - 1:
            self.active_choice += 1
        else:
            self.active_choice = 0

    def _minus_action(self):
        if self.active_choice > 0:
            self.active_choice -= 1
        else:
            self.active_choice = len(self.choices) - 1  # Wrap to end

    def _return_action(self):
        if self.active_choice is None:
            return self.active_choice
        return self.choices[self.active_choice]


class AmountMenu(_Menu):
    """
    Menu used to get an amount from the user.
    """
    def __init__(self, lcds, prompt, clean=True, position=0):
        super().__init__(lcds, clean, position)
        self.active_choice = 0
        self.prompt = prompt

    def _lcd_output(self):
        return "%s: %2d" % (self.prompt, self.active_choice)

    def _plus_action(self):
        self.active_choice += 1

    def _minus_action(self):
        if self.active_choice > 0:
            self.active_choice -= 1


class KeyboardMenu(_Menu):
    """
    Menus where we want text input.

    ` is used for empty character
    """

    def __init__(self, lcds, prompt, clean=True, position=0):
        super().__init__(lcds, clean, position)
        self.active_choice = "`"  # Initializes the text-string
        self.prompt = prompt + "\n> "

        for lcd in lcds:
            lcd.tick_on()

    def _lcd_output(self):
        if self.active_choice[-1] is '`':
            return self.prompt + str(self.active_choice[:-1])
        return self.prompt + str(self.active_choice)

    def _enter_action(self):
        if self.active_choice[-1] == '`':
            self.running = False
            pass
        else:
            self.active_choice += '`'

    def _change_last_char(self, operator):
        cur_char = ord(self.active_choice[-1]) - 96  # Only deal with lower case characters (And a extra char for nothing)
        cur_char = operator(cur_char, 1) % 27  # 26 characters in the alphabet (plus one for nothing)
        cur_char += 96  # Set it back to lower case character

        self.active_choice = self.active_choice[:-1] + chr(cur_char)

    def _plus_action(self):
        self._change_last_char(lambda a, b: a + b)

    def _minus_action(self):
        self._change_last_char(lambda a, b: a - b)

    def _clean_up(self):
        for lcd in self.lcds:
            lcd.tick_off()
