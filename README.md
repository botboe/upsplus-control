# upsplus-control
Toolset for interaction with the Raspberry-PI UPS ["UPS Plus"]([LICENSE](https://52pi.com/products/52pi-ups-board-with-rtc-coulometer-for-raspberry-pi?variant=40719609102488)) by 52PI. More details in the official [wiki](https://wiki.52pi.com/index.php/EP-0136).


## Prerequisites

* Enable I2C on the RPi
    ```
    sudo raspi-config
    > 3 Interface Options > I5 I2C > Yes
    ```

* Install necessary dependencies:
    ```
    sudo apt-get update
    sudo apt-get install git i2c-tools

    pip3 install smbus smbus2
    ```

* Clone this repository:
    ```
    git clone https://github.com/botboe/upsplus-control.git
    ```

## Usage

### Dryrun
Disables the shutdown-functionality to test and debug the behavior
```
python3 ./upsplus_control.py --<OPTION> --test
```

### Shutdown OS followed by UPS
```
python3 ./upsplus_control.py --shutdown
```

