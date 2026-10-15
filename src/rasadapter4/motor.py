"""
I2C Motor Driver
================
This driver is for the I2C motor driver on the Hiwonder Rasadapter 4.

.. autoclass:: I2CMotor
    :members:

.. autoclass:: Motors
    :members:

.. autofunction:: get_default_motors
"""


from warnings import warn

import numpy as np
from retry import retry
from numpy import clip as clamp
from smbus2 import SMBus, i2c_msg


def is_contiguous_indices(indices):
    speeds = np.asarray(indices)
    return np.array_equiv(speeds, np.arange(speeds.min(), speeds.max() + 1))


class I2CMotor:
    """Single I2CMotor Instance to control motor speed.

    Functions which send commands to the board will retry up to 3 times.

    Parameters
    ----------
    index : int
        Motor index (0-3)
    i2c : int, default=1
        I2C bus channel
    address : int, default=0x7A
        I2C peripheral address (rasadapter MCU)
    base_register : int, default=0x1F
        I2C register base address
    speed : int, default=None
        Initial motor speed in percent (0-100)
    """

    bus_id = 1
    address = 0x7A  # 122
    base_register = 0x1F  # 31

    def __init__(self, index, i2c=None, address=None, base_register=None, speed=None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if i2c is not None:
            self.bus_id = i2c
        if address is not None:
            self.address = address
        if base_register is not None:
            self.base_register = base_register
        self.register = self.base_register + index
        self._speed = None
        if speed is not None:
            self.set_speed(speed)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def set_speed(self, speed):
        """Send command to set motor speed.

        Parameters
        ----------
        speed : int
            Motor speed in percent [-100, 100]
        """
        speed = int(clamp(speed, -100, 100))
        msg = i2c_msg.write(
            self.address,
            [
                self.register,
                speed.to_bytes(1, 'little', signed=True)[0]
            ]
        )
        with SMBus(self.bus_id) as bus:
            bus.open(self.bus_id)
            bus.i2c_rdwr(msg)
            bus.close()
        self._speed = speed

    @property
    def speed(self):
        """Set motor speed or get most recently set speed.

        Parameters
        ----------
        speed : int
            Motor speed in percent [-100, 100]
        """
        return self._speed

    @speed.setter
    def speed(self, speed):
        self.set_speed(speed)

    def stop(self):
        """Stop the motor.
        Equivalent to `motor.speed = 0`
        """
        self.set_speed(0)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def _set_speed_contiguous(self, speeds):
        # not meant to be used directly
        # called by Motors.set_speeds for optimized
        speeds = np.array(speeds)
        speeds = speeds.clip(-100, 100)
        msg = i2c_msg.write(
            self.address,
            [
                self.register,
                *speeds.astype(np.int8).tobytes()
            ]
        )
        # msg = i2c_msg.write(
        #     self.address,
        #     [
        #         self.register,
        #         speed.to_bytes(1, 'little', signed=True)[0]
        #     ]
        # )
        with SMBus(self.bus_id) as bus:
            bus.open(self.bus_id)
            bus.i2c_rdwr(msg)
            bus.close()


class Motors:
    def __init__(self, motors=4, offset=0, **kwargs):
        """Group of motors.

        Optimization: If the selected motors are contiguous, the speeds will be set
        using a single I2C command.

        Parameters
        ----------
        motors : int | slice | list, optional
            Indices of motors to use.
        offset : int, default=0
            Offset to add to motor indices.
            Useful if you want to refer to the first motor as motors[1].

        Examples
        --------
        >>> motors = Motors(4)
        >>> motors[0] = 100
        >>> motors[0]
        100
        >>> motors.speeds = [100, 100, 100, 100]  # set all motors to 100
        >>> motors.stop()  # stop all motors
        """
        if isinstance(motors, (int, slice)):
            motor_indices = range(motors)
        else:
            motor_indices = motors
        self.offset = offset
        self.motors = {i: I2CMotor(i, **kwargs) for i in motor_indices}
        self.contiguous = is_contiguous_indices(motor_indices)

    def check_index(self, index):
        if index not in self.motors:
            msg = f"Motor index {index} not registered."
            raise IndexError(msg)

    def set_speed(self, index, speed):
        """Set the speed of a motor in the group.

        Parameters
        ----------
        index : int
        speed : float
        """
        self.check_index(index)
        self.motors[index + self.offset].set_speed(speed)

    def __getitem__(self, index):
        self.check_index(index)
        return self.motors[index + self.offset].speed

    def __setitem__(self, index, value):
        self.check_index(index)
        self.motors[index + self.offset].set_speed(value)

    @property
    def speeds(self):
        """Get/set the speeds of all motors in the group.

        If the motors are contiguous, the speeds will be set using a single I2C command.

        Parameters
        ----------
        speeds : list
            List of motor speeds in percent [-100, 100].
            The length of the list must match the number of motors in the group.
            If the motors are not contiguous, the speeds must be provided
            in the order this instance was initialized with.

        Returns
        -------
        list
            List of motor speeds.
        """
        return [motor.speed for motor in self.motors.values()]

    @speeds.setter
    def speeds(self, speeds):
        if self.contiguous:
            self.set_speeds_contiguous(speeds)
            return

        for motor, speed in zip(self.motors.values(), speeds):
            motor.set_speed(speed)

    def set_speeds_contiguous(self, speeds):
        """Set the motor speeds using a single I2C command.

        Parameters
        ----------
        speeds : Iterable
            List of motor speeds [-100, 100].
        """
        motor = next(iter(self.motors.values()))
        motor._set_speed_contiguous(speeds)
        for motor, speed in zip(self.motors.values(), speeds):
            motor._speed = speed

    @property
    def speedsdict(self):
        """Get/set the speeds of specific motors in the group.

        Parameters
        ----------
        speedsdict : dict
            Dictionary of motor speeds in percent [-100, 100].

        Returns
        -------
        dict
            Dictionary of motor speeds.
        """
        return {i: motor.speed for i, motor in self.motors.items()}

    @speedsdict.setter
    def speedsdict(self, speedsdict):
        for i, speed in speedsdict.items():
            self.motors[i].set_speed(speed)

    def stop(self):
        """Stop all motors in the group."""
        for motor in self.motors.values():
            motor.stop()


def get_default_motors():
    return Motors(4)


#: The default motors instance.
motors: Motors

try:
    motors = get_default_motors()
except Exception as e:
    motors = None
    warn(str(e), ImportWarning, stacklevel=2)
