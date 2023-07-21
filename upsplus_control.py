#!/usr/bin/env python3

# '''Enable Auto-Shutdown Protection Function '''
import os
import time
import smbus2
import logging
import argparse
import sys
from ina219 import INA219,DeviceRangeError

# https://wiki.52pi.com/index.php?title=EP-0136

### General settings ###
# Set the threshold of UPS automatic power-off to prevent damage caused by battery over-discharge, unit: mV.
PROTECT_VOLT = 3500

# Set the time on battery before automatic shutdown, e. g. initiate a shutdown after a defined period after shutting down the powersupply
TIME_ON_BATTERY_BEFORE_SHUTDOWN = 20

# Delay to poweroff the UPS after OS-Shutdown
UPS_POWEROFF_DELAY = 20

# Set the interval between the checks of the ups-state
CHECK_INTERVAL = 5


### I2C-settings ###
# Define I2C bus
DEVICE_BUS = 1

# Define device i2c slave address.
UPS_DEVICE_ADDR = 0x17

# Register for shutting down the ups
UPS_POWEROFF_REGISTER = 0x18


class UpsState:
    """Contains the UPS' current state"""
    input_voltage_micro_usb = 0
    input_voltage_usb_c = 0
    current_runtime = 0

    def is_on_battery(self):
        return (self.input_voltage_usb_c < 1000) and (self.input_voltage_micro_usb < 1000)
    
    def power_state_str(self):
        if(ups_state.is_on_battery()):
            return("On battery")
        else:
            return("External power supplied")

def poll_ups_data(ups_state):
    aReceiveBuf = []
    aReceiveBuf.append(0x00)
    for i in range(1, 255):
        aReceiveBuf.append(bus.read_byte_data(UPS_DEVICE_ADDR, i))

    ups_state.input_voltage_usb_c       = (aReceiveBuf[8] << 8 | aReceiveBuf[7])
    ups_state.input_voltage_micro_usb   = (aReceiveBuf[10] << 8 | aReceiveBuf[9])
    ups_state.current_runtime           = (aReceiveBuf[0x27] << 24 | aReceiveBuf[0x26] << 16 | aReceiveBuf[0x25] << 8 | aReceiveBuf[0x24])
    return aReceiveBuf

def shutdown_os():
    logging.info("Initiating OS and UPS shutdown... goodbye!")
    time.sleep(1)
    if(not args.test):
        bus.write_byte_data(UPS_DEVICE_ADDR, UPS_POWEROFF_REGISTER, UPS_POWEROFF_DELAY)
        os.system("sudo sync && sudo halt")
    quit()

def write_settings():
    logging.info("Writing Settings to UPS")
    quit()

if __name__ == "__main__":

    # Read options and configuration
    parser = argparse.ArgumentParser(prog='UPSplus - Autoshutdown', description="Automatic shutdown of RPI and the connected UPSplus.")
    parser.add_argument("--debug",          "-d",   action='store_true', help="runs the daemon in debug-mode")
    parser.add_argument("--shutdown",       "-s",   action='store_true', help="shutdown os and ups immediately")
    parser.add_argument("--test",           "-t",   action='store_true', help="testmode without shutdown")
    parser.add_argument("--write-config",   "-w",   action='store_true', help="writes settings to UPS-board", dest='writeconfig')
    args = parser.parse_args()

    # set up logging
    if args.debug:
        logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Shutdown OS and UPS directly
    if args.shutdown:
        shutdown_os()

    # Write settings to UPS-hardware
    if args.writeconfig:
        write_settings()

    # Starting main-job
    logging.debug("Python version: %s" % sys.version)
    logging.info("UPS-Daemon started")
    if(args.test):
        logging.info("Running in Test-Mode - No automatic shutdown!")

    # Initiate communication with MCU via i2c protocol.
    bus = smbus2.SMBus(DEVICE_BUS)



    ups_state = UpsState()
    poll_ups_data(ups_state)
    prev_is_on_battery = ups_state.is_on_battery()
    if(ups_state.is_on_battery()):
        timestamp_begin_on_battery = time.time()

    logging.debug("Starts watching UPS-state")
    logging.info("Current power-state: " + ups_state.power_state_str())
    while(True):
        logging.debug("Checking state...")
        poll_ups_data(ups_state)
        
        if((prev_is_on_battery == False) and (ups_state.is_on_battery() == True)): 
            logging.info("State changed to on-battery!")
            logging.info("Automatic shutdown after " + str(TIME_ON_BATTERY_BEFORE_SHUTDOWN) + " sseconds")
            timestamp_begin_on_battery = time.time()

        if((prev_is_on_battery == True) and (ups_state.is_on_battery() == False)): 
            logging.info("State changed to external power")

        if(ups_state.is_on_battery()):
            logging.debug("Time on battery: " + str(time.time() - timestamp_begin_on_battery) + " seconds")
            if(time.time() - timestamp_begin_on_battery > TIME_ON_BATTERY_BEFORE_SHUTDOWN):
                shutdown_os()
        else:
            logging.debug("Current power-state: " + ups_state.power_state_str())


        prev_is_on_battery = ups_state.is_on_battery()
        time.sleep(CHECK_INTERVAL)

