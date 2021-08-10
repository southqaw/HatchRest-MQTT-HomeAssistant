# Hatch Rest Home Assistant MQTT Bridge
This program allows an original [Hatch Rest](https://www.hatch.co/rest) to be controlled via BLE, through MQTT. This program has support for Home Assistant MQTT auto discovery. The Hatch Rest will show up as a Switch component, a Light component and a Fan component (for the sound machine part). This program is primarily intended to be run on Raspberry Pi devices. This is a bit flakey, and sometimes stops working. I just restart the Pi every night.
## Installation
* Clone the repo somewhere onto a raspberry pi that is physically close to the Hatch
* Copy the `mqtt.ini.example` file to `mqtt.ini`
** Edit the various entries
** You can get the MAC from a BLE scanner
* Install the packages in requirements.txt with pip
* Start the hatchmqtt.py at startup of the Pi.
## Example

## Credits
