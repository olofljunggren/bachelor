import pika
import time

def get_input(prompt):
    return input(prompt)

def connect_to_server(host):
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        except Exception:
            print("Cannot connect...")
            time.sleep(5)
    return connection

def callback(ch, method, properties, body):
    print(f"Received message: {body.decode()}")

def consume_latest_message(channel, queue):
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue=queue, on_message_callback=callback, auto_ack=True)
    print("Waiting for messages...")

def main():
    host = get_input("Enter the RabbitMQ server host: ")
    connection = connect_to_server(host)
    channel = connection.channel()

    queue = get_input("Enter the queue name: ")
    channel.queue_declare(queue=queue)

    consume_latest_message(channel, queue)

    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Stopped listening for messages.")
        channel.stop_consuming()
        connection.close()

if __name__ == '__main__':
    main()
