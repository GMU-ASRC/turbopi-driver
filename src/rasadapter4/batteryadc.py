"""
Battery ADC Driver

This driver is for the built-in battery ADC on the Hiwonder Rasadapter 4.
The ADC reads the series voltage from the two 18650 batteries and returns
an integer voltage in millivolts. This driver will return the value in volts.

The driver is a singleton, so you can access it via the `battery` global.

Example:

.. code-block:: python
    import time
    from rasadapter4 import battery
    while True:
        print(f'Battery voltage: {battery.voltage}')
        time.sleep(1)


The voltage reading will be -1 upon read failure, but this
can be overridden by setting the `Battery.failed_read_value` class attribute.

Hardware note: It is likely that the analog-to-digital converter (ADC) on the
rasadapter for the Pi 4 is not a separate chip, but is instead part of the
board's microcontroller. Note that the ADC's I2C address is shared with other
peripherals in this driver package.
"""


from retry import retry
from smbus2 import SMBus, i2c_msg


class Battery:
    bus_id = 1
    address = 0x7A  # 122
    register = 0x0
    failed_read_value = -1

    def __init__(self, i2c=None, address=None, register=None):
        # the ifs make it use the class defaults if not specified (shared across all instances)
        if i2c is not None:
            self.bus_id = i2c
        if address is not None:
            self.address = address
        if register is not None:
            self.register = register

    @retry((OSError), tries=3, delay=1, backoff=3)
    def read_register_v(self):
        msg = i2c_msg.write(self.address, [self.register,])
        read = i2c_msg.read(self.address, 2)
        with SMBus(self.bus_id) as bus:
            bus.i2c_rdwr(msg)  # does not support repeated start
            bus.i2c_rdwr(read)  # do not combine with previous line
        return int.from_bytes(bytes(list(read)), 'little')

    @property
    def voltage(self):
        """Battery voltage in volts, up to 3 decimal places.
        Returns `self.failed_read_value` if the read fails (-1 by default).
        """
        v = self.read_register_v()
        if v < 1 or v > 20000:
            return self.failed_read_value
        return v / 1000.0


def get_default_battery():
    return Battery()


#: The default battery instance.
battery: Battery

try:
    battery = get_default_battery()
except Exception as e:
    battery = None
    print(e)
