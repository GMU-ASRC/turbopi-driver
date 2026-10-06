import RPi.GPIO as GPIO

DEFAULT_PIN = 31

GPIO.setmode(GPIO.BOARD)


def set_buzzer(new_state, pin=DEFAULT_PIN):
    GPIO.setup(DEFAULT_PIN, GPIO.OUT)
    GPIO.output(DEFAULT_PIN, new_state)


setBuzzer = set_buzzer
