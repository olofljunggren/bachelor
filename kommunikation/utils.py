import pika
import ast
import logging
import socket
import psutil

# Takes in a list of full or partial names of python processes
# Kills the processes if they are running
def kill_scripts_containing(substring):
    PID = []
    for proc in psutil.process_iter():
        try:
            if proc.name() == "python3":
                path = proc.cmdline()[1]
                filename = None
                if ("/" in path):
                    filename = path.split("/")[-1]
                else:
                    filename = path
                if (filename is not None) and (substring in filename):
                    PID.append(proc.pid)
                    proc.kill()
        except:
            pass
    return PID

# A function to check if there is a connection to a particular wifi using ssid
def is_connected_to_wifi(wifi_name):
    try:
        for conn in psutil.net_connections(kind='inet'):
            if conn.family == socket.AF_INET and conn.type == socket.SOCK_DGRAM and conn.laddr.port == 68:
                interface = conn.laddr.ip
                break
        else:
            return False

        for nic, addrs in psutil.net_if_addrs().items():
            for addr in addrs:
                if addr.family == socket.AF_INET and addr.address == interface:
                    return psutil.net_if_stats()[nic].ssid == wifi_name
        else:
            return False
    except AttributeError:
        return False

# A function to convert a list of hex values or strings in hex form and converts it to a list of ints
def process_hex_string(input_str):
    try:
        # Check if the input string is a hex value
        if input_str.startswith("0x"):
            return [int(input_str, 0)]  # Return as a list with a single value
        else:
            # Evaluate the string as a list of hex values
            hex_list = ast.literal_eval(input_str)
            if isinstance(hex_list, list) and all(isinstance(x, int) for x in hex_list):
                return hex_list
            else:
                raise ValueError("Invalid input format. Please provide a hex value or a list of hex values.")
    except (SyntaxError, ValueError) as e:
        raise ValueError("Invalid input format. Please provide a hex value or a list of hex values.") from e

def connect_to_server(host):
    connection = None
    logger = logging.getLogger('pika')
    logger.setLevel(logging.ERROR)
    try:
        connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
    except Exception:
        print("Cannot connect...")
    return connection

def purge_queue(queuename):
    connection = connect_to_server("localhost")
    channel = connection.channel()
    channel.queue_declare(queue=queuename)
    channel.queue_purge(queuename)

def create_channel(connection, queuename):
    connection = connect_to_server("localhost")
    channel = connection.channel()
    channel.queue_declare(queue=queuename)
    return channel

# Sends a message over a particular channel and connection
# Has option to pass a connection and channel to prevent creation of too many channels
# A connection and channel will be created if none is provided
def send_message(queuename, message, connection="", channel=""):

    logger = logging.getLogger('pika')
    logger.setLevel(logging.ERROR)

    if connection == "":
        connection = connect_to_server("localhost")

    if channel == "":
        channel = connection.channel()
        channel.queue_declare(queue=queuename)
    try:
        channel.basic_publish(exchange='', routing_key=queuename, body=message)
    except:
        print(f"send_message misslyckades med queuename {queuename} och message {message}")

# Get the latest message in a pika queue
# Has option to pass a connection and channel to prevent creation of too many channels
# A connection and channel will be created if none is provided
def get_latest_message(queue_name, connection="", channel=""):

    logger = logging.getLogger('pika')
    logger.setLevel(logging.ERROR)

    if connection == "":
        connection = connect_to_server("localhost")

    latest_message = None

    if channel == "":
        channel = connection.channel()
        channel.queue_declare(queue_name)

    while True:
        method_frame, _, body = channel.basic_get(queue_name, auto_ack=True)
        if method_frame and (not method_frame is None):
            latest_message = body.decode()
        else:
            break

    return latest_message

# Takes an int value and divides it into two bytes in hex string format
def convert_int_to_two_bytes(data, max = 32767):
        first_byte = "0x00"
        second_byte = "0x00"
        
        if int(data,16) > max:
            return 

        value = data.split('x')[1]

        if len(value) >= 1:
            first_byte = "0x0" + value[-1]
        if len(value) >= 2:
            first_byte = "0x" + value[-2] + value[-1]
        if len(value) >= 3:
            second_byte = "0x0" + value[-3] 
        if len(value) >= 4:
            second_byte = "0x" + value[-4] + value[-3]
        if data[0] == '-':
            second_byte = second_byte[2] + second_byte[3]
            second_byte = hex(int(second_byte,16)+128)

        return first_byte, second_byte