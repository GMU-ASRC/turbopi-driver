from warnings import warn

import numpy as np
from retry import retry
from numpy import clip as clamp
from smbus2 import SMBus, i2c_msg


def fmap(x, in_min, in_max, out_min, out_max):
    """Given a set of ranges, remap x to a new set of ranges."""
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class I2CServo:
    bus_id = 1
    address = 0x7A  # 122
    base_register = 0x15  # 21
    min_angle = 0
    max_angle = 180
    min_pulse = 500
    max_pulse = 2500

    def __init__(self, index, i2c=None, address=None, base_register=None,
                 angle=None, pulse=None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if i2c is not None:
            self.bus_id = i2c
        if address is not None:
            self.address = address
        if base_register is not None:
            self.base_register = base_register
        self.register = self.base_register + index
        self._deg = None
        self._pulse = None
        if pulse is not None:
            self.set_pulse(pulse)
        elif angle is not None:
            self.set_deg(angle)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def set_pulse(self, pulse, limit=True):
        if limit:
            pulse = clamp(pulse, self.min_pulse, self.max_pulse)
        pulse = int(round(pulse))
        msg = i2c_msg.write(
            self.address,
            [
                self.register,
                pulse.to_bytes(1, 'little', signed=True)[0]
            ]
        )
        with SMBus(self.bus_id) as bus:
            bus.open(self.bus_id)
            bus.i2c_rdwr(msg)
            bus.close()
        self._pulse = pulse
        self._deg = fmap(pulse, self.min_pulse, self.max_pulse, self.min_angle, self.max_angle)

    def set_deg(self, degrees, limit=True):
        if limit:
            degrees = clamp(degrees, self.min_angle, self.max_angle)
        self.set_pulse(fmap(degrees, self.min_angle, self.max_angle,
                            self.min_pulse, self.max_pulse), limit=False)

    @property
    def deg(self):
        return self._deg

    @deg.setter
    def deg(self, speed):
        self.set_deg(speed)

    @property
    def pulse(self):
        return self._pulse

    @pulse.setter
    def pulse(self, speed):
        self.set_pulse(speed)

    def center(self):
        self.set_deg(90)


def get_default_servos():
    return [I2CServo(i) for i in range(6)]


try:
    servos = get_default_servos()
except Exception as e:
    servos = None
    warn(str(e), ImportWarning, stacklevel=2)
