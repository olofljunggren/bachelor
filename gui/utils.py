
import pika
import time
import os
import platform
import re
import paramiko
from queue import Queue
from threading import Thread
import socket
from pika.exceptions import AMQPConnectionError

def decode_script_status(body):
    # parse the message as a JSON object
    print("status nu")
    is_running_list = [0,0,0,0]
    message = body.split(":")
    for index, is_running in enumerate(message):
        is_running_list[index] = bool(is_running)

    return is_running_list

import time

# Takes in the name of a queue and purges it if it exists
def purge_queue(connection, queue_name):

    if not check_connection(connection):
        connection["connection"], connection["failed"] = connect_to_server(connection["ip"])

    if not queue_name in connection["channels"].keys():
        connection["channels"][queue_name] = connection["connection"].channel()

    channel = connection["channels"][queue_name]

    if not channel.is_open:
        connection["channels"][queue_name] = connection["connection"].channel()
        channel = connection["channels"][queue_name]
        channel.queue_declare(queue_name)

    channel.queue_purge(queue_name)

# Get the next message in a message queue
def get_next_message(connection, queue_name):
    retries = 2
    message = None

    while retries > 0:
        try:
            if connection["failed"]:
                return None

            if not check_connection(connection):
                connection["connection"], connection["failed"] = connect_to_server(connection["ip"])

            if not queue_name in connection["channels"].keys():
                connection["channels"][queue_name] = connection["connection"].channel() 

            channel = connection["channels"][queue_name]

            if not channel.is_open:
                connection["channels"][queue_name] = connection["connection"].channel()
                channel = connection["channels"][queue_name]
                channel.queue_declare(queue_name)
            try:
                method_frame, _, body = channel.basic_get(queue_name, auto_ack=True)
                if method_frame and (not method_frame is None):
                    message = body.decode()
                else:
                    break
            except Exception:
                pass

        except pika.exceptions.StreamLostError as e:
            print("StreamLostError, retrying...")
            retries -= 1
            time.sleep(1)  # Wait for a second before retrying

            # Reestablish the connection
            connection["failed"] = True
            connection["connection"], connection["failed"] = connect_to_server(connection["ip"])
        finally:
            retries -= 1
            
    return message

# Get the latest message in a message queue (removes all remaining messages)
def get_latest_message(connection, queue_name):
    retries = 2
    latest_message = None

    while retries > 0:
        try:
            if connection["failed"]:
                return None

            if not check_connection(connection):
                connection["connection"], connection["failed"] = connect_to_server(connection["ip"])

            if not queue_name in connection["channels"].keys():
                connection["channels"][queue_name] = connection["connection"].channel() 

            channel = connection["channels"][queue_name]

            if (not channel.is_open) and (not connection["connection"] is None):
                connection["channels"][queue_name] = connection["connection"].channel()
                channel = connection["channels"][queue_name]
                channel.queue_declare(queue_name)
            try:
                 while True:
                    method_frame, _, body = channel.basic_get(queue_name, auto_ack=True)
                    if method_frame and (not method_frame is None):
                        latest_message = body.decode()
                    else:
                        break
            except Exception:
                pass

            #channel.queue_purge(queue_name)

        except pika.exceptions.StreamLostError as e:
            print("StreamLostError, retrying...")
            retries -= 1
            time.sleep(1)  # Wait for a second before retrying

            # Reestablish the connection
            connection["failed"] = True
            connection["connection"], connection["failed"] = connect_to_server(connection["ip"])
        finally:
            retries -= 1
            
    return latest_message

# Esablish and return a pika connection
def connect_to_server(hostname):
    connection = None
    if not hostname == "0.1":
        try:
            credentials = pika.PlainCredentials('test', 'test')
            parameters = pika.ConnectionParameters(hostname,
                                        5672,
                                        '/',
                                        credentials,
                                        socket_timeout=1,
                                        connection_attempts=2, # Set the number of connection attempts
                                        retry_delay=0.5, # Time in seconds between retries
                                        blocked_connection_timeout=1) # Time to wait before raising an exception if the connection is blocked
            connection = pika.BlockingConnection(parameters)
        except (AMQPConnectionError, Exception) as e:
            print(f"Failed to connect: {e}")
            return connection, True
        return connection, False
    else:
        return connection, True

# Check if an instance of a pika connection is still alive
def check_connection(connection):
    return hasattr(connection["connection"], 'is_open') and connection["connection"].is_open

# Send a message over a queue
def send_message(connection, queuename, message):
    retries = 3
    while retries > 0:
        try:
            if connection["failed"]:
                return
            
            if not check_connection(connection):
                connection["connection"], connection["failed"] = connect_to_server(connection["ip"])
            
            if not queuename in connection["channels"].keys():
                connection["channels"][queuename] = connection["connection"].channel()

            if not connection["channels"][queuename].is_open:
                connection["channels"][queuename] = connection["connection"].channel()

            connection["channels"][queuename].queue_declare(queue=queuename)
            connection["channels"][queuename].basic_publish(exchange='', routing_key=queuename, body=message)
            break

        except pika.exceptions.StreamLostError as e:
            print("StreamLostError, retrying...")
            retries -= 1
            time.sleep(1)  # Wait for a second before retrying
            
            # Reestablish the connection
            connection["failed"] = True
            connection["connection"], connection["failed"] = connect_to_server(connection["ip"])

# Get the IP address of the car
def get_communcation_module_ip():
    try:
        return socket.gethostbyname("gruppsexpi.wlan")
    except Exception:
        return "0.1"

# Establish an SSH connection to a device
def ssh_connect(hostname, port, username, password):
    ssh_client = paramiko.SSHClient()
    ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh_client.load_system_host_keys()

    try:
        ssh_client.connect(hostname, port, username, password)
        print(f"Connected to {hostname}")
    except Exception as e:
        print(f"Failed to connect to {hostname}: {e}")
        ssh_client = None

    return ssh_client

# Open a file on a remote device given a paramiko SSH connection
"""
def open_remote_python_file(ssh_client, remote_file_path):
    try:
        command = f"nohup python3 {remote_file_path} > ./output.log 2>&1 &"
        ssh_client.exec_command(command)
    except Exception as e:
        print(f"Failed to open remote file: {e}")
"""

"""
def open_remote_python_file(ssh_client, remote_file_path):
    try:
        session_name = "control_session"
        #command = f"screen -dmS {session_name} python3 {remote_file_path} > ./output.log 2>&1"
        #command = f"screen -dmS {session_name} python3 {remote_file_path}"
        command = f"ulimit -n 4096; screen -dmS {session_name} python3 {remote_file_path}"
        #print(command)
        ssh_client.exec_command(command)
    except Exception as e:
        print(f"Failed to open remote file: {e}")
"""


def open_remote_python_file(ssh_client, directory, file_name):
    try:
        session_name = "my_session"
        command = f"sudo /etc/init.d/screen-cleanup start; cd {directory}; screen -dmS {session_name} python3 {file_name}"
        
        shell = ssh_client.invoke_shell()
        #shell.send(f'{command}\n')
        shell.send(f'{command}\nexit\n')

        time.sleep(2)
        
        # Print the shell output
        while not shell.recv_ready():
            time.sleep(1)
        output = shell.recv(1000)
        print(output.decode())

    except Exception as e:
        print(f"Failed to open remote file: {e}")



def position_listner(channel_send):
    queue_name_send = 'position_data'
    channel_send.basic_consume(queue=queue_name_send, on_message_callback=callback_pos, auto_ack=True)
    channel_send.start_consuming()
    channel_send.queue_purge(queue_name_send)


def speed_listner(channel_send):
    queue_name_send = 'speed_data'
    channel_send.basic_consume(queue=queue_name_send, on_message_callback=callback_speed, auto_ack=True)
    channel_send.start_consuming()
    channel_send.queue_purge(queue_name_send)

