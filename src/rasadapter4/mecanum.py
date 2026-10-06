from .motor import motors

from numpy import cos, sin, pi, sqrt
from math import atan


class MecanumChassis:
    # A = 67  # mm
    # B = 59  # mm
    # WHEEL_DIAMETER = 65  # mm

    def __init__(self, a=67, b=59, wheel_diameter=65, motors=motors):
        self.motors = motors
        self.a = a
        self.b = b
        self.wheel_diameter = wheel_diameter
        self._velocity = 0
        self._direction = 0
        self._angular_rate = 0

    def reset(self):
        self.motors.stop()

        self._velocity = 0
        self._direction = 0
        self._angular_rate = 0

    def set_velocity(self, velocity, direction, angular_rate, fake=False):
        """
        Use polar coordinates to control moving
        motor1 fl|  ↑  |fr motor2
                 |     |
        motor3 rl|     |rr motor4
        :param velocity: mm/s
        :param direction: Moving direction 0~360deg, 180deg<--- ↑ ---> 0deg
        :param angular_rate:  The speed at which the chassis rotates
        :param fake:
        :return:
        """
        rad_per_deg = pi / 180
        vx = velocity * cos(direction * rad_per_deg)
        vy = velocity * sin(direction * rad_per_deg)
        vp = -angular_rate * (self.a + self.b)
        fl = int(vy + vx - vp)
        fr = int(vy - vx + vp)
        rl = int(vy - vx - vp)
        rr = int(vy + vx + vp)
        if fake:
            return
        self.motors.speeds = [fl, fr, rl, rr]  # set speeds
        self._velocity = velocity
        self._direction = direction
        self._angular_rate = angular_rate

    def translation(self, velocity_x, velocity_y, fake=False):
        velocity = sqrt(velocity_x ** 2 + velocity_y ** 2)
        if velocity_x == 0:
            direction = 90 if velocity_y >= 0 else 270  # pi/2 90deg, (pi * 3) / 2  270deg
        else:
            if velocity_y == 0:
                direction = 0 if velocity_x > 0 else 180
            else:
                direction = atan(velocity_y / velocity_x)  # θ=arctan(y/x) (x!=0)
                direction = direction * 180 / pi
                if velocity_x < 0:
                    direction += 180
                else:
                    if velocity_y < 0:
                        direction += 360
        if fake:
            return velocity, direction
        else:
            return self.set_velocity(velocity, direction, 0)
