import spidev
import time
import pika
import threading
import queue
from utils import *
import single_instance_with_monitor
import json
import csv

# Set up SPI
spi = spidev.SpiDev()
spi.open(0, 0)  # SPI bus 0, device (slave) 0 (SS0)
spi.max_speed_hz = 4000000  # 4 MHz clock speed

spi_lock = threading.Lock()
spi_queue = queue.Queue()

def connect_to_server(host):
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        except Exception:
            print("Cannot connect...")
            time.sleep(5)
    return connection

# Listen to messages sent to the 'send_spi' queue
# and transfer them to SPI
def callback(ch, method, properties, body):
    #print(body.decode())
    message = process_hex_string(body.decode())
    send_signal(message)

def message_listner(channel_send):
    queue_name_send = 'send_spi'
    channel_send.basic_consume(queue=queue_name_send, on_message_callback=callback, auto_ack=True)
    channel_send.start_consuming()
    channel_send.queue_purge(queue_name_send)

# Set up and initiate varibles and connections
def main():
    # From odometer 
    connection_receive = connect_to_server("localhost")
    channel_receive = connection_receive.channel()
    queue_name_receive = 'received_spi'
    channel_receive.queue_declare(queue=queue_name_receive)
    
    # From car to spi
    connection_send_to_spi = connect_to_server("localhost")
    channel_send_to_spi = connection_send_to_spi.channel()
    queue_name_send_to_spi = 'send_spi'
    channel_send_to_spi.queue_declare(queue=queue_name_send_to_spi)

    T = threading.Thread(target=spi_listner, args=(channel_receive, connection_receive)) 
    T.start()
    
    T2 = threading.Thread(target=message_listner, args=(channel_send_to_spi,))
    T2.start()

# Takes in a signal
# Initiates a SPI access lock to prevent race condtions
# Sends the signal to the control module
def send_signal(signal):
    acquired = spi_lock.acquire(blocking=False)
    if acquired:
        try:
            #print("sending")
            #print(signal)
            spi.xfer(signal, len(signal))
        finally:
            spi_lock.release()
    else:
        spi_queue.put(signal)

# Send out SPI signals built up during sending phase
def process_spi_queue():
    while not spi_queue.empty():
        signal = spi_queue.get()
        spi.xfer(signal, len(signal))

# Get odometer value from sensor module at specific frequency
def spi_listner(channel_receive, connection):
    freq = 10
    while True:
        with spi_lock:
            spi.open(0, 1)
            received_signal = spi.xfer([0, 0, 0], 3)
            str_signal = [format(sig, '#x') for sig in received_signal]
            send_message("internal_odometer_signal", json.dumps(str_signal), connection, channel_receive)
            spi.open(0, 0)
        process_spi_queue()
        time.sleep(1/freq)


if __name__ == '__main__':
    single_instance_with_monitor.run_with_lock_and_monitor(main)