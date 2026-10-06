from warnings import warn

import numpy as np
from retry import retry
from numpy import clip as clamp
from smbus2 import SMBus, i2c_msg


def is_contiguous_indices(indices):
    speeds = np.asarray(indices)
    return np.array_equiv(speeds, np.arange(speeds.min(), speeds.max() + 1))


class I2CMotor:
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
        return self._speed

    @speed.setter
    def speed(self, speed):
        self.set_speed(speed)

    def stop(self):
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
        return [motor.speed for motor in self.motors.values()]

    @speeds.setter
    def speeds(self, speeds):
        if self.contiguous:
            self.set_speeds_contiguous(speeds)
            return

        for motor, speed in zip(self.motors.values(), speeds):
            motor.set_speed(speed)

    def set_speeds_contiguous(self, speeds):
        motor = next(iter(self.motors.values()))
        motor._set_speed_contiguous(speeds)
        for motor, speed in zip(self.motors.values(), speeds):
            motor._speed = speed

    @property
    def speedsdict(self):
        return {i: motor.speed for i, motor in self.motors.items()}

    @speedsdict.setter
    def speedsdict(self, speedsdict):
        for i, speed in speedsdict.items():
            self.motors[i].set_speed(speed)

    def stop(self):
        for motor in self.motors.values():
            motor.stop()


def get_default_motors():
    return Motors(4)


try:
    motors = get_default_motors()
except Exception as e:
    motors = None
    warn(str(e), ImportWarning, stacklevel=2)
