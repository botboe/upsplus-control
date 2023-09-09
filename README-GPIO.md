# X728-GPIOs and communication

Documentation from https://github.com/DavidAntliff/x728ups/blob/main/x728ups.py

## GPIOs

### GPIO 5 - "SHUTDOWN"
 - High > 600ms when UPS requests RPi shutdown
 - High > 200ms & < 600ms when UPS requests RPi reboot

### GPIO 6 - "PLD"
 - AC power loss detection
 - High when external power is disconnected (and jumper 3 present)
 - Low when external power is connected (or jumper 3 is missing)

### GPIO 12 - "BOOT OK"
 - RPi should set this high after boot
 - when the UPS is in shutdown-waiting mode, the RPi setting this to low initiates a UPS power-off after ~5300ms.

### GPIO 13 - "BUTTON"
 - can be set by RPi for a period of time to simulate a button-press
 - therefore can initiate a shutdown sequence on the UPS

### Protocol
RPi can request UPS shutdown with pulses on GPIO 13
UPS can request RPi shutdown with pulses on GPIO 5
UPS can notify RPi of external power status with GPIO 6
RPi can tell UPS that it is shut down with falling edge on GPIO 12 - UPS will auto-power off ~5300ms after this event.

## Operation
Sequence of operation for this service is:

1. User initiates RPi power up, or external power is restored and Jumper 2 (AON) is present.
2. RPi boots and starts this systemd service (x728ups).
3. This service sets GPIO 12 ("BOOT OK") high immediately.
4. This service monitors GPIO 5:
     - If GPIO 5 is continuously high for more than 200ms and less than 600ms, this service will reboot the RPi.
     - if GPIO 5 is continuously high for more than 600ms, this service will shut down the RPi.
5. This service monitors GPIO 6:
     - If GPIO 6 is continuously high for more than X seconds, this service will request a shut down of the system via
       GPIO 13 (see note below).

Note: System reboot (UPS & RPi) is requested by holding GPIO 13 high for 240 - 1500ms.
System shutdown is requested by holding GPIO 13 high for longer than 1500ms.
System immediate power-off occurs if GPIO 13 is high for longer than ~6400ms.


UPS states:

 - Idle mode - blue PWR LED is solid on.
 - ~200ms to ~1500ms button press results in ~500ms pulse on GPIO 5, triple-blink of blue PWR LED - request reboot.
 - ~1500ms or longer button press results in continual high on GPIO 5, pulsing of blue PWR LED - request shutdown.
 - If GPIO 12 does not go low shortly after either of these requests are issued, the mode expires after about 50 seconds.

"""