from datetime import datetime
import json
import os
from pathlib import Path, PosixPath
import socket

import keyring
from outagedetector import log_f
from outagedetector import pushnotification as push
from outagedetector import send_mail as mail
import keyring.backend
from keyrings.alt.file import PlaintextKeyring

def ping_status(ip):
    import subprocess
    import re
    ip = 'google.com'
    ping_process = subprocess.Popen(["ping", "-c", "1", ip], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    ping_msg = str(ping_process.stdout.read())
    ONLINE = "online"
    OUTAGE = "outage"
    UNREACHABLE = "network unreachable"

    if re.search(r'100.0% packet loss|100% packet loss', ping_msg) != None:
        status = OUTAGE
    elif re.search(r'Network is unreachable', ping_msg) != None:
        status = UNREACHABLE
    else:
        status = ONLINE
    match = re.search(r'\/\d{2,4}\.\d{3}\/', ping_msg)
    if match is not None:
        ping_time = float(match.group(0).replace("/", ''))
    else:
        ping_time = None
    result = dict(status=status, ping_time=ping_time)
    return result

def check_internet_connection():
    try:
        sock = socket.create_connection(("www.google.com", 80))    # if connection to google fails, we assume internet is down
        sock.close()
        return True
    except OSError:
        pass
    return False


# if power is on, script will run even if internet is down, therefore we only take into account the power timestamp
# from the last run in determining the periodicity of the script runs
def extract_run_periodicity(scheduled_now, last_scheduled, current_time, last_power_time, last_period):
    if scheduled_now == "scheduled" and last_scheduled == "scheduled":
        return int((current_time - last_power_time).total_seconds() / 60)
    else:
        return last_period



def check_power_and_internet(run, notification):
    if run == "boot":
        just_booted = True
    elif run == "scheduled":
        just_booted = False
    if notification == "notification" or notification == "ifttt":
        send_notification = True
        ifttt_notification = False
    elif notification == "mail":
        send_notification = False
        ifttt_notification = False
    if notification == "ifttt":
        ifttt_notification = True

    config_path = os.path.join(os.path.expanduser("~"), ".config/outagedetector")
    address_available = False
    address = ""
    timestamp_format = "%d-%m-%Y %H-%M-%S"
    hour_minute_format = "%H:%M"

    #internet_connected = check_internet_connection()
    result = ping_status('google.com')
    if result['status'] == 'online':
        internet_connected = True
    else:
        internet_connected = False
    ping_time = result['ping_time']
    if not send_notification:
        try:
            with open(os.path.join(config_path, "config.json")) as json_file:
                mail_json = json.load(json_file)
                sender = mail_json["sender"]
                receivers = mail_json["receivers"]
                smtp_server = mail_json["smtp_server"]
                keyring.set_keyring(PlaintextKeyring())
                password = keyring.get_password("Mail-OutageDetector", sender)
                if password is None:
                    print("Mail password not found, try running initial configuration again!")
                    exit(1)
                address = mail_json["house_address"]
        except FileNotFoundError:
            print("Mail will not be sent, there is no config file in the folder.")
        except KeyError:
            print("Config.json file doesn't have all fields (sender, receivers, smtp_server, house address")
    else:
        if not ifttt_notification:
            keyring.set_keyring(PlaintextKeyring())
            push_key = keyring.get_password("PushBullet-OutageDetector", "pushbullet")
            try:
                with open(os.path.join(config_path, "config.json")) as json_file:
                    notification_json = json.load(json_file)
                    address = notification_json["house_address"]
            except FileNotFoundError:
                print("Configuration file does not exist, try running the initial configuration again!")
            except KeyError:
                print("Config.json file doesn't have all fields, try running the initial configuration again!")
        else:
            try:
                with open(os.path.join(config_path, "config.json")) as json_file:
                    notification_json = json.load(json_file)
                    ifttt_name = notification_json["ifttt_event"]
                    address = notification_json["house_address"]
            except FileNotFoundError:
                print("Configuration file does not exist, try running the initial configuration again!")
            except KeyError:
                print("Config.json file doesn't have all fields, try running the initial configuration again!")
            keyring.set_keyring(PlaintextKeyring())
            api_key = keyring.get_password("IFTTT-OutageDetector", ifttt_name)

    if address:
        address_available = True

    current_timestamp = datetime.now()
    current_timestring = datetime.strftime(current_timestamp, timestamp_format)
    current_hour_min = datetime.strftime(current_timestamp, hour_minute_format)

    try:
        with open(os.path.join(config_path, "last_timestamp.txt")) as file:
            read_string = file.read()
    except FileNotFoundError:
        read_string = ""

    file_data = read_string.split(",")

    try:
        last_power_timestring = file_data[0]
        last_internet_timestring = file_data[1]
        last_argument = file_data[2]
        last_periodicity = int(file_data[3])
    except IndexError:
        last_power_timestring = current_timestring
        last_internet_timestring = current_timestring
        last_argument = "N/A"
        last_periodicity = 0

    last_power_timestamp = datetime.strptime(last_power_timestring, timestamp_format)

    periodicity = extract_run_periodicity(run,
                                          last_argument,
                                          current_timestamp,
                                          last_power_timestamp,
                                          last_periodicity)

    with open(os.path.join(config_path, "last_timestamp.txt"), 'w+') as file:
        if internet_connected:
            file.write("{},{},{},{}".format(current_timestring, current_timestring, run, periodicity))
        else:
            file.write("{},{},{},{}".format(current_timestring, last_internet_timestring, run, periodicity))

    if internet_connected:
        if just_booted:
            power_outage_time = int((current_timestamp - last_power_timestamp).total_seconds() / 60)
            if periodicity > 0:
                min_outage_time = max(range(0, power_outage_time + 1, periodicity))
            else:
                min_outage_time = 0
            notification = "Power was out for {} to {} minutes at {}.".format(min_outage_time, power_outage_time,
                                                                              current_hour_min)
            if address_available:
                notification += " Address: {}.".format(address)
            print("Power was out for {} to {} minutes at {}".format(min_outage_time, power_outage_time,
                                                                    current_timestring))
            if send_notification:
                if ifttt_notification:
                    push.push_to_ifttt(ifttt_name, api_key, notification)
                else:
                    push.push_to_iOS("Power outage", notification, push_key)
            else:
                mail.send_mail(sender, receivers, "Power outage", notification, smtp_server, password)

        if not last_power_timestring == last_internet_timestring:
            last_internet_timestamp = datetime.strptime(last_internet_timestring, timestamp_format)
            internet_downtime = int((current_timestamp - last_internet_timestamp).total_seconds() / 60)
            if periodicity > 0:
                min_outage_time = max(range(0, internet_downtime + 1, periodicity))
            else:
                min_outage_time = 0
            print("Internet was down for {} to {} minutes at {}".format(min_outage_time, internet_downtime,
                                                                        current_timestring))
            notification = "Internet has been down for {} to {} minutes at {}.".format(min_outage_time,
                                                                                       internet_downtime,
                                                                                       current_hour_min)
            if address_available:
                notification += " Address: {}.".format(address)
            if send_notification:
                if ifttt_notification:
                    push.push_to_ifttt(ifttt_name, api_key, notification)
                else:
                    push.push_to_iOS("Internet down", notification, push_key)
            else:
                mail.send_mail(sender, receivers, "Internet down", notification, smtp_server, password)

    print("Script has run at {}. Internet connected: {}. Just booted: {}. Ping Time: {}".format(current_timestring,
                                                                                  internet_connected,
                                                                                  just_booted, ping_time))
    log_f.separate_log_file(current_timestamp, internet_connected, just_booted, ping_time)
