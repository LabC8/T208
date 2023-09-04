# Control script for Geekworm T208 UPS for Jatson Nano.

## Introduction
The script periodecly checks if [Geekworm T208](https://wiki.geekworm.com/T208) is plugged to the mains, and it's battary capacity and voltage.
The script turns off power of Jetson when T208 battary capacity reaches setting low level and it lost a power outage.
Information about the state of device, if necessary, available by UDP.

Some functions were get from [Geekworm T208 Software page](https://wiki.geekworm.com/T208-Software). Strongly recommended to read the webpage before using this script.

##Installation
To install and use our script let's follow the next steps:
1.1 Clone the code:
```
git clone -b debug https://github.com/LabC8/T208.git {T208_FOLDER_NAME}
```
1.2 Install necessary packages:
```
sudo pip install Jetson.GPIO
pip3 install smbus
pip3 install jsonschema
pip3 install tendo
```
1.3 And run script:
```
python3 {T208_FOLDER_NAME}/PowerControl.py
```

Before executing of step 1.2 you may want to install script into virtual environment like [venv](https://docs.python.org/3/library/venv.html), but it is not good idea to put our script inside virtual environment venv because of necessity to install one of python package from sudo. If you install a package with sudo, it ignore **$PATH** environment variable and the package is placed in *usr/bin* instead of *VENV/bin*.
We can follow the next steps instead of step 1.2 , but it is not good practise:

###1.2.1) Create and activate our virtual environment
```
cd {T208_FOLDER_NAME}
python3 -m venv T208.venv
source {T208_FOLDER_NAME}/T208.venv/bin/activate
```
###1.2.2) Install necessary packages:
```
pip3 install -r {T208_FOLDER_NAME}/requirements.txt
```
###1.2.3) Allow all to write and read gpiochip. 
<sup>
Attention! This command will cause the following message to show *"{T208_FOLDER_NAME}/T208.venv/lib/python3.6/site-packages/Jetson/GPIO/gpio_event.py:182: RuntimeWarning: Event not found".*
Script shows it at execution of instruction `"GPIO.cleanup()"` before finish as in case venv is active, so in case venv was disactivated. Maybe there is a better solution, but I didn't look for it.
</sup>
```	
sudo chmod a+rw /dev/gpiochip*
```
##Start program like a service
I.
If we want to use PowerControl with Jetson Nano power off capability, we have to use visudo and add our program:
{MY_USER_NAME} ALL=NOPASSWD: /{PATH}/{TO}/{YOUR}/{T208 DIRECTORY}/PowerControl/PowerControl
!!!TO DO try to add (root) like this myusername ALL = (root) NOPASSWD: /path/to/my/program

II.
How to make PowerControl starts like a service (https://www.shellhacks.com/systemd-service-file-example/):

Lets add visudo with
jetson ALL=NOPASSWD: /home/jetson/T208/dist/PowerControl/PowerControl

Lets use systemd:
1. Create Systemd Service File
    $ sudo touch /etc/systemd/system/t208.service
    $ sudo chmod 664 /etc/systemd/system/t208.service

2. Open the /etc/systemd/system/t208.service with vi for example "sudo vi /etc/systemd/system/t208.service" and add the next lines
    [Unit]
    Description=T208Daemon

    [Service]
    #!!!Replace /{PATH}/{TO}/{YOUR}/{T208 DIRECTORY} with your T208 project directory
    ExecStart=/{PATH}/{TO}/{YOUR}/{T208 DIRECTORY}/dist/PowerControl/PowerControl /home/jetson/T208

    [Install]
    WantedBy=multi-user.target

3. Once the service file is changed, it needs to reload systemd configuration:
    $ sudo systemctl daemon-reload

4. Now you should be able to start...
    $ sudo systemctl start t208.service

5. ...and check the service status
    $ systemctl status t208.service

    We need to get the status of the service active (running)

6. To configure a service to start automatically on boot, you need to enable it:
    $ sudo systemctl enable t208.service