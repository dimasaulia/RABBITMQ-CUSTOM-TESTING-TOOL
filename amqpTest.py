"""
THIS SCRIPT USE FOR AUTOMATE SMART DOOR AMQP DATA TRANSMISSION TESTING
"""
import pika
import json
import time
import random
import requests
import cuid
from unittest.mock import MagicMock
from concurrent.futures import ThreadPoolExecutor, thread
from threading import Thread
from logHandler import setup_logging
from datetime import datetime

# URL
BASE_URL = "http://127.0.0.1:8000"
ADD_CARD_URL = f"{BASE_URL}/api/v1/card/add-access-card-to-room"
REMOVE_CARD_URL = f"{BASE_URL}/api/v1/room/unpair"
EDIT_CARD_URL = f"{BASE_URL}/api/v1/card/admin-modify-card/"
logger = setup_logging()


# DEFINE AND LOG-IN SUPERADMIN AND PASSWORD
SECRET = {
    "username": "dimasaulia",
    "password": "T4np4$4nd1"
}
RUID = "RDl-Y"
LOGIN = requests.post(url=f'{BASE_URL}/api/v1/user/login', json=SECRET)
ADMIN_AUTH = LOGIN.cookies

# ASK DATA SOURCE
# FILE_PATH = input("Path to data source: ")
FILE_PATH = "./datasource.json"
# OPEN DATA SOURCE
FILE = open(f'{FILE_PATH}')
if not FILE_PATH.endswith(".json"):
    print("ONLY JSON FILE ALLOW TO BE DATA SOURCE!")
    exit()
DATA_SOURCE = json.load(FILE)
FILE.close()

# ASK HOW MANY FAKE AMQP CONNECTION TO MAKE
FAKE_AMQP_CONNECTION = int(input("how much fake amqp connection: "))

# ASK HOW LONG TESTING
TESTING_DURATION = int(input("How much iteration: "))
ITERATION_EACH_TEST = int(input("Data transfer per iteration: "))
TESTING_INTERVAL = float(input("How long delay beetwen request: "))

# DEFINE ACTION: ACTION LIKE ADD CARD NUMBER, REMOVE CARD NUMBER, MODIFY CARD
ACTION_LIST = ["ADD_CARD", "REMOVE_CARD", "MODIFY_CARD"]

print("|\tTESTING INTERVAL\t|\tEXAMINATIONS")
print(f"|\t{TESTING_INTERVAL}\t\t|\t{TESTING_DURATION}")

FAKE_AMQP_CONSUMER = []
FAKE_AMQP_PRODUCER = []
RABIT_SETTINGS = {
    "protocol": "amqp",
    "hostname": "192.168.220.184",
    "port": 5672,
    "vhost": "0.0.0.0",
    "exchange": "smartdoor",
    "queues": [""],
}
LAST_ACTION = ""
ALLOWED_CARD = {}
ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID = []

running = True


def stop_execution():
    global running
    running = False


class FakeConnection:

    @staticmethod
    def createProducer(connectionId):
        msgId = 0
        while running:
            credential = pika.PlainCredentials("smartdoor", "t4np454nd1")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(RABIT_SETTINGS["hostname"], RABIT_SETTINGS["port"], "0.0.0.0", credential))
            properties = pika.BasicProperties(delivery_mode=2)
            exchange = f"dummy-exchange-{connectionId}"
            bindingKey = f"dummy/{connectionId}/gateway"
            queue = f"dummy-queue-{connectionId}"
            channel = connection.channel()
            channel.exchange_declare(
                exchange=exchange, exchange_type='direct', durable=True)
            result = channel.queue_declare(
                queue, exclusive=False, durable=True)
            queue_name = result.method.queue
            data_obj = []

            def send():
                msgCUID = cuid.cuid()

                # channel.queue_bind(exchange=exchange,
                #                    queue=queue_name, routing_key=bindingKey)

                data = {
                    "cardNumber": "E82a4b2BA0Db",
                    "cardPin": "$2b$10$n39.7Zz/NSPTI3iXudyqoeI7xVhH0yx.OHQYwuW1l6SRT3RmQAAIq",
                    "cardStatus": "REGISTER",
                    "isBanned": False,
                    "isTwoStepAuth": True,
                    "duid": "Z37YC",
                    "createdAt": "2023-06-25T18:31:42.258Z",
                    "messageId": msgCUID,
                    "broadcastTimeAt": datetime.now().isoformat()
                }
                channel.basic_publish(
                    exchange=exchange,
                    routing_key=bindingKey,
                    body=json.dumps(data),
                    properties=properties
                )

                print(
                    f"Sending message for connection {connectionId}, msg id {msgCUID}")
                # print(data)
                logger.info(f"[AMQP PRODUCER] - Addcard - {data}")

            with ThreadPoolExecutor(ITERATION_EACH_TEST) as executor:
                executor.map(send, )
                executor.shutdown(wait=True)

            connection.close()
            if msgId > TESTING_DURATION:
                break
            msgId += 1
            time.sleep(TESTING_INTERVAL)
        exit()

    @staticmethod
    def createConsumer(connectionId):
        while running:
            credential = pika.PlainCredentials("smartdoor", "t4np454nd1")
            connection = pika.BlockingConnection(
                pika.ConnectionParameters(RABIT_SETTINGS["hostname"], RABIT_SETTINGS["port"], "0.0.0.0", credential))

            exchange = f"dummy-exchange-{connectionId}"
            queue = f"dummy-queue-{connectionId}"
            bindingKey = f"dummy/{connectionId}/gateway"

            channel = connection.channel()
            channel.exchange_declare(
                exchange, exchange_type='direct', durable=True)
            result = channel.queue_declare(
                queue, exclusive=False, durable=True)
            queue_name = result.method.queue

            channel.queue_bind(exchange=exchange, queue=queue_name,
                               routing_key=bindingKey)

            def callback(ch, method, properties, body):
                action = method.routing_key.split(".")[0]
                # payloadObj = json.loads(body)
                print(f"[AMQP] - receive data - {action} - {body}")
                logger.info(f"[AMQP CONSUMER] - Addcard - {body}")

            print(
                f'[AMQP] waiting data for connection id {connectionId}, Binding key {bindingKey} ')
            channel.basic_consume(
                queue=queue_name, on_message_callback=callback, auto_ack=True)
            channel.start_consuming()


for i in range(FAKE_AMQP_CONNECTION):
    FAKE_AMQP_CONSUMER.append(
        Thread(target=lambda: FakeConnection.createConsumer(f"{i}")))

for i in range(FAKE_AMQP_CONNECTION):
    FAKE_AMQP_PRODUCER.append(
        Thread(target=lambda: FakeConnection.createProducer(f"{i}")))

for i, connection in enumerate(FAKE_AMQP_CONSUMER):
    connection.start()

for i, connection in enumerate(FAKE_AMQP_PRODUCER):
    connection.start()
