# upsplus-control
Toolset for interaction with the Raspberry-PI UPS ["UPS Plus"]([LICENSE](https://52pi.com/products/52pi-ups-board-with-rtc-coulometer-for-raspberry-pi?variant=40719609102488)) by 52PI. More details in the official [wiki](https://wiki.52pi.com/index.php/EP-0136).


## Prerequisites

* Enable I2C on the RPi
    ```
    sudo raspi-config
    > 3 Interface Options > I5 I2C > Yes
    ```

* Clone this repository:
    ```
    git clone https://github.com/botboe/upsplus-control.git
    ```

* Install necessary dependencies:
    ```
    sudo apt-get update
    sudo apt-get install git i2c-tools

    pip3 install smbus smbus2
    ```


## Usage
