from utils import *
import subprocess

def main():
    scripts_to_kill = ["control", "spi_com", "main", "position_receiver", "lidar_receiver"]
    for script_to_kill in scripts_to_kill:
        kill_scripts_containing(script_to_kill)
    script_path = f'/home/admin/Dokument/communication-module/stop_lidar.py'
    subprocess.Popen(["python3", script_path], start_new_session=True)


if __name__ == '__main__':
    main()