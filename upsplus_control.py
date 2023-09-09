#!/usr/bin/env python3

# '''Enable Auto-Shutdown Protection Function '''
import os
import time
import smbus2
import logging
import argparse
import sys
import subprocess
import RPi.GPIO as GPIO
import struct
import multiprocessing

### General settings ###

# Set the time on battery before automatic shutdown, e. g. initiate a shutdown after a defined period after shutting down the powersupply
TIME_ON_BATTERY_BEFORE_SHUTDOWN = 20

# Set the interval between the checks of the ups-state
CHECK_INTERVAL = 5

# Call a script before initiating the shutdown
BEFORE_SHUTDOWN_SCRIPT = "/home/pi/upsplus-control/before_shutdown.sh"


### Battery settings

# Set the "Protection Voltage" in mV. If the battery's voltage is lower, a shutdown is initiated
BATTERY_VOLTAGE_PROTECTION = 3100


### X728 - pins and timings ###
# If pin high, the ups has a powerloss detected
PIN_POWERLOSS_DETECTION = 6

# pin-toggling initiates shutdown-mode on the ups
PIN_INIT_UPS_POWEROFF = 26

# high pin state informs the ups that the RPi has booted. 
# a low state tells the ups that it's save to powerdown the RPi's powersupply (low state set on shutdown via "dtoverlay=gpio-poweroff,gpiopin=12,active_low=1")
PIN_BOOTED_STATE = 12

# pin for ups-initiated reboot / shutdown requests
PIN_UPS_REQUESTS = 5

# pulse-interval in milliseconds for reboot, if longer do a shutdown
UPS_REBOOT_PULSE_MIN = 200
UPS_REBOOT_PULSE_MAX = 600


### I2C-settings ###
# Define I2C bus
UPS_I2S_DEVICE_BUS = 1

# Define device i2c slave address.
UPS_I2S_DEVICE_ADDR = 0x36

# Register for shutting down the ups
UPS_POWEROFF_REGISTER = 0x18

# Initiate communication with MCU via i2c protocol.
bus = smbus2.SMBus(UPS_I2S_DEVICE_BUS)

# Configure GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)
GPIO.setup(PIN_POWERLOSS_DETECTION, GPIO.IN)
GPIO.setup(PIN_UPS_REQUESTS, GPIO.IN)
GPIO.setup(PIN_INIT_UPS_POWEROFF, GPIO.OUT)
GPIO.setup(PIN_BOOTED_STATE, GPIO.OUT)

class UpsState:
    """Contains the UPS' current state"""
    battery_voltage = 0
    battery_capacity = 0

    def is_on_battery(self):
        if GPIO.input(PIN_POWERLOSS_DETECTION):
            return True
        else:
            return False
    
    def power_state_str(self):
        if(self.is_on_battery()):
            return("On battery")
        else:
            return("External power")

def current_time_ns():
    return time.time_ns() / 1000000

def poll_ups_data(ups_state):
    i2c_data = bus.read_word_data(UPS_I2S_DEVICE_ADDR, 2)
    unpacked = struct.unpack("<H", struct.pack(">H", i2c_data))[0]
    ups_state.battery_voltage = unpacked * 1.25 / 1000 / 16

    i2c_data = bus.read_word_data(UPS_I2S_DEVICE_ADDR, 4)
    unpacked = struct.unpack("<H", struct.pack(">H", i2c_data))[0]
    ups_state.battery_capacity = 100 if (unpacked / 256) > 100 else unpacked / 256

def show_ups_state():
    ups_state = UpsState()
    poll_ups_data(ups_state)
    logging.info("[UPS] Powersupply: "  + ups_state.power_state_str())
    logging.info("[Battery] Voltage: "  + "{:.2f}".format(ups_state.battery_voltage) + "V")
    logging.info("[Battery] Capacity: " + "{:.2f}".format(ups_state.battery_capacity) + "%")

def activate_ups_poweroff_mode():
    GPIO.output(PIN_INIT_UPS_POWEROFF, GPIO.HIGH)
    time.sleep(3.5)
    GPIO.output(PIN_INIT_UPS_POWEROFF, GPIO.LOW)

def run_pre_shutdown_script():
    try:
        if BEFORE_SHUTDOWN_SCRIPT:
            logging.info("Trying to run before-shutdown-script")
            logging.info(subprocess.run([BEFORE_SHUTDOWN_SCRIPT,
                        ""], shell=True))
            logging.info("Success!")
    except Exception as e:
        logging.info("Failed, could not run before-shutdown-script:")
        logging.info(str(e))

def os_shutdown():
    logging.info("Initiating OS and UPS shutdown... goodbye!")
    run_pre_shutdown_script()
    if(not args.test):
        activate_ups_poweroff_mode()
        os.system("sudo sync && sudo shutdown -h now")

def os_reboot():
    logging.info("Initiating OS reboot... see you later!")
    run_pre_shutdown_script()
    if(not args.test):
        os.system("sudo sync && sudo shutdown -r now")

def ups_check_pld():
    prev_is_on_battery = ups_state.is_on_battery()
    if(ups_state.is_on_battery()):
        timestamp_begin_on_battery = time.time()

    logging.debug("[PROC] Started watching UPS-state")
    logging.info("Current power-state: " + ups_state.power_state_str())
    while(True):
        logging.debug("Checking state...")
        poll_ups_data(ups_state)
        
        if((prev_is_on_battery == False) and (ups_state.is_on_battery() == True)): 
            logging.info("State changed to on-battery!")
            logging.info("Automatic shutdown after " + str(TIME_ON_BATTERY_BEFORE_SHUTDOWN) + " seconds")
            timestamp_begin_on_battery = time.time()

        if((prev_is_on_battery == True) and (ups_state.is_on_battery() == False)): 
            logging.info("State changed to external power")

        if(ups_state.is_on_battery()):
            logging.debug("Time on battery: " + "{:.0f}".format(time.time() - timestamp_begin_on_battery) + " seconds")
            if args.debug:
                show_ups_state()
            if(time.time() - timestamp_begin_on_battery > TIME_ON_BATTERY_BEFORE_SHUTDOWN):
                os_shutdown()
        else:
            if args.debug:
                show_ups_state()


        prev_is_on_battery = ups_state.is_on_battery()
        time.sleep(CHECK_INTERVAL)

def ups_check_request():
    logging.debug("[PROC] Started watching for UPS-requests")
    while(True):
        if GPIO.input(PIN_UPS_REQUESTS) == 0:
            time.sleep(0.1)
        else:
            pulse_start = current_time_ns()
            logging.debug("[REQ] ups-pulse detected")
            while GPIO.input(PIN_UPS_REQUESTS) == 1:
                time.sleep(0.02)
                if current_time_ns() - pulse_start > UPS_REBOOT_PULSE_MAX:
                    logging.info("[UPS-REQ] Shutdown requested...")
                    os_shutdown()
            if current_time_ns() - pulse_start > UPS_REBOOT_PULSE_MIN:
                logging.info("[UPS-REQ] Reboot requested...")
                os_reboot()


if __name__ == "__main__":

    # Read options and configuration
    parser = argparse.ArgumentParser(prog='UPSplus - Autoshutdown', description="Automatic shutdown of RPI and the connected UPSplus.")
    parser.add_argument("--debug",              "-d",   action='store_true', help="runs the daemon in debug-mode")
    parser.add_argument("--shutdown",           "-s",   action='store_true', help="shutdown os and ups immediately")
    parser.add_argument("--test",               "-t",   action='store_true', help="testmode without shutdown")
    parser.add_argument("--show-battery-state", "-b",   action='store_true', help="shows current battery state", dest='showbatterystate')

    args = parser.parse_args()

    # set up logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Shutdown OS and UPS directly
    if args.shutdown:
        os_shutdown()
        quit()

    # Show battery settings
    if args.showbatterystate:
        logging.info("=== Current UPS state ===")
        show_ups_state()
        quit()

    # Starting main-job
    logging.debug("Python version: %s" % sys.version)
    logging.info("UPS-Daemon started")

    logging.info("Setting PIN \"Booted\" to high state")
    GPIO.output(PIN_BOOTED_STATE, GPIO.HIGH)
    
    if(args.test):
        logging.info("Running in Test-Mode - No automatic shutdown!")

    ups_state = UpsState()
    poll_ups_data(ups_state)



    proc_ups_check_pld = multiprocessing.Process(target=ups_check_pld, args=())
    proc_ups_check_request = multiprocessing.Process(target=ups_check_request, args=())
    proc_ups_check_pld.start()
    proc_ups_check_request.start()

