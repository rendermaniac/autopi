import time
import datetime
import logging
import argparse

from paho.mqtt import client as mqtt_client

import pigpio

def clamp(v, minimum, maximum):
    return max(min(v, maximum), minimum)

def on_message(client, car, msg):
    payload = msg.payload.decode()
    if msg.topic == "/car/direction/backwards":
        car.backwards()
    if msg.topic == "/car/direction/turn":
        car.turn(int(payload))
    if msg.topic == "/car/reset":
        if int(payload) == 0:
            car.stop()
        else:
            car.reset()
    if msg.topic == "/car/throttle":
        car.change_frequency(int(payload))

class Car(object):

    def __init__(self, simulate=False):

        self.frequency = 2000
        self.power_left = 0
        self.power_right = 0

        self.power_left_previous = -1
        self.power_right_previous = -1
        self.frequency_previous = 0
        self.throttle_previous = -1

        self.delay = 0.1

        self.turn_time = None
        self.backwards_time = None

        self.pi = pigpio.pi()

        self.MOTOR_LEFT0 = 19
        self.MOTOR_LEFT1 = 16
        self.MOTOR_LEFT_ENABLE = 12

        self.MOTOR_RIGHT0 = 26
        self.MOTOR_RIGHT1 = 20
        self.MOTOR_RIGHT_ENABLE = 13

        # motor A
        self.pi.set_mode(self.MOTOR_LEFT0, pigpio.INPUT)
        self.pi.set_mode(self.MOTOR_LEFT1, pigpio.INPUT)

        # motor B
        self.pi.set_mode(self.MOTOR_RIGHT0, pigpio.INPUT)
        self.pi.set_mode(self.MOTOR_RIGHT1, pigpio.INPUT)

        # initialize motors
        self.pi.set_PWM_dutycycle(self.MOTOR_LEFT_ENABLE, self.power_left)
        self.pi.set_PWM_dutycycle(self.MOTOR_RIGHT_ENABLE, self.power_right)
        self.pi.set_PWM_frequency(self.MOTOR_LEFT_ENABLE, self.frequency)
        self.pi.set_PWM_frequency(self.MOTOR_RIGHT_ENABLE, self.frequency)

        self.forwards()

        self.client = mqtt_client.Client("car_computer", userdata=self)
        self.client.connect("127.0.0.1", 1883)

        self.client.subscribe("/car/direction/turn")
        self.client.subscribe("/car/direction/backwards")
        self.client.subscribe("/car/reset")
        self.client.subscribe("/car/throttle")

        self.client.on_message = on_message
        self.client.loop_start()

        logging.info("Running car computer")

        print(f"INIT left {self.power_left} right {self.power_right}")

    def forwards(self):

        self.pi.write(self.MOTOR_LEFT0, 1)
        self.pi.write(self.MOTOR_LEFT1, 0)

        self.pi.write(self.MOTOR_RIGHT0, 1)
        self.pi.write(self.MOTOR_RIGHT1, 0)

        self.backwards_time = None

        logging.info("Moving forwards")

    def backwards(self):

        self.pi.write(self.MOTOR_LEFT0, 0)
        self.pi.write(self.MOTOR_LEFT1, 1)

        self.pi.write(self.MOTOR_RIGHT0, 0)
        self.pi.write(self.MOTOR_RIGHT1, 1)

        self.backwards_time = datetime.datetime.now()

        logging.info("Moving backwards")

    def reset_turn(self):
        self.power_left = 128
        self.power_right = 128

        self.turn_time = None
        logging.info("Resetting turning")

    def reset(self):
        self.reset_turn()
        self.frequency = 2000

    def turn(self, amount):
        """
        negative turns left
        positive turns right
        """
        self.power_left = clamp(self.power_left + amount, 0, 255)
        self.power_right = clamp(self.power_right - amount, 0, 255)

        self.turn_time = datetime.datetime.now()

    def change_frequency(self, amount):
        self.frequency = clamp(self.frequency + amount, 0, 20000)

    def stop(self):
        self.power_left = 0
        self.power_right = 0

    def run(self):

        while True:

            now = datetime.datetime.now()
            if self.turn_time:
                if (now - self.turn_time).microseconds > 700000:
                    self.reset_turn()

            if self.backwards_time:
                if (now - self.backwards_time).seconds > 2:
                    self.forwards()

            if self.power_left_previous != self.power_left:
                self.pi.set_PWM_dutycycle(self.MOTOR_LEFT_ENABLE, self.power_left)
                logging.info(f"Setting Left Power: {self.power_left}")

            if self.power_right_previous != self.power_right:
                self.pi.set_PWM_dutycycle(self.MOTOR_RIGHT_ENABLE, self.power_right)
                logging.info(f"Setting Right Power: {self.power_right}")

            if self.frequency_previous != self.frequency:
                self.pi.set_PWM_frequency(self.MOTOR_LEFT_ENABLE, self.frequency)
                self.pi.set_PWM_frequency(self.MOTOR_RIGHT_ENABLE, self.frequency)

            self.power_left_previous = self.power_left
            self.power_right_previous = self.power_right
            self.frequency_previous = self.frequency

            time.sleep(self.delay)

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", type=str, help="pass a simulation csv file instead of live readings")
    args = parser.parse_args()

    car = Car(simulate=args.simulate)
    car.run()

