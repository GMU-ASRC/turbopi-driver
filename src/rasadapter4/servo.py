"""
I2C Servo Driver
================
This driver is for the I2C PWM servo driver on the Hiwonder Rasadapter 4.

.. autoclass:: I2CServo
    :members:

.. autofunction:: get_default_servos
"""


from warnings import warn

from retry import retry
from numpy import clip as clamp
from smbus2 import SMBus, i2c_msg


def fmap(x, in_min, in_max, out_min, out_max):
    """Given a set of ranges, remap x to a new set of ranges."""
    return (x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min


class I2CServo:
    """Single I2C Servo instance to control servo position or pulse width.

    Functions which send commands to the board will retry up to 3 times.

    Parameters
    ----------
    index : int
        The index of I2C Servo PWM output. 0-5.
    i2c : int, default=1
        I2C bus channel
    address : int, default=0x7A
        I2C peripheral address (rasadapter MCU)
    base_register : int, default=0x15
        I2C register base address
    angle : int, default=None
        Initial angle in degrees. 0-180.
    pulse : int, default=None
        Initial pulse width in microseconds. 500-2500.

    Examples
    --------
    >>> servo = I2CServo(0)
    >>> servo.pulse = 1500
    >>> servo.pulse
    1500
    >>> servo.deg = 90
    """
    bus_id = 1
    address = 0x7A  # 122
    base_register = 0x15  # 21
    SERVO_CMD_REG = 0x28  # 40
    min_angle = 0
    max_angle = 180
    min_pulse = 500
    max_pulse = 2500

    def __init__(self, index: int, i2c=None, address=None, base_register=None,
                 angle=None, pulse=None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if i2c is not None:
            self.bus_id = i2c
        if address is not None:
            self.address = address
        if base_register is not None:
            self.base_register = base_register
        self.index = index
        self.register = self.base_register + index
        self._deg = None
        self._pulse = None
        if pulse is not None:
            self.set_pulse(pulse)
        elif angle is not None:
            self.set_deg(angle)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def set_pulse(self, pulse, use_time=None, limit=True):
        """Set the pulse width of the servo.

        Parameters
        ----------
        pulse : float
            The pulse width in microseconds.
        use_time : None | int, optional
        limit : bool, default=True
            Limit the pulse width to within I2CServo.min_pulse and I2CServo.max_pulse.

        Raises
        ------
        ValueError
        """
        if limit:
            pulse = clamp(pulse, self.min_pulse, self.max_pulse)
        pulse = int(round(pulse))
        if use_time is None:
            data = [
                self.register,
                pulse.to_bytes(1, 'little', signed=True)[0]
            ]
        else:
            if use_time not in range(0, 30001):
                raise ValueError("use_time must be in range(0, 30000)")
            data = [
                self.SERVO_CMD_REG,
                1,
                *list(use_time.to_bytes(2, 'little')),
                int(self.index),
                *list(pulse.to_bytes(2, 'little'))
            ]
        msg = i2c_msg.write(self.address, data)
        with SMBus(self.bus_id) as bus:
            bus.open(self.bus_id)
            bus.i2c_rdwr(msg)
            bus.close()
        self._pulse = pulse
        try:
            self._deg = fmap(pulse, self.min_pulse, self.max_pulse, self.min_angle, self.max_angle)
        except Exception as e:
            warn(str(e), RuntimeWarning, stacklevel=2)

    def set_deg(self, degrees, limit=True):
        """Set the angle of the servo.

        Parameters
        ----------
        degrees : float
            The angle in degrees.
        limit : bool, default=True
            Limit the angle to within I2CServo.min_angle and I2CServo.max_angle.
        """
        if limit:
            degrees = clamp(degrees, self.min_angle, self.max_angle)
        self.set_pulse(fmap(degrees, self.min_angle, self.max_angle,
                            self.min_pulse, self.max_pulse), limit=False)

    @property
    def deg(self):
        """Get/set the angle of the servo.

        Parameters
        ----------
        degrees : float
            The angle in degrees.

        Returns
        -------
        float
            The last angle set, in degrees.
        """
        return self._deg

    @deg.setter
    def deg(self, speed):
        self.set_deg(speed)

    @property
    def pulse(self):
        """Get/set the pulse width of the servo.

        Parameters
        ----------
        speed : int
            The pulse width in microseconds.

        Returns
        -------
        int
            The last pulse width set, in microseconds.
        """
        return self._pulse

    @pulse.setter
    def pulse(self, speed):
        self.set_pulse(speed)

    def center(self):
        """Set the angle of the servo to 90 degrees."""
        self.set_deg(90)


def get_default_servos():
    return [I2CServo(i) for i in range(6)]


#: List of 6 default servos.
servos: list[I2CServo]

try:
    servos = get_default_servos()
except Exception as e:
    servos = None
    warn(str(e), ImportWarning, stacklevel=2)
