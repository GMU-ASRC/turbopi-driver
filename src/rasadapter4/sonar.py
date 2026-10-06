from retry import retry
from smbus2 import SMBus, i2c_msg


class I2CSonar:
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

    @retry((OSError), stop_max_attempt_number=3, delay=1, backoff=3)
    def set_rgb_mode(self, mode):
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, self.REG_RGB_MODE, mode)

    def numPixels(self):
        return 2

    def __len__(self):
        return self.numPixels()

    @retry((OSError), stop_max_attempt_number=3, delay=1, backoff=3)
    def write_color_register(self, register: int, value: int):
        if value < 0 or value > 255:
            raise ValueError("Value not between 0 and 255: ", value)
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, register, value)

    @retry((OSError), stop_max_attempt_number=3, delay=1, backoff=3)
    def write_pixel_register_sep(self, start_register: int, rgb: int):
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, start_register, 0xFF & (rgb >> 16))
            bus.write_byte_data(self.address, start_register + 1, 0xFF & (rgb >> 8))
            bus.write_byte_data(self.address, start_register + 2, 0xFF & rgb)

    @retry((OSError), stop_max_attempt_number=3, delay=1, backoff=3)
    def write_pixel_registers(self, start_register: int, rgb: int):
        # data = [start_register, 0xFF & (rgb >> 16), 0xFF & (rgb >> 8), 0xFF & rgb]
        data = [start_register, *int(rgb).to_bytes(3, 'little', signed=False)]
        msg = i2c_msg.write(self.address, data)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(start_register + msg)

    # TODO: allow passing color tuple, color string, etc
    def set_pixel_color(self, index: int, rgb: int):
        if index not in self.PIXEL_START_REG:
            raise ValueError("Invalid pixel index: ", index)
        self.write_pixel_register_sep(self.PIXEL_START_REG[index], rgb)
        self._pixel_values[index] = rgb

    def fill_color(self, rgb: int):
        for i in self.PIXEL_START_REG:
            self.set_pixel_color(i, rgb)

    def get_pixel_color(self, index: int):
        if index not in self.PIXEL_START_REG:
            raise ValueError("Invalid pixel index: ", index)
        return ((self._pixel_values[index] >> 16) & 0xFF,
                (self._pixel_values[index] >> 8) & 0xFF,
                self._pixel_values[index] & 0xFF)

    def write_breath_register(self, reg: int, ms: int):
        ms = ms // 100
        with SMBus(self.bus_id) as bus:
            bus.write_byte_data(self.address, reg, ms)

    @retry((OSError), stop_max_attempt_number=3, delay=1, backoff=3)
    def measure_distance(self):
        msg = i2c_msg.write(self.address, [self.REG_DIST,])
        read = i2c_msg.read(self.address, 2)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(msg, read)
        return int.from_bytes(bytes(list(read)), byteorder='little', signed=False)

    @property
    def distance(self) -> int:
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