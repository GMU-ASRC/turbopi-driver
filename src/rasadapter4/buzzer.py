import RPi.GPIO as GPIO

DEFAULT_PIN = 6  # GPIO 6, board pin 31 on RPi4b

GPIO.setmode(GPIO.BCM)


def set_buzzer(new_state, pin=DEFAULT_PIN):
    GPIO.setup(DEFAULT_PIN, GPIO.OUT)
    GPIO.output(DEFAULT_PIN, new_state)


setBuzzer = set_buzzer
