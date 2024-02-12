# communcation-module


## QUEUES

| Queue       | Format      | Description   |
| :---        |    :----:   |          ---: |
| running_scripts      | "[script1, script2, ...]"       | List of runnings scripts   |
| script_handle   | script_name:action, (action = on/off)        | Turns scripts on com.mod on or off |
| send_spi      | "[{id}{nr. bytes}, {data byte 1}, {data byte 2}]"       | SPI signal to control module (values in hex)   |
| mode_queue  | autonomous/manual      | Sets the mode of the car      |
| position_data | "x:y:angle:time"   | queue to update the car position on the GUI, in mm and degrees, time in sec |
| speed_data   | odometer_speed:requested_speed | update speed on GUI, type: int, mm/s |
| PID_queue   | KP_speed:KI_speed:KD_speed | set PID parameters |
| checkpoint_data   | steer_angle:distance_to_goal:angle_to_goal | update checkpoint info on GUI |
