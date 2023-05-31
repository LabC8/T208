#!/usr/bin/env python3
"""
Control script for Geekworm T208 UPS (https://wiki.geekworm.com/T208) for Jatson Nano.
Some functions were get from https://wiki.geekworm.com/T208-Software. Strongly recommended to read the webpage before using this script.
The script periodecly checks if the device is plugged to the mains, and it's battary capacity and voltage.
The script turns off power of Jetson when T208 battary capacity reaches setting low level and it lost a power outage.
Information about the state of device, if necessary, available by UDP.

Script needs the next modules, who install with pip3 (of course you have to install pip3 before):
pip3 install RPi.GPIO -- I hadn't to install this module, it had been installed on my Jetson Nano by default
sudo pip3 install smbus
pip3 install jsonschema
pip3 install tendo
"""

# Set Python3 as a default version: https://raspberry-valley.azurewebsites.net/Python-Default-Version/
# This script had got an x-attribut and was added into /etc/sudoers file with 'sudo visudo'
# sudo pip3 install smbus
# pip3 install jsonschema

import sys
import os
import logging
import time
import RPi.GPIO as GPIO
import struct
import socket
import json
import smbus
import jsonschema
from os import path
from enum import Enum, auto
from threading import Thread
from tendo import singleton
from typing import Union

SHOW_INFO = True
SLEEP_TIME = 5
CRITICAL_CAPACITY = 20
UDP_PORT = 7777
UDP_HOST = ''

GPIO_PORT = 4

I2C_ADDRESS = 0x36


# States of Power Loss Detection led
class PLDLedEnumClass (Enum):
    """PLDLedEnumClass -- Class defines state of Power Loss Detection (PLD) LED
    """
    off = 1
    """off -- T208 is plugged to the mains
    """
    red = 2
    """red -- T208 is not plugged to the mains
    """
    blink = 3
    """blink -- It is undocumented state of plugged T208.
    Happens occasionally, frequient after a power outage.
    Perhaps this is due to the fact that I use the Jetson Nano from the Yahboom manufacturer.
    """

class ReadT208ResultEnumClass (Enum):
    """CfgReadResultEnumClass -- Class defines the state of reading SMBus
    """
    is_correct = auto()
    """T208 returned a value
    """
    is_not_connected = auto()
    """Could not read from SMBus and was returned errno 121. It possible T208 doesn't connected
    """
    unknown = auto()
    """Something unusual happened.
    """


class CfgReadResultEnumClass (Enum):
    """CfgReadResultEnumClass -- Class defines the state of reading the file of configuration
    """
    is_exist = auto()
    """Configuration file exists and has a correct structure
    """
    is_not_exist = auto()
    """Configuration file doesn't exist
    """
    is_broken = auto()
    """Configuration file hasn't JSON structure
    """
    is_incorrect = auto()
    """Configuration fule doesn't correlate to JSON scheme
    """
    unknown = auto()
    """Something unusual happened.
    """


class Configuration:
    """ Configuration variables
    """
    ShowInfo : bool
    """ Flag of logging to the console
    """
    SleepTime : float
    """ Time of holding main control loop after reading information about T208
    """
    CriticalCapacity : float
    """ T208 UPS Low Battery Level
    """
    UdpPort : int
    """ Port of our UDP-server
    """
    UdpHost : str
    """ Address of our UDP-server
    """
    def __init__(self):
        """__init__ Initilize configuration varyables by default
        """
        self.ShowInfo = SHOW_INFO
        self.SleepTime = SLEEP_TIME
        self.CriticalCapacity = CRITICAL_CAPACITY
        self.UdpPort = UDP_PORT
        self.UdpHost = UDP_HOST


# global fullfilename
# """ Global variables of the configuration
# ShowInfo -- Flag of logging to the console
# SleepTime -- Time of holding main control loop after reading information about T208
# CriticalCapacity -- T208 UPS Low Battery Level
# UdpPort -- Port of the UDP-server
# UdpHost -- Address of the UDP-server
# """
# global ShowInfo, SleepTime, CriticalCapacity
# global UdpPort, UdpHost

global TheLogger


def read_config(config_path: str) -> Union[CfgReadResultEnumClass, str]:
    """read_config  -- Read initial settings. Configuration file has a name "PowerCtrl.cfg" and puts into directory, defined by argument "config_path"

    Arguments:
        config_path {string} -- Configuration file path

    Returns:
        Union[CfgReadResultEnumClass, str] -- Information about result of configuration reading in coded and text formats,
    """
    # global ShowInfo, SleepTime, CriticalCapacity
    # global UdpPort, UdpHost

    cfg_schema = {
        "type": "object",
        "properties": {
            "show info": {
                "type": "boolean"
            },
            "sleep time": {
                "type": "number",
                "minimum": 0,
                "maximum": 3600,
            },
            "critical capacity": {
                "type": "number",
                "minimum": 10,
                "maximum": 99,
            },
            "udp port": {
                "type": "number",
                "minimum": 4096,
                "maximum": 49151,
            },
            "udp host": {
                "type": "string",
                "format": "ip-address"
            }
        },
        "required": ["show info", "sleep time",
                     "critical capacity", "udp port", "udp host"],
        "additionalProperties": False
    }

    result: CfgReadResultEnumClass
    result = CfgReadResultEnumClass.is_not_exist
    error_message: str = ""
    file_name = "{0}/{1}.cfg".format(config_path, "PowerCtrl")

    # ShowInfo = SHOW_INFO
    # SleepTime = SLEEP_TIME
    # CriticalCapacity = CRITICAL_CAPACITY
    # UdpPort = UDP_PORT
    # UdpHost = UDP_HOST

    if os.path.isfile(file_name):
        result = CfgReadResultEnumClass.is_exist
        with open(file_name, "r") as cfg_file_handler:
            try:
                config = json.load(cfg_file_handler)
            except ValueError:
                error_message = ('Configuration file "' + file_name +
                                 '" hasn\'t JSON structure')
                result = CfgReadResultEnumClass.is_broken
                return result, error_message
            except Exception:
                error_message = 'Something unusual happened. Send this information with details to the author'
                result = CfgReadResultEnumClass.unknown
                return result, error_message
            else:
                cfg_validator = jsonschema.Draft3Validator(
                    cfg_schema,
                    format_checker=jsonschema.draft3_format_checker)
                if not cfg_validator.is_valid(config):
                    _error_message = 'The following errors were found in the configuration file "' + file_name + '":'
                    for error in sorted(cfg_validator.iter_errors(config), key=str):
                        _error_message += error.message
                        _error_message += '", "'
                    error_message = _error_message[:-3]
                    result = CfgReadResultEnumClass.is_incorrect
                    return result, error_message

                Configuration.ShowInfo = config.get("show info", SHOW_INFO)
                Configuration.SleepTime = config.get("sleep time", SLEEP_TIME)
                Configuration.CriticalCapacity = config.get("critical capacity", CRITICAL_CAPACITY)
                Configuration.UdpPort = config.get("udp port", UDP_PORT)
                Configuration.UdpHost = config.get("udp host", UDP_HOST)
                return result, error_message
    else:
        error_message = 'Configuration file "' + file_name + '" is missing'
        result = CfgReadResultEnumClass.is_not_exist
        return result, error_message


def create_logger(log_path: str):
    """create_logger -- Set up script logger. Log file has a name "PowerCtrl.log" and puts into directory, defined by argument "log_path"

    Arguments:
        log_path {string} -- Log file path
    """
    global TheLogger #, ShowInfo
    TheLogger = logging.getLogger(__name__)

    """ Create handlers """
    c_handler = logging.StreamHandler()
    f_handler = logging.FileHandler("{0}/{1}.log".format(log_path, "PowerCtrl"))

    """ Create formatters and add it to handlers"""
    c_format = logging.Formatter("%(asctime)s [%(threadName)-12s] [%(levelname)-8s]  %(message)s")
    f_format = logging.Formatter("%(asctime)s [%(threadName)-12s] [%(levelname)-8s]  %(message)s")
    c_handler.setFormatter(c_format)
    f_handler.setFormatter(f_format)

    if Configuration.ShowInfo:
        c_handler.setLevel(logging.DEBUG)
    else:
        c_handler.setLevel(logging.CRITICAL + 1)
    f_handler.setLevel(logging.INFO)

    """ Add handlers to the logger """
    TheLogger.addHandler(c_handler)
    TheLogger.addHandler(f_handler)

    TheLogger.setLevel(logging.DEBUG)


def pld_led_message(pld: PLDLedEnumClass) -> str:
    """pld_led_message -- Form PLD status string.

    Arguments:
        pld {PLDLedEnumClass} -- PLD status

    Returns:
        str -- String with PLD status
    """
    if pld == PLDLedEnumClass.off:
        return 'PLD status: off'
    if pld == PLDLedEnumClass.blink:
        return 'PLD status: blink'
    if pld == PLDLedEnumClass.red:
        return 'PLD status: red'
    return 'PLD status: unknown'


def power_loss_test() -> PLDLedEnumClass:
    """power_loss_test -- Test T208 UPS state.

    Returns:
        (class) PLDLedEnumClass -- PLD status
    """
    TEST_REPEATS = 10
    counter = 0
    # To recognize blinking state, have to get information {TEST_REPEATS} times
    for i in range(TEST_REPEATS):
        if GPIO.input(GPIO_PORT) != 0:
            counter += 1
        time.sleep(0.01)
    if counter == 0:
        return PLDLedEnumClass.off
    else:
        if counter < TEST_REPEATS:
            return PLDLedEnumClass.blink
        else:
            return PLDLedEnumClass.red



def read_voltage(bus: smbus.SMBus) -> Union[ReadT208ResultEnumClass, float]:
    """read_voltage -- Read current battary voltage

    Arguments:
        bus {smbus.SMBus} -- Number of I2C bus

    Returns:
        Union[ReadT208ResultEnumClass, float] -- State of battary voltage reading and its value
    """
    error_code: ReadT208ResultEnumClass
    error_code = ReadT208ResultEnumClass.is_correct
    try:
        read = bus.read_word_data(I2C_ADDRESS, 2)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        voltage = swapped * 1.25 / 1000 / 16
    except IOError as exception:
        if exception.errno == 121:
            TheLogger.critical("Cannot read value of voltage. It possible T208 dosn't connect. Exception:" + str(exception))
            error_code = ReadT208ResultEnumClass.is_not_connected
    except Exception as exception:
        TheLogger.critical("Function read_voltage stopped with an exception ---" + str(exception))
        error_code = ReadT208ResultEnumClass.unknown
    finally:
        if error_code != ReadT208ResultEnumClass.is_correct:
            voltage = 5
        # TheLogger.debug('error_code: {}'.format(error_code.name))
        return error_code, voltage

def read_capacity(bus: smbus.SMBus) -> Union[ReadT208ResultEnumClass, int]:
    """read_capacity -- Read current battary capacity

    Arguments:
        bus {smbus.SMBus} -- Number of I2C bus

    Returns:
        Union[ReadT208ResultEnumClass, int] -- State of battary capacity reading and its value
    """
    error_code: ReadT208ResultEnumClass
    error_code = ReadT208ResultEnumClass.is_correct
    try:
        read = bus.read_word_data(I2C_ADDRESS, 4)
        swapped = struct.unpack("<H", struct.pack(">H", read))[0]
        capacity = swapped / 256
    except IOError as exception:
        if exception.errno == 121:
            TheLogger.critical("Cannot read value of capacity. It possible T208 dosn't connect. Exception:" + str(exception))
            error_code = ReadT208ResultEnumClass.is_not_connected
    except Exception as exception:
        TheLogger.critical("Function read_capacity stopped with an exception ---" + str(exception))
        error_code = ReadT208ResultEnumClass.unknown
    finally:
        if error_code != ReadT208ResultEnumClass.is_correct:
            capacity = 100
        return error_code, capacity


def GetVoltage(bus: smbus.SMBus) -> str:
    """GetVoltage -- Return voltage in string format with error checking

    Arguments:
        bus {smbus.SMBus} -- Number of I2C bus

    Returns:
        str -- String like "Voltage:{value}V" or error information
    """
    reading_code: ReadT208ResultEnumClass
    reading_code, voltage = read_voltage(bus)
    # TheLogger.debug('reading_code: {}'.format(reading_code.name))
    if reading_code == ReadT208ResultEnumClass.is_correct:
        return "Voltage:%5.2fV" % voltage
    return "Incorrect information about voltage"


def GetCapacity(bus: smbus.SMBus) -> str:
    """GetCapacity -- Return capacity in string format with error checking

    Arguments:
        bus {smbus.SMBus} -- Number of I2C bus

    Returns:
        str -- String like "Capacity:{value}V" or error information
    """
    reading_code: ReadT208ResultEnumClass
    reading_code, capacity = read_capacity(bus)
    if reading_code == ReadT208ResultEnumClass.is_correct:
        return "Battery:%5i%%" % capacity
    return "Incorrect information about capacity"


def power_loss_control():
    """power_loss_control -- Run a loop of control of the UPS state.
    The loop breaks after T208 lost a power outage and battaries capacity reaches setting low level.
    """
    global is_time_to_stop
    global stop_plc_thread
    global pld_led_status

    GPIO.setmode(GPIO.BCM)
    GPIO.setup(GPIO_PORT, GPIO.IN)

    # 0 = /dev/i2c-0(port I2C0), 1 = /dev/i2c-1(port I2C1)
    bus = smbus.SMBus(1)
    try:

        TheLogger.info("======== START ========")
        TheLogger.info("Testing Started")
        TheLogger.info(GetVoltage(bus))
        TheLogger.info(GetCapacity(bus))

        is_time_to_stop = False
    # Main control loop
        while not stop_plc_thread:
            pld_led_status = power_loss_test()
            TheLogger.debug(pld_led_message(pld_led_status))
            if pld_led_status != PLDLedEnumClass.off:
                ReadingState, BattaryCapacity = read_capacity(bus)
                if ReadingState == ReadT208ResultEnumClass.is_correct:
                    if pld_led_status == PLDLedEnumClass.red:
                        TheLogger.warning("AC Power Loss OR Power Adapter Failure. Battery:%5i%%" % BattaryCapacity)
                        if BattaryCapacity < Configuration.CriticalCapacity:
                            TheLogger.error("The battery is too low. Battery:%5i%%" % BattaryCapacity)
                            is_time_to_stop = True
                            # exit()
                            break
                    else:
                        if pld_led_status == PLDLedEnumClass.blink:
                            TheLogger.debug("PLD led is blinking. It isn't normal state. Battery:%5i%%" % BattaryCapacity)
            # if pld_led_status == PLDLedEnumClass.red:
            #     ReadingState, BattaryCapacity = read_capacity(bus)

            #     TheLogger.warning("AC Power Loss OR Power Adapter Failure. Battery:%5i%%" % BattaryCapacity)

            #     if BattaryCapacity < Configuration.CriticalCapacity:
            #         TheLogger.error("The battery is too low. Battery:%5i%%" % BattaryCapacity)
            #         is_time_to_stop = True
            #         # exit()
            #         break
            # else:
            #     if pld_led_status == PLDLedEnumClass.blink:
            #         BattaryCapacity = read_capacity(bus)
            #         TheLogger.debug("PLD led is blinking. It isn't normal state. Battery:%5i%%" % BattaryCapacity)
            #     else:
            #         if pld_led_status == PLDLedEnumClass.off:
            #             pass
            time.sleep(Configuration.SleepTime)
    except Exception as exception:
        exc_type, exc_obj, exc_tb = sys.exc_info()
        TheLogger.critical("Stopped with an exception ---" + str(exception) + "--- in line" + str(exc_tb.tb_lineno))
    finally:
        if is_time_to_stop:
            TheLogger.warning("System will be shutdowned in 5 seconds.")
        # stop_logging()
        TheLogger.info("~~~~~~~~~ STOP ~~~~~~~~~")
        GPIO.cleanup()
        TheLogger.debug("Control stopped")


def udp_server():
    """udp_server -- Run udp-server loop
    Udp-server waits command from client and sends an answer:
    - for command 'state' sends information, created with function 'pld_led_message'
    - for command 'charge' sends information about capacity and voltage of battaries
    - for other sends 'Ready' answer
    """
    global stop_udp_server_thread
    global pld_led_status
    # global UdpPort, UdpHost

    timeout = 5
    # host = '192.168.201.201'
    # host = ''
    # port = 7777
    host = Configuration.UdpHost
    port = Configuration.UdpPort
    addr = (host, port)
    server = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        server.bind(addr)
    except OSError as error:
        ErrorMsg = error.strerror + ". UDP-server isn't exist."
        TheLogger.warning (ErrorMsg)
        return

    stop_udp_server_thread = False

    while not stop_udp_server_thread:
        server.settimeout(timeout)
        msg = "Ready"
        try:
            d = server.recvfrom(1024)
        except socket.timeout:
            continue

        received_str = d[0].decode('utf-8')
        addr = d[1]
        TheLogger.debug(received_str)
        if received_str == "state":
            msg = pld_led_message(pld_led_status)
        else:
            if received_str == "charge":
                bus = smbus.SMBus(1)
                msg = GetVoltage(bus) + " " + GetCapacity(bus)
            else:
                msg = "Ready"
        TheLogger.debug(msg)
        server.sendto(msg.encode('utf-8'), addr)
    server.close()
    TheLogger.debug("Udp stopped")


def main():
    """main -- Organize the general logic of the script.
    This function create logger, runs the control loop and udp server threads,
    and shuts down the computer when shutdown conditions are reached.
    """
    global stop_plc_thread, stop_udp_server_thread
    global pld_led_status
    # global ShowInfo, SleepTime, CriticalCapacity

    # Eliminate the chance to run another exemplar of the script.
    try:
        me = singleton.SingleInstance()
    except:
        sys.exit()

    pld_led_status = PLDLedEnumClass.off
    stop_plc_thread = False

    # Get path for log file and config file
    if len(sys.argv) > 1:
        # name = sys.argv[0]
        logpath = sys.argv[1]
        if not os.path.isdir (logpath):
            logpath = path.abspath(path.dirname(__file__))
    else:
        # name = sys.argv[0]
        logpath = path.abspath(path.dirname(__file__))

    # ShowInfo = SHOW_INFO
    # SleepTime = SLEEP_TIME
    # CriticalCapacity = CRITICAL_CAPACITY

    # Read config file and get error message to use it by logger if nessery
    read_cfg_res: CfgReadResultEnumClass
    read_cfg_res, cfg_error_message = read_config(logpath)

    create_logger(logpath)

    if read_cfg_res == CfgReadResultEnumClass.is_exist:
        TheLogger.debug('Config file was opened')
    elif read_cfg_res == CfgReadResultEnumClass.is_broken:
        TheLogger.warn(cfg_error_message + '. Default values will be set')
    elif read_cfg_res == CfgReadResultEnumClass.is_incorrect:
        TheLogger.warn(cfg_error_message + '. Default values will be set')
    elif read_cfg_res == CfgReadResultEnumClass.is_not_exist:
        TheLogger.warn(cfg_error_message + '. Default values will be set')

    if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
        TheLogger.debug('Running in a PyInstaller bundle')
    else:
        TheLogger.debug('Running in a normal Python process')

    try:
        # Create threads and wait keyboard interrupt
        th_control = Thread(target=power_loss_control, daemon=False)
        th_udp = Thread(target=udp_server, daemon=False)
        th_control.start()
        th_udp.start()
        while True:
            time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        # Set flags to stop thread loops and block threads until finish
        stop_plc_thread = True
        stop_udp_server_thread = True
        th_control.join()
        th_udp.join()
    finally:
        # If need to shut down, stop udp-server thread and send system command "poweroof"
        if is_time_to_stop:
            stop_udp_server_thread = True
            th_udp.join()
            time.sleep(5)
            os.system("poweroff")
        else:
            TheLogger.debug("Ordinary exit")

if __name__ == "__main__":
    main()
