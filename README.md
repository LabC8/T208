Control script for Geekworm T208 UPS for Jatson Nano (https://wiki.geekworm.com/T208).
Some functions were get from https://wiki.geekworm.com/T208-Software. Strongly recommended to read the webpage before using this script.
The script periodecly checks if the device is plugged to the mains, and it's battary capacity and voltage.
The script turns off power of Jetson when T208 battary capacity reaches setting low level and it lost a power outage.
Information about the state of device, if necessary, available by UDP.