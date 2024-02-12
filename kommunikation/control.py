import pika
import json
import subprocess
import time
from utils import *
import json
from filelock import FileLock, Timeout
import os
import sys
import signal

SCRIPT_MANAGER = {
    "spi_com" : None,
    "main": None
}

connection = ""
com_message_channel = ""

# Check runnings scripts and send the info to the GUI
def check_running_processes():
    queue_name = 'running_scripts'

    is_running_list = ["Control"]

    for index, script in enumerate(SCRIPT_MANAGER.keys()):
        if not SCRIPT_MANAGER[script] == None:
            if SCRIPT_MANAGER[script].poll() == None:
                is_running_list.append(script)

    is_running_list = json.dumps(is_running_list)
    send_message(queue_name, is_running_list)

# Establish a connection to PIKA
# (This function already exists in untils, should be removed)
def connect_to_server(host):
    connection = None
    while not connection:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=host))
        except Exception:
            print("Cannot connect...")
            time.sleep(5)
    return connection

# Listen to commands from the GUI
def callback(ch, method, properties, body):
        # parse the message as a JSON object
        global com_message_channel
        global connection

        data = body.decode()

        if ":" in data:
            message = body.decode().split(":")
            script_name = message[0]
            action = message[1]

            # determine the path to the script based on its name
            script_path = f'/home/admin/Dokument/communication-module/{script_name}.py'

            #/home/admin/control.py
                
            # if the action is "on", execute the script
            if action == 'on':
                filename = f'error_{script_name}.txt'
                command = ["python3", script_path]


                sub = subprocess.Popen(command, start_new_session=True)
                SCRIPT_MANAGER[script_name] = sub

                message = "Startar " + str(script_name)
                send_message("com_message", message, connection, com_message_channel)
            
            elif action == 'off':
                os.killpg(os.getpgid(SCRIPT_MANAGER[script_name].pid), signal.SIGTERM)

                if script_name == "main":
                    script_path = f'/home/admin/Dokument/communication-module/stop_lidar.py'
                    subprocess.Popen(["python3", script_path], start_new_session=True)
                
                message = "Stoppar " + str(script_name)
                send_message("com_message", message, connection, com_message_channel)

        elif (data == "getRunningStatus"):
            check_running_processes()
        elif (data == "mapCones"):
            script_path = f'/home/admin/Dokument/communication-module/map_cones.py'
            subprocess.Popen(["python3", script_path], start_new_session=True)
        elif (data == "calculateRoute"):
            script_path = f'/home/admin/Dokument/communication-module/bezier.py'
            subprocess.Popen(["python3", script_path], start_new_session=True)
        elif (data == "exit"):
            send_message("com_message", "Stoppar alla skript", connection, com_message_channel)
            scripts_to_kill = ["spi_com", "main", "position_receiver", "lidar_receiver"]
            for script_to_kill in scripts_to_kill:
                kill_scripts_containing(script_to_kill)
            script_path = f'/home/admin/Dokument/communication-module/stop_lidar.py'
            subprocess.Popen(["python3", script_path], start_new_session=True)
            sys.exit()

def main():
    global connection

    # Connect to the RabbitMQ server
    connection = connect_to_server('localhost')
    channel = connection.channel()

    # declare the queue we'll be listening to
    channel.queue_declare(queue='script_handle')

    # define a callback function to handle incoming messages
    global com_message_channel
    com_message_channel = create_channel(connection, "com_message")

    send_message("com_message", "Startar kontrollskriptet", connection, com_message_channel)

    # Stop all other scripts
    scripts_to_kill = ["spi_com", "main", "position_receiver", "lidar_receiver"]
    for script_to_kill in scripts_to_kill:
        kill_scripts_containing(script_to_kill)

    # start listening for messages
    channel.basic_consume(queue='script_handle', on_message_callback=callback, auto_ack=True)
    channel.start_consuming()

if __name__ == '__main__':
    script_name = os.path.basename(sys.argv[0])
    lock_file = f"{script_name}.lock"
    lock = FileLock(lock_file, timeout=1)
    try:
        with lock:
            main()
    except Timeout:
        print(f"Another instance of {script_name} is already running. Exiting...")
        sys.exit(1)
