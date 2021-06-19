import time
import logging
import argparse

from paho.mqtt import client as mqtt_client

from keepalive import ConnectedClientsKeepAlive
from motors import DualMotors

MOTOR_LEFT0 = 19
MOTOR_LEFT1 = 16
MOTOR_LEFT_ENABLE = 12

MOTOR_RIGHT0 = 26
MOTOR_RIGHT1 = 20
MOTOR_RIGHT_ENABLE = 13

def on_message(client, car, msg):
    payload = msg.payload.decode()
    if msg.topic == "/car/direction/backwards":
        car.motors.backwards()
        logging.info("Vehicle going backwards")
    if msg.topic == "/car/direction/left":
        car.motors.left(int(payload))
        logging.info("Turning left")
    if msg.topic == "/car/direction/right":
        car.motors.right(int(payload))
        logging.info("Turning right")
    if msg.topic == "/car/reset":
        if int(payload) == 0:
            car.motors.stop()
            logging.info("Stopping vehicle")
        else:
            car.motors.reset()
            logging.info("Resetting vehicle")
    if msg.topic == "/car/throttle":
        car.motors.change_frequency(int(payload))

class Car(object):

    def __init__(self, simulate=False):

        self.keepalive = ConnectedClientsKeepAlive()
        self.motors = DualMotors(MOTOR_LEFT0, MOTOR_LEFT1, MOTOR_LEFT_ENABLE,
                                 MOTOR_RIGHT0, MOTOR_RIGHT1, MOTOR_RIGHT_ENABLE)

        self.delay = 0.1

        self.client = mqtt_client.Client("car_computer", userdata=self)
        self.client.connect("127.0.0.1", 1883)

        self.client.subscribe("/car/direction/left")
        self.client.subscribe("/car/direction/right")
        self.client.subscribe("/car/direction/backwards")
        self.client.subscribe("/car/throttle")
        self.client.subscribe("/car/reset")

        self.client.on_message = on_message
        self.client.loop_start()

        logging.info("Running vehicle computer")

    def run(self):

        while True:

            if not self.keepalive.poll():
                self.motors.stop()

            self.motors.update()

            time.sleep(self.delay)

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)

    parser = argparse.ArgumentParser()
    parser.add_argument("--simulate", type=str, help="pass a simulation csv file instead of live readings")
    args = parser.parse_args()

    car = Car(simulate=args.simulate)
    car.run()

