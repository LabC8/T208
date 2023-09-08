# Control script for Geekworm T208 UPS for Jatson Nano.

## 1 Introduction
The script periodecly checks if [Geekworm T208](https://wiki.geekworm.com/T208) is plugged to the mains, and it's battary capacity and voltage.
The script turns off power of Jetson when T208 battary capacity reaches setting low level and it lost a power outage.
Information about the state of device, if necessary, available by UDP. Simple script to control by UDP located in this repository and named *udp_client.py*

Some functions were get from [Geekworm T208 Software page](https://wiki.geekworm.com/T208-Software). Strongly recommended to read the webpage before using this script.

## 2 Installation
To install and use our script let's follow the next steps:
### 2.1 Clone the code:
<details>
<summary>Attention!</summary> 
You must use your own T208 script path. {T208_FOLDER_NAME} is only alias. In my case e.g. it is */home/jetson/T208*
</details>
```
$ git clone -b debug https://github.com/LabC8/T208.git {T208_FOLDER_NAME}
```
### 2.2 Install necessary packages:
<details>
<summary>Remark</summary> 
I hadn't to install `Jetson.GPIO` module, it had been installed on my Jetson Nano by default.
</details>
```
$ sudo pip install Jetson.GPIO
$ pip3 install smbus
$ pip3 install jsonschema
$ pip3 install tendo
```
### 2.3 And run script:
```
$ python3 {T208_FOLDER_NAME}/PowerControl.py
```

Before executing of step 2.2 you may want to install script into virtual environment like [venv](https://docs.python.org/3/library/venv.html), but it is not good idea to put our script inside virtual environment venv because of necessity to install one of python package from sudo. If you install a package with sudo, it ignore **$PATH** environment variable and the package is placed in *usr/bin* instead of *VENV/bin*.
We can follow the next steps instead of step 2.2 , but it is not good practise:

### 2.2.1 Create and activate our virtual environment
```
$ cd {T208_FOLDER_NAME}
$ python3 -m venv T208.venv
$ source {T208_FOLDER_NAME}/T208.venv/bin/activate
```
### 2.2.2 Install necessary packages:
```
$ pip3 install -r {T208_FOLDER_NAME}/requirements.txt
```
### 2.2.3 Allow all to write and read gpiochip. 
<details>
<summary>Attention!</summary> 
This command will cause the following message to show *"{T208_FOLDER_NAME}/T208.venv/lib/python3.6/site-packages/Jetson/GPIO/gpio_event.py:182: RuntimeWarning: Event not found".*
Script shows it at execution of instruction `"GPIO.cleanup()"` before finish as in case venv is active, so in case venv was disactivated. Maybe there is a better solution, but I didn't look for it.
</details>
```	
$ sudo chmod a+rw /dev/gpiochip*
```
## 3 Start program like a service
### 3.1 Use a Python application 
At first [PyInstaller](https://pypi.org/project/pyinstaller/) was used to create a Python application with all its dependencies. It located at *{T208_FOLDER_NAME}/dist/PowerControl* folder with *PowerControl* file name.
### 3.2 Grant root privileges to our Python application 
Then if we want to use PowerControl with power off capability, we have to use [visudo](https://www.sudo.ws/docs/man/1.8.13/visudo.man/): 
```
$ sudo visudo
```
and add our program *PowerControl* into sudoers module, inserting the line `jetson ALL=NOPASSWD: {T208_FOLDER_NAME}/T208/dist/PowerControl/PowerControl` into the end of the file.

### 3.3 Create a systemd service
Then we will create a systemd service file that will allow us to control our service [accordingly with the example] (https://www.shellhacks.com/systemd-service-file-example/)

Create Systemd Service File
```
$ sudo touch /etc/systemd/system/t208.service
$ sudo chmod 664 /etc/systemd/system/t208.service
```
Open the /etc/systemd/system/t208.service with a text editor (e.g. vi): 
```
$ sudo vi /etc/systemd/system/t208.service
```
and add the next lines
```
[Unit]
Description=T208Daemon

[Service]
#!!!Replace {T208_FOLDER_NAME} with your T208 project directory
ExecStart={T208_FOLDER_NAME}/dist/PowerControl/PowerControl {T208_FOLDER_NAME}

[Install]
WantedBy=multi-user.target
```
Once the service file is changed, it needs to reload systemd configuration:
```
$ sudo systemctl daemon-reload
```
Now you should be able to start ...
```
$ sudo systemctl start t208.service
```
... and check the service status
```
$ systemctl status t208.service
```
We need to get the status of the service is active (running)

To configure a service to start automatically on boot, you need to enable it:
```
$ sudo systemctl enable t208.service
```