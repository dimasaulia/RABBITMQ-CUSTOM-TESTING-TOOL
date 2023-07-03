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
RUID = "yXeWi"
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
TESTING_DURATION = int(input("How long duration to send all data: "))
TESTING_INTERVAL = float(input("How long interval you need: "))
TESTING_COUNT = round(TESTING_DURATION/TESTING_INTERVAL)

# ASK HOW MANY THREAD USE FOR SENDING REQUEST
THREAD_SIZE = int(input("How many thread you want to use?: "))

# DEFINE ACTION: ACTION LIKE ADD CARD NUMBER, REMOVE CARD NUMBER, MODIFY CARD
ACTION_LIST = ["ADD_CARD", "REMOVE_CARD", "MODIFY_CARD"]

print("|\tTESTING DURATION\t|\tTESTING INTERVAL\t|\tEXAMINATIONS")
print(f"|\t\t{TESTING_DURATION}\t\t|\t\t{TESTING_INTERVAL}\t\t|\t\t{TESTING_COUNT}")

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
            # properties = pika.BasicProperties(delivery_mode=2)
            exchange = f"dummy-exchange-{connectionId}"
            bindingKey = f"dummy/{connectionId}/gateway"
            queue = f"dummy-queue-{connectionId}"
            channel = connection.channel()
            channel.exchange_declare(
                exchange=exchange, exchange_type='direct', durable=True)
            result = channel.queue_declare(
                queue, exclusive=False, durable=True)
            queue_name = result.method.queue

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
                "messageId": cuid.cuid(),
                "broadcastTimeAt": datetime.now().isoformat()
            }
            channel.basic_publish(
                exchange=exchange,
                routing_key=bindingKey,
                body=json.dumps(data),
                # properties=properties
            )
            print(
                f"Sending message for connection {connectionId}, msg id {msgId}")
            print(data)
            # logger.info(f"[AMQP PRODUCER] - Addcard - {data}")
            msgId += 1
            connection.close()
            time.sleep(1)
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


def addCardAction():
    # PICK RANDOM CARD NUMBER
    data_source_id = str(random.randint(0, len(DATA_SOURCE)-1))
    # TRY LOOK ALLOWED CARD, IF CARD ALREADY HAVE ACCESS TRY DIFFERENT CARD
    while (data_source_id) in ALLOWED_CARD:
        data_source_id = random.randint(0, len(DATA_SOURCE)-1)

    # THIS IS DONE FOR THE PROCESS OF DELETING CARD DATA, SINCE DELETING CAN BE DONE WHEN THE CARD IS REGISTERED
    used_data = DATA_SOURCE[int(data_source_id)]
    used_data["ruid"] = RUID
    ALLOWED_CARD[data_source_id] = used_data
    ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID.append(data_source_id)
    return used_data


def removeCardAction():
    # DO FIND RANDOM CARD NUMBER FROM THE ARRAY, REMOVE THAT CARD FROM ARRAY, SEND REQUEST TO SERVER
    allowed_card_id = str(random.randint(
        0, len(ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID)-1))
    allowed_card = ALLOWED_CARD[ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID[int(
        allowed_card_id)]]
    # print("remove card", allowed_card_id, allowed_card)
    # REMOVE THAT CARD FROM ARRAY
    del ALLOWED_CARD[ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID[int(
        allowed_card_id)]]
    ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID.pop(int(allowed_card_id))
    allowed_card["ruid"] = RUID
    return (allowed_card)


def modifyCardAction():
    # DO FIND RANDOM CARD NUMBER FROM THE ARRAY, SEND REQUEST TO SERVER TO MODIFY CARD
    allowed_card_id = str(random.randint(
        0, len(ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID)-1))
    allowed_card = ALLOWED_CARD[ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID[int(
        allowed_card_id)]]
    allowed_card["cardName"] = "Kartu atm mandiri"
    allowed_card["cardType"] = "card_atm"
    allowed_card["isTwoStepAuth"] = "true"
    allowed_card["cardBannedStatus"] = "false"
    return allowed_card

# HTTP REQUEST WRAPPER


def httpRequest(url, body: None, method):
    with requests.Session() as client:
        if method == "POST":
            if body != None:
                resp = client.post(f'{url}', json=body, cookies=ADMIN_AUTH)
                resptime = round(float(resp.elapsed.total_seconds()), 3)*1000
                # print(resp.json(), f"{resptime}ms")
                print("[HTTP]", resp)
                logger.info(f"[HTTP] - {resp.json()}, f'{resptime}ms'")
                return resp

        if method == "GET":
            if body != None:
                resp = client.get(f'{url}', json=body)
                return resp
            if body == None:
                resp = client.get(f'{url}')
                return resp


loop_index = 0
while loop_index < TESTING_COUNT:
    # START REQUEST TO SERVER WITH RANDOM ACTION
    action = ACTION_LIST[0]

    # If the loop index is divisible by 3
    if loop_index % 3 == 0 and loop_index != 0:
        action = ACTION_LIST[2]

    # If the loop index is divisible by 5
    if loop_index % 5 == 0 and loop_index != 0:
        action = ACTION_LIST[1]

    print(action)

    # IF ADD CARD
    if (action == ACTION_LIST[0]):
        # DO REQUEST TO SERVER AFTER GET RANDOM DATA,
        randomData = addCardAction()
        body = [addCardAction() for _ in range(THREAD_SIZE)]
        with ThreadPoolExecutor(THREAD_SIZE) as executor:
            executor.map(httpRequest, [ADD_CARD_URL] *
                         THREAD_SIZE, body, ["POST"] * THREAD_SIZE)
            executor.shutdown(wait=True)

    # IF DELETE CARD
    if (action == "REMOVE_CARD"):
        # IF ALLOWED CARD EQUALS 0, ADD 1 TO LOOP INDEX
        if (len(ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID) == 0):
            loop_index += 1
            continue
        # DO FIND RANDOM CARD NUMBER FROM THE ARRAY, REMOVE THAT CARD FROM ARRAY, SEND REQUEST TO SERVER
        body = [removeCardAction() for _ in range(THREAD_SIZE)]
        with ThreadPoolExecutor(THREAD_SIZE) as executor:
            executor.map(httpRequest, [REMOVE_CARD_URL] *
                         THREAD_SIZE, body, ["POST"] * THREAD_SIZE)
            executor.shutdown(wait=True)

    # IF MODIFY CARD
    if (action == ACTION_LIST[2]):
        # IF ALLOWED CARD EQUALS 0, ADD 1 TO LOOP INDEX
        if (len(ALLOWED_CARD_BASE_ON_DATA_SOURCE_ID) == 0):
            loop_index += 1
            continue
        # DO FIND RANDOM CARD NUMBER FROM THE ARRAY, SEND REQUEST TO SERVER TO MODIFY CARD
        body = [modifyCardAction() for _ in range(THREAD_SIZE)]
        urls = [f"{EDIT_CARD_URL}{data['cardNumber']}" for i,
                data in enumerate(body)]

        # f"{EDIT_CARD_URL}{modifyCardAction()[1]}" for _ in range(THREAD_SIZE)]
        with ThreadPoolExecutor(THREAD_SIZE) as executor:
            executor.map(httpRequest, urls, body, ["POST"] * THREAD_SIZE)
            executor.shutdown(wait=True)

        # print(editableData)
        # print("modify card", allowed_card_id, allowed_card)

    loop_index += 1
    LAST_ACTION = action
    time.sleep(TESTING_INTERVAL * 60)

exit()
# print(ALLOWED_CARD)
