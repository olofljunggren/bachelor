import sys
import os
from filelock import FileLock, Timeout
import psutil
import threading
import signal
import time

control_py_running = True
control_py_not_running = threading.Event()

def get_running_python_scripts():
    filenames = []
    for proc in psutil.process_iter():
        try:
            if proc.name() == "python3":
                path = proc.cmdline()[1]
                if ("/" in path):
                    filenames.append(path.split("/")[-1])
                else:
                    filenames.append(path)
                
        except:
            pass
    return filenames

# If control.py is running AND another instance of the same channel is running, clost this script
def monitor_scripts():
    global control_py_running
    script_name = os.path.basename(sys.argv[0])
    while control_py_running:
        running_scripts = get_running_python_scripts()
        if "control.py" not in running_scripts:
            control_py_running = False
            control_py_not_running.set()
            parent_pid = os.getppid()
            os.killpg(parent_pid, signal.SIGTERM)
            sys.exit()
        time.sleep(1)

# Setup and initiate.
# If control.py is not running, close this script
def run_with_lock_and_monitor(main_func):
    global control_py_running

    # Start the monitoring thread
    monitor_thread = threading.Thread(target=monitor_scripts)
    monitor_thread.setDaemon(True)
    monitor_thread.start()

    running_scripts = get_running_python_scripts()
    script_name = os.path.basename(sys.argv[0])
    
    # Start the main function thread
    if ("control.py" in running_scripts) and \
            (running_scripts.count(script_name) < 2):
        main_func_thread = threading.Thread(target=main_func)
        main_func_thread.setDaemon(True)
        main_func_thread.start()

        try:
            control_py_not_running.wait()
            control_py_running = False
            main_func_thread.join()
        finally:
            monitor_thread.join()
            sys.exit(1)
    else:
        sys.exit(1)
