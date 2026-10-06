from retry import retry
from smbus2 import SMBus, i2c_msg


class Battery:
    bus_id = 1
    address = 0x7A  # 122
    register = 0x0

    def __init__(self, i2c=None, address=None, register=None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if i2c is not None:
            self.bus_id = i2c
        if address is not None:
            self.address = address
        if register is not None:
            self.register = register

    @retry((OSError), tries=3, delay=1, backoff=3)
    def get_voltage(self):
        msg = i2c_msg.write(self.address, [self.register,])
        read = i2c_msg.read(self.address, 2)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(msg, read)
        return int.from_bytes(bytes(list(read)), 'little')


def get_default_battery():
    return Battery()


try:
    battery = get_default_battery()
except Exception as e:
    battery = None
    print(e)
