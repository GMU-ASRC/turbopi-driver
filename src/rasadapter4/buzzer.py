"""
Buzzer Driver
=============
This driver is for the buzzer on the Hiwonder Rasadapter 4.

.. autofunction:: set_buzzer

.. warning::
    This driver does not play nicely with the newer gpiochip kernel module
    found on newer Raspberry Pi OS versions, especially if multiple processes
    try to use the same GPIO pin.

    If your Pi uses the `lgpio` library, consider using our buzzer daemon found in `turbocore.buzzer`.

"""


import RPi.GPIO as GPIO

#: The default buzzer pin.
DEFAULT_PIN = 6  # GPIO 6, board pin 31 on RPi4b

GPIO.setmode(GPIO.BCM)


def set_buzzer(new_state, pin=DEFAULT_PIN):
    """Set the buzzer state.

    Parameters
    ----------
    new_state : bool
        The new state of the buzzer.
    pin : int, default=DEFAULT_PIN
        The GPIO pin to use, in BCM numbering.
        The default is GPIO 6 (board pin 31).
    """
    GPIO.setup(DEFAULT_PIN, GPIO.OUT)
    GPIO.output(DEFAULT_PIN, new_state)


setBuzzer = set_buzzer
