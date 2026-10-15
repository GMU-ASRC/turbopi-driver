"""
I2C Sonar Driver
================
This driver is for the I2C sonar driver on the Hiwonder Rasadapter 4.

.. autoclass:: I2CSonar
    :members:

.. autofunction:: get_default_sonar
"""


from retry import retry
from smbus2 import SMBus, i2c_msg


class I2CSonar:
    """I2C Sonar instance to measure distance or change color.

    Parameters
    ----------
    bus_id : int | None, default=1
        I2C bus channel
    address : int | None, default=0x77
        I2C peripheral address (Sonar)
    """

    REG_DIST = 0

    REG_RGB_MODE = 2
    REG_RGB1_R = 3
    REG_RGB1_G = 4
    REG_RGB1_B = 5
    REG_RGB2_R = 6
    REG_RGB2_G = 7
    REG_RGB2_B = 8

    REG_RGB1_R_BREATHING_CYCLE = 9
    REG_RGB1_G_BREATHING_CYCLE = 10
    REG_RGB1_B_BREATHING_CYCLE = 11
    REG_RGB2_R_BREATHING_CYCLE = 12
    REG_RGB2_G_BREATHING_CYCLE = 13
    REG_RGB2_B_BREATHING_CYCLE = 14

    PIXEL_START_REG = {0: REG_RGB1_R, 1: REG_RGB2_R}

    address = 0x77  # 119
    bus_id = 1

    def __init__(self,
                 bus_id: int | None = None,
                 address: int | None = None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if bus_id is not None:
            self.bus_id = bus_id
        if address is not None:
            self.address = address
        self._pixel_values = [0, 0]
        self.RGBMode = 0

    @retry((OSError), tries=3, delay=1, backoff=3)
    def set_rgb_mode(self, mode):
        """Set the RGB mode.

        Parameters
        ----------
        mode : int
            RGB mode. 0=solid, 1=breathing
        """
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, self.REG_RGB_MODE, mode)

    def solid(self):
        """Set the RGB mode to solid."""
        self.set_rgb_mode(0)

    def breath(self):
        """Set the RGB mode to breathing."""
        self.set_rgb_mode(1)

    def numPixels(self):
        """Get the number of color pixels. Always 2."""
        return 2

    def __len__(self):
        return self.numPixels()

    @retry((OSError), tries=3, delay=1, backoff=3)
    def write_color_register(self, register: int, value: int):
        """Write a value to a single color register.

        Parameters
        ----------
        register : int
            Register number. See class constants for regmap.
        value : int
            8-bit value to write to color register.

        Raises
        ------
        ValueError
        """
        if value < 0 or value > 255:
            raise ValueError("Value not between 0 and 255: ", value)
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, register, value)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def write_pixel_register_sep(self, start_register: int, rgb: int):
        """Write a 24-bit rgb color using three write commands.

        Parameters
        ----------
        start_register : int
            Starting register for pixel. WARNING: This is not checked.
        rgb : int
            24-bit rgb color.
        """
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, start_register, 0xFF & (rgb >> 16))
            bus.write_byte_data(self.address, start_register + 1, 0xFF & (rgb >> 8))
            bus.write_byte_data(self.address, start_register + 2, 0xFF & rgb)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def write_pixel_registers(self, start_register: int, rgb: int):
        """Write a 24-bit rgb color using a single write command.

        Uses I2C/smbus repeated start.

        Parameters
        ----------
        start_register : int
            Starting register for pixel. WARNING: This is not checked.
        rgb : int
            24-bit rgb color.
        """
        # data = [start_register, 0xFF & (rgb >> 16), 0xFF & (rgb >> 8), 0xFF & rgb]
        data = [start_register, *int(rgb).to_bytes(3, 'little', signed=False)]
        msg = i2c_msg.write(self.address, data)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(start_register + msg)

    # TODO: allow passing color tuple, color string, etc
    def set_pixel_color(self, index: int, rgb: int):
        """Set the color of a single pixel.

        Parameters
        ----------
        index : int
            Pixel index. 0 or 1.
        rgb : int
            24-bit rgb color.
        """
        if index not in self.PIXEL_START_REG:
            raise ValueError("Invalid pixel index: ", index)
        self.write_pixel_register_sep(self.PIXEL_START_REG[index], rgb)
        self._pixel_values[index] = rgb

    def fill_color(self, rgb: int):
        """Set all pixels to the same color.

        Parameters
        ----------
        rgb : int
            24-bit rgb color.
        """
        for i in self.PIXEL_START_REG:
            self.set_pixel_color(i, rgb)

    def get_pixel_color(self, index: int):
        """Get the last set color for a pixel.

        Parameters
        ----------
        index : int
            Index of the pixel.

        Returns
        -------
        tuple[int, int, int]
            Three 8-bit values representing the red, green, and blue components of the color.

        Raises
        ------
        ValueError
        """
        if index not in self.PIXEL_START_REG:
            raise ValueError("Invalid pixel index: ", index)
        return ((self._pixel_values[index] >> 16) & 0xFF,
                (self._pixel_values[index] >> 8) & 0xFF,
                self._pixel_values[index] & 0xFF)

    def write_breath_register(self, reg: int, ms: int):
        """Set a color breathing register.

        .. hint:
            Don't forget to set the sonar color mode to breathing with `set_rgb_mode(1)`.

        The sonar module has a breathing cycle for each color on each pixel.
        You cannot set the max/min intensity, only the period of the cycle.
        Once breathing starts, the color will go from max intensity to min intensity,
        then back to max intensity, over the period set.

        .. note::
            The register is a single byte, so the period can only be set in increments of 100ms.

        Parameters
        ----------
        reg : int
            Register number. Each pixel has a single byte register for the breathing cycle.
            See class constants for regmap.
        ms : int
            Breathing cycle in milliseconds, up to 25500.
            If 0, the color will not light up.

        Examples
        --------
        # breath red. Amplitude will roughly follow cos(2pi*t/2000)
        >>> sonar.breath()
        >>> sonar.write_breath_register(sonar.REG_RGB1_R_BREATHING_CYCLE, 2000)
        >>> sonar.write_breath_register(sonar.REG_RGB1_G_BREATHING_CYCLE, 0)
        >>> sonar.write_breath_register(sonar.REG_RGB1_B_BREATHING_CYCLE, 0)
        >>> sonar.write_breath_register(sonar.REG_RGB2_R_BREATHING_CYCLE, 2000)
        >>> sonar.write_breath_register(sonar.REG_RGB2_G_BREATHING_CYCLE, 0)
        >>> sonar.write_breath_register(sonar.REG_RGB2_B_BREATHING_CYCLE, 0)
        # breath rainbow, slightly different each pixel
        >>> sonar.write_breath_register(sonar.REG_RGB1_R_BREATHING_CYCLE, 2000)
        >>> sonar.write_breath_register(sonar.REG_RGB1_G_BREATHING_CYCLE, 3300)
        >>> sonar.write_breath_register(sonar.REG_RGB1_B_BREATHING_CYCLE, 4700)
        >>> sonar.write_breath_register(sonar.REG_RGB2_R_BREATHING_CYCLE, 4600)
        >>> sonar.write_breath_register(sonar.REG_RGB2_G_BREATHING_CYCLE, 2000)
        >>> sonar.write_breath_register(sonar.REG_RGB2_B_BREATHING_CYCLE, 3400)
        """
        ms = ms // 100
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, reg, ms)

    @retry((OSError), tries=3, delay=1, backoff=3)
    def measure_distance(self):
        """Get a distance reading from the ultrasonic sensor.

        Returns
        -------
        int
            Distance in millimeters.
        """
        msg = i2c_msg.write(self.address, [self.REG_DIST,])
        read = i2c_msg.read(self.address, 2)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(msg, read)
        return int.from_bytes(bytes(list(read)), byteorder='little', signed=False)

    @property
    def distance(self) -> int:
        """Get a distance reading from the ultrasonic sensor.

        Returns
        -------
        int
            Distance in millimeters.
        """
        return self.measure_distance()


def get_default_sonar():
    return I2CSonar()


try:
    front_sonar = get_default_sonar()
except Exception as e:
    from warnings import warn
    front_sonar = None
    warn(str(e), ImportWarning, stacklevel=2)


if __name__ == '__main__':
    import time
    s = I2CSonar()
    s.set_rgb_mode(0)
    s.fill_color(0)
    time.sleep(0.1)
    s.fill_color(0xFF0000)
    time.sleep(1)
    s.fill_color(0x00FF00)
    time.sleep(1)
    s.fill_color(0x0000FF)
    time.sleep(1)
    s.set_rgb_mode(1)
    s.write_breath_register(s.REG_RGB1_R_BREATHING_CYCLE, 2000)
    s.write_breath_register(s.REG_RGB1_G_BREATHING_CYCLE, 3300)
    s.write_breath_register(s.REG_RGB1_B_BREATHING_CYCLE, 4700)
    s.write_breath_register(s.REG_RGB2_R_BREATHING_CYCLE, 4600)
    s.write_breath_register(s.REG_RGB2_G_BREATHING_CYCLE, 2000)
    s.write_breath_register(s.REG_RGB2_B_BREATHING_CYCLE, 3400)
    while True:
        time.sleep(1)
        print(s.measure_distance())