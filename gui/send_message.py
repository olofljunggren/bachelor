import pika
import time
import socket

def connect_to_server(hostname):
    connection = None
    while not connection:
        try:
            credentials = pika.PlainCredentials('test', 'test')
            parameters = pika.ConnectionParameters(hostname,
                                       5672,
                                       '/',
                                       credentials)
            connection = pika.BlockingConnection(parameters)
        except Exception:
            print("Cannot connect...")
            time.sleep(5)
    return connection


def send_message(channel, queuename, message):
    channel.queue_declare(queue=queuename)
    channel.basic_publish(exchange='', routing_key=queuename, body=message)

def main():
    host = input("RabbitMQ server (def 192.168.5.5): ")
    if host=="":
        host = "192.168.5.3"
    connection = connect_to_server(host)
    channel = connection.channel()

    queue = input("Enter the queue name: ")

    while True:
        message = input("Enter the message (eg 0x01)): ")
        print(f"Sent message: {message}")
        send_message(channel, queue, message)

if __name__ == '__main__':
    main()
