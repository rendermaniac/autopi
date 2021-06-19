import logging
import datetime
import pigpio

FREQUENCY_MIN = 0
FREQUENCY_MAX = 20000

def clamp(v, minimum, maximum):
    return max(min(v, maximum), minimum)

class Motor(object):

    def __init__(self, pin0, pin1, enable) -> None:
        super().__init__()
        self.pin0 = pin0
        self.pin1 = pin1
        self.pin_enable = enable

        self._power = 0
        self._power_previous = -1

        self._frequency = 2000
        self._frequency_previous = 0

        self.pi = pigpio.pi()

        self.pi.set_PWM_dutycycle(self.pin_enable, self._power)
        self.pi.set_PWM_frequency(self.pin_enable, self._frequency)

        self.backwards_time = None

        self.forwards()

    def forwards(self):

        self.pi.write(self.pin0, 1)
        self.pi.write(self.pin1, 0)

        self.backwards_time = None

    def backwards(self):

        self.pi.write(self.pin0, 0)
        self.pi.write(self.pin1, 1)

        self.backwards_time = datetime.datetime.now()

    def stop(self):
        self._power = 0

    def reset_power(self):
        self._power = 128

    def reset_frequency(self):
        self.frequency = 2000

    def reset(self):
        self.reset_power()
        self.reset_frequency()

    @property
    def frequency(self):
        return self._frequency

    @frequency.setter
    def frequency(self, amount):
        self._frequency = amount

    def change_frequency(self, amount):
        self._frequency = clamp(self._frequency + amount, FREQUENCY_MIN, FREQUENCY_MAX)

    @property
    def power(self):
        return self._power

    @power.setter
    def power(self, amount):
        self._power = amount

    def update(self):

        if self.backwards_time:
            if (datetime.datetime.now() - self.backwards_time).seconds > 2:
                self.forwards()
                logging.debug("Changing back to forwards")

        if self._power_previous != self._power:
            self.pi.set_PWM_dutycycle(self.pin_enable, self._power)
            self._power_previous = self._power
            logging.debug(f"Setting power to {self._power}")

        if self._frequency_previous != self._frequency:
            self.pi.set_PWM_frequency(self.pin_enable, self._frequency)
            self._frequency_previous = self._frequency
            logging.debug(f"Setting frequency to {self._frequency}")

class DualMotors(object):

    def __init__(self, pin0_left, pin1_left, enable_left, pin0_right, pin1_right, enable_right) -> None:
        super().__init__()

        self._left = Motor(pin0_left, pin1_left, enable_left)
        self._right = Motor(pin0_right, pin1_right, enable_right)

        self.turn_time = None
        self.turn_reset_time = 700000

    def forwards(self):

        self._left.forwards()
        self._right.forwards()

    def backwards(self):

        self._left.backwards()
        self._right.backwards()

    def stop(self):
        self._left.stop()
        self._right.stop()

    def turn(self, amount):
        """
        negative turns left
        positive turns right
        """
        self._left.power = clamp(self._left.power + amount, 0, 255)
        self._right.power = clamp(self._right.power - amount, 0, 255)

        self.turn_time = datetime.datetime.now()

    def left(self, amount):
        self.turn(-amount)

    def right(self, amount):
        self.turn(amount)

    def reset_turn(self):
        self._left.reset_power()
        self._right.reset_power()

        self.turn_time = None

    def reset(self):
        self.reset_turn()
        self._left.reset()
        self._right.reset()

    @property
    def frequency(self):
        return (self._left.frequency, self._right.frequency)

    @frequency.setter
    def frequency(self, amount):
        self._left.frequency = amount
        self._right.frequency = amount

    def change_frequency(self, amount):
        self._left.change_frequency(amount)
        self._right.change_frequency(amount)

    @property
    def power(self):
        return (self._left.power, self._right.power)

    @power.setter
    def power(self, amount):
        self._left.power = amount
        self._right.power = amount

    def update(self):

        if self.turn_time:
            if (datetime.datetime.now() - self.turn_time).microseconds > self.turn_reset_time:
                self.reset_turn()

        self._left.update()
        self._right.update()