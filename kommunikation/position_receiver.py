import asyncio
import xml.etree.ElementTree as ET
import pkg_resources
import time
from utils import *
import json
import os
import csv
import logging
import sys
import qtm

IP = "192.168.0.50"

DATA_DIR = "data/input"
POS_FILE = "untitled.csv"

isRecording = False
pos_list = []
connection = ""
threshold = 0
counter = 0

pos_capture_channel = ""
internal_position_channel = ""
com_message_channel = ""

def create_body_index(xml_string):
    """ Extract a name to index dictionary from 6dof settings xml """
    xml = ET.fromstring(xml_string)

    body_to_index = {}
    for index, body in enumerate(xml.findall("*/Body/Name")):
        body_to_index[body.text.strip()] = index

    return body_to_index

def body_enabled_count(xml_string):
    xml = ET.fromstring(xml_string)
    return sum(enabled.text == "true" for enabled in xml.findall("*/Body/Enabled"))

async def setup():

    """
    Initializes global variables, connects to the server, creates channels for communication,
    and starts streaming frames with 6DOF data. Processes and records position data if required.
    """

    global connection
    connection = connect_to_server("localhost")

    global com_message_channel
    com_message_channel = create_channel(connection, "com_message")

    global pos_capture_channel
    global internal_position_channel

    pos_capture_channel = create_channel(connection, "pos_capture")
    internal_position_channel = create_channel(connection, "internal_position")

    connection = await qtm.connect(IP)
    if connection is None:
        return
    
    send_message("com_message", "Redo att ta emot positionsdata", connection, com_message_channel)

    # Get 6dof settings from qtm
    xml_string = await connection.get_parameters(parameters=["6d"])
    body_index = create_body_index(xml_string)
    #print(body_index)

    wanted_body = "racecar"

    def on_packet(packet):

        """
        Process received packet, extract body position and rotation,
        check for start/stop recording commands, and store or send
        position data accordingly.
        """

        global isRecording
        global pos_list
        global DATA_DIR
        global POS_FILE

        info, bodies = packet.get_6d_euler()

        if wanted_body is not None and wanted_body in body_index:
            # Extract one specific body
            wanted_index = body_index[wanted_body]

            global isRecording
            global pos_list
            global connection
            global DATA_DIR
            global POS_FILE
            global threshold
            global counter

            global pos_capture_channel
            global internal_position_channel
            global com_message_channel

            position, rotation = bodies[wanted_index]
            x = position[0]
            y = position[1]
            a3 = rotation[2]

            if (x != "NaN") and (y != "NaN") and (a3 != "NaN"):
                try:
                    Y = int(x)
                    X = -int(y)
                    ANGLE = int(a3)  + 90

                    #print(f"Mottagen pos: {X}, {Y}, vinkel {ANGLE}")

                    if 180 < ANGLE < 270:
                        ANGLE -= 360
                except Exception as e:
                    X   = "NaN"
                    Y = "NaN"
                    ANGLE = "NaN"

            message = None
            if counter > threshold:
                message = get_latest_message("pos_capture", connection, pos_capture_channel)

            if not message is None:
                data_capture = json.loads(message)
                if data_capture["action"] == "start":
                    POS_FILE = data_capture[ "id"] + "_pos" + ".csv"
                    isRecording = True
                    send_message("com_message", f'Spelar in till {POS_FILE}', connection, com_message_channel)
                elif data_capture["action"] == "stop":
                    isRecording = False
                    send_message("com_message", "Slutar spela in positionsdata", connection, com_message_channel)

            if (isRecording):
                pos_list.append([X, Y, ANGLE, str(time.time())])
            elif pos_list:
                os.makedirs(DATA_DIR, exist_ok=True)
                with open(os.path.join(DATA_DIR, POS_FILE), 'a', newline='') as csvfile:
                    csv_writer = csv.writer(csvfile)
                    csv_writer.writerows(pos_list)
                pos_list = []
                

            data = json.dumps({"X": X, "Y": Y, "ANGLE": ANGLE})

            if counter > threshold:
                send_message("internal_position", data, connection, internal_position_channel)
                counter = 0

            counter += 1

    # Start streaming frames
    await connection.stream_frames(components=["6deuler"], on_packet=on_packet)


if __name__ == "__main__":
    asyncio.ensure_future(setup())
    asyncio.get_event_loop().run_forever()