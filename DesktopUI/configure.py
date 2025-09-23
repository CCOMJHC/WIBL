# configure.py
#
# Provide a simple configuration dialog box for configuration
#
# Copyright 2023 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
# Hydrographic Center, University of New Hampshire.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
# and to permit persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
# OR OTHER DEALINGS IN THE SOFTWARE.

import tkinter as tk
import tkinter.ttk as ttk
from tkinter import filedialog
from tkinter import messagebox as mbox
from typing import Dict, Any
import json
from command import LoggerInterface
from uuid import uuid4

class ConfigDBox:
    hor_pad = 10
    ver_pad = 5
    __default_commandproc_version__ = '1.4.0'
    __default_providerid__ = 'UNHJHC'

    def __init__(self, root, address: str, port: str, output_widget):
        self.root = tk.Toplevel(root)
        self.server_address = address
        self.server_port = port
        self.output_widget = output_widget

        self.main_frame = tk.Frame(self.root, padx=self.hor_pad, pady=self.ver_pad)
        self.main_frame.pack(fill='both')

        self.left_column = tk.Frame(self.main_frame)
        self.left_column.grid(row=0,column=0, sticky="n")
        self.right_column = tk.Frame(self.main_frame)
        self.right_column.grid(row=0,column=1, sticky="n")

        # Set up version information (which should not be edited)
        self.version_frame = tk.LabelFrame(self.left_column, text='Versions', padx=self.hor_pad, pady=self.ver_pad)
        self.version_frame.grid(row=0, column=0, columnspan=2, sticky='we')
        self.firmware_var = tk.StringVar()
        self.command_var = tk.StringVar()
        self.nmea0183_var = tk.StringVar()
        self.nmea2000_var = tk.StringVar()
        self.imu_var = tk.StringVar()
        self.serialiser_var = tk.StringVar()
        self.firmware_version_label = tk.Label(self.version_frame, text='Firmware')
        self.firmware_version_entry = tk.Entry(self.version_frame, textvariable=self.firmware_var, state='disabled')
        self.firmware_version_label.grid(row=0, column=0, sticky='e')
        self.firmware_version_entry.grid(row=0, column=1, sticky='w')
        self.command_version_label = tk.Label(self.version_frame, text='Command Processor')
        self.command_version_entry = tk.Entry(self.version_frame, textvariable=self.command_var, state='disabled')
        self.command_version_label.grid(row=1, column=0, sticky='e')
        self.command_version_entry.grid(row=1, column=1, sticky='w')
        self.nmea0183_version_label = tk.Label(self.version_frame, text='NMEA0183 Logger')
        self.nmea0183_version_entry = tk.Entry(self.version_frame, textvariable=self.nmea0183_var, state='disabled')
        self.nmea0183_version_label.grid(row=2, column=0, sticky='e')
        self.nmea0183_version_entry.grid(row=2, column=1, sticky='w')
        self.nmea2000_version_label = tk.Label(self.version_frame, text='NMEA2000 Logger')
        self.nmea2000_version_entry = tk.Entry(self.version_frame, textvariable=self.nmea2000_var, state='disabled')
        self.nmea2000_version_label.grid(row=3, column=0, sticky='e')
        self.nmea2000_version_entry.grid(row=3, column=1, sticky='w')
        self.imu_version_label = tk.Label(self.version_frame, text='IMU Logger')
        self.imu_version_entry = tk.Entry(self.version_frame, textvariable=self.imu_var, state='disabled')
        self.imu_version_label.grid(row=4, column=0, sticky='e')
        self.imu_version_entry.grid(row=4, column=1, sticky='w')
        self.serialiser_version_label = tk.Label(self.version_frame, text='Serialiser')
        self.serialiser_version_entry = tk.Entry(self.version_frame, textvariable=self.serialiser_var, state='disabled')
        self.serialiser_version_label.grid(row=5, column=0, sticky='e')
        self.serialiser_version_entry.grid(row=5, column=1, sticky='w')

        # Set up metadata on unique ID and ship name
        self.metadata_frame = tk.LabelFrame(self.left_column, text='Metadata', padx=self.hor_pad, pady=self.ver_pad)
        self.metadata_frame.grid(row=1, column=0, columnspan=2, sticky='we')
        self.uniqueid_var = tk.StringVar()
        self.shipname_var = tk.StringVar()
        self.uniqueid_label = tk.Label(self.metadata_frame, text='Unique Identifier')
        self.uniqueid_entry = tk.Entry(self.metadata_frame, textvariable=self.uniqueid_var)
        self.uniqueid_label.grid(row=0, column=0, sticky='e')
        self.uniqueid_entry.grid(row=0, column=1, sticky='w')
        self.uniqueid_button = tk.Button(self.metadata_frame, text='Generate UUID', command=self.on_uuid_generate)
        self.uniqueid_button.grid(row=0, column=2, sticky='w')
        self.shipname_label = tk.Label(self.metadata_frame, text='Ship Name')
        self.shipname_entry = tk.Entry(self.metadata_frame, textvariable=self.shipname_var)
        self.shipname_label.grid(row=1, column=0, sticky='e')
        self.shipname_entry.grid(row=1, column=1, sticky='w')

        # Set up the check-buttons for all of the optional loggers, etc.
        self.options_frame = tk.LabelFrame(self.left_column, text='Options', padx=self.hor_pad, pady=self.ver_pad)
        self.options_frame.grid(row=2, column=0, sticky='nw')
        self.log_nmea0183_var = tk.IntVar()
        self.log_nmea2000_var = tk.IntVar()
        self.log_imu_var = tk.IntVar()
        self.powermonitor_var = tk.IntVar()
        self.sdmmc_var = tk.IntVar()
        self.udpbridge_var = tk.IntVar()
        self.webserver_var = tk.IntVar()
        self.upload_var = tk.IntVar()
        self.nmea0183_check = tk.Checkbutton(self.options_frame, text='NMEA0183 Logger', variable=self.log_nmea0183_var, onvalue=1, offvalue=0)
        self.nmea0183_check.grid(row=0, column=0, sticky='w')
        self.nmea2000_check = tk.Checkbutton(self.options_frame, text='NMEA2000 Logger', variable=self.log_nmea2000_var, onvalue=1, offvalue=0)
        self.nmea2000_check.grid(row=1, column=0, sticky='w')
        self.imu_check = tk.Checkbutton(self.options_frame, text='IMU Logger', variable=self.log_imu_var, onvalue=1, offvalue=0)
        self.imu_check.grid(row=2, column=0, sticky='w')
        self.powermonitor_check = tk.Checkbutton(self.options_frame, text='Emergency Power Monitor', variable=self.powermonitor_var, onvalue=1, offvalue=0)
        self.powermonitor_check.grid(row=3, column=0, sticky='w')
        self.sdmmc_check = tk.Checkbutton(self.options_frame, text='SD/MMC Memory Controller', variable=self.sdmmc_var, onvalue=1, offvalue=0)
        self.sdmmc_check.grid(row=4, column=0, sticky='w')
        self.udpbridge_check = tk.Checkbutton(self.options_frame, text='UDP NMEA0183 Bridge', variable=self.udpbridge_var, onvalue=1, offvalue=0)
        self.udpbridge_check.grid(row=5, column=0, sticky='w')
        self.webserver_check = tk.Checkbutton(self.options_frame, text='Webserver On Boot', variable=self.webserver_var, onvalue=1, offvalue=0)
        self.webserver_check.grid(row=6, column=0, sticky='w')
        self.upload_check = tk.Checkbutton(self.options_frame, text='Auto-upload Logfiles', variable=self.upload_var, onvalue=1, offvalue=0)
        self.upload_check.grid(row=7, column=0, sticky='w')

        # Set up the auto-upload configuration panel
        self.upload_frame = tk.LabelFrame(self.left_column, text='Upload', padx=self.hor_pad, pady=self.ver_pad)
        self.upload_frame.grid(row=2, column=1, sticky='nwe', padx=(self.hor_pad, 0))
        self.upload_server_var = tk.StringVar()
        self.upload_port_var = tk.IntVar()
        self.upload_timeout_var = tk.DoubleVar()
        self.upload_interval_var = tk.DoubleVar()
        self.upload_duration_var = tk.DoubleVar()
        self.upload_server_label = tk.Label(self.upload_frame, text='Server')
        self.upload_server_entry = tk.Entry(self.upload_frame, textvariable=self.upload_server_var)
        self.upload_server_label.grid(row=0, column=0, sticky='e')
        self.upload_server_entry.grid(row=0, column=1, sticky='w')
        self.upload_port_label = tk.Label(self.upload_frame, text='Port')
        self.upload_port_entry = tk.Entry(self.upload_frame, textvariable=self.upload_port_var)
        self.upload_port_label.grid(row=1, column=0, sticky='e')
        self.upload_port_entry.grid(row=1, column=1, sticky='w')
        self.upload_timeout_label = tk.Label(self.upload_frame, text='Timeout (s)')
        self.upload_timeout_entry = tk.Entry(self.upload_frame, textvariable=self.upload_timeout_var)
        self.upload_timeout_label.grid(row=2, column=0, sticky='e')
        self.upload_timeout_entry.grid(row=2, column=1, sticky='w')
        self.upload_interval_label = tk.Label(self.upload_frame, text='Interval (s)')
        self.upload_interval_entry = tk.Entry(self.upload_frame, textvariable=self.upload_interval_var)
        self.upload_interval_label.grid(row=3, column=0, sticky='e')
        self.upload_interval_entry.grid(row=3, column=1, sticky='w')
        self.upload_duration_label = tk.Label(self.upload_frame, text='Duration (s)')
        self.upload_duration_entry = tk.Entry(self.upload_frame, textvariable=self.upload_duration_var)
        self.upload_duration_label.grid(row=4, column=0, sticky='e')
        self.upload_duration_entry.grid(row=4, column=1, sticky='w')

        # Set up the (rather complex) WiFi configuration frame
        self.wifi_frame = tk.LabelFrame(self.right_column, text='WiFi Configuration', padx=self.hor_pad, pady=self.ver_pad)
        self.wifi_frame.grid(row=0, column=1, sticky='nwe', padx=self.hor_pad)
        self.wifi_mode_var = tk.StringVar()
        self.wifi_address_var = tk.StringVar()
        self.retry_delay_var = tk.IntVar()
        self.retry_count_var = tk.IntVar()
        self.join_timeout_var = tk.IntVar()
        self.ap_ssid_var = tk.StringVar()
        self.ap_passwd_var = tk.StringVar()
        self.station_ssid_var = tk.StringVar()
        self.station_passwd_var = tk.StringVar()
        self.mdns_name_var = tk.StringVar()
        self.udpbridge_port_var = tk.IntVar()

        self.mode_label = tk.Label(self.wifi_frame, text='Mode')
        self.mode_combo = ttk.Combobox(self.wifi_frame, textvariable=self.wifi_mode_var, values=('AP', 'Station'))
        self.mode_label.grid(row=0, column=0, stick='e')
        self.mode_combo.grid(row=0, column=1, sticky='w')
        self.address_label = tk.Label(self.wifi_frame, text='Address')
        self.address_entry = tk.Entry(self.wifi_frame, textvariable=self.wifi_address_var, state='disabled')
        self.address_label.grid(row=1, column=0, sticky='e')
        self.address_entry.grid(row=1, column=1, sticky='w')

        self.station_frame = tk.LabelFrame(self.wifi_frame, text='Station Join Configuration', padx=self.hor_pad, pady=self.ver_pad)
        self.station_frame.grid(row=2, column=0, columnspan=2,sticky='we')
        self.retry_delay_label = tk.Label(self.station_frame, text='Retry Delay (s)')
        self.retry_delay_entry = tk.Entry(self.station_frame, textvariable=self.retry_delay_var)
        self.retry_delay_label.grid(row=0, column=0, sticky='e')
        self.retry_delay_entry.grid(row=0, column=1, sticky='w')
        self.retry_count_label = tk.Label(self.station_frame, text='Retry Count')
        self.retry_count_entry = tk.Entry(self.station_frame, textvariable=self.retry_count_var)
        self.retry_count_label.grid(row=1, column=0, sticky='e')
        self.retry_count_entry.grid(row=1, column=1, sticky='w')
        self.join_timeout_label = tk.Label(self.station_frame, text='Join Timeout (s)')
        self.join_timeout_entry = tk.Entry(self.station_frame, textvariable=self.join_timeout_var)
        self.join_timeout_label.grid(row=2, column=0, sticky='e')
        self.join_timeout_entry.grid(row=2, column=1, sticky='w')

        self.identity_frame = tk.LabelFrame(self.wifi_frame, text='Identification', padx=self.hor_pad, pady=self.ver_pad)
        self.identity_frame.grid(row=3, column=0, columnspan=2, sticky='we')
        self.ap_ssid_label = tk.Label(self.identity_frame, text='AP SSID')
        self.ap_ssid_entry = tk.Entry(self.identity_frame, textvariable=self.ap_ssid_var)
        self.ap_ssid_label.grid(row=0, column=0, sticky='e')
        self.ap_ssid_entry.grid(row=0, column=1, sticky='w')
        self.ap_passwd_label = tk.Label(self.identity_frame, text='AP Password')
        self.ap_passwd_entry = tk.Entry(self.identity_frame, textvariable=self.ap_passwd_var)
        self.ap_passwd_label.grid(row=1, column=0, sticky='e')
        self.ap_passwd_entry.grid(row=1, column=1, sticky='w')
        self.station_ssid_label = tk.Label(self.identity_frame, text='Station SSID')
        self.station_ssid_entry = tk.Entry(self.identity_frame, textvariable=self.station_ssid_var)
        self.station_ssid_label.grid(row=2, column=0, sticky='e')
        self.station_ssid_entry.grid(row=2, column=1, sticky='w')
        self.station_passwd_label = tk.Label(self.identity_frame, text='Station Password')
        self.station_passwd_entry = tk.Entry(self.identity_frame, textvariable=self.station_passwd_var)
        self.station_passwd_label.grid(row=3, column=0, sticky='e')
        self.station_passwd_entry.grid(row=3, column=1, sticky='w')
        self.mdns_name_label = tk.Label(self.identity_frame, text='mDNS Responder Name')
        self.mdns_name_entry = tk.Entry(self.identity_frame, textvariable=self.mdns_name_var)
        self.mdns_name_label.grid(row=4, column=0, sticky='e')
        self.mdns_name_entry.grid(row=4, column=1, sticky='w')

        self.udpbridge_port_label = tk.Label(self.wifi_frame, text='UDP Bridge Port')
        self.udpbridge_port_entry = tk.Entry(self.wifi_frame, textvariable=self.udpbridge_port_var)
        self.udpbridge_port_label.grid(row=5, column=0, sticky='e')
        self.udpbridge_port_entry.grid(row=5, column=1, sticky='w')

        # Set up baud rate frame
        self.baud_frame = tk.LabelFrame(self.right_column, text='NMEA0183 Baud Rates', padx=self.hor_pad, pady=self.ver_pad)
        self.baud_frame.grid(row=3, column=1, sticky='we', padx=self.hor_pad)
        self.port1_baud_var = tk.IntVar()
        self.port2_baud_var = tk.IntVar()
        self.port1_baud_label = tk.Label(self.baud_frame, text='Port 1')
        self.port1_baud_entry = tk.Entry(self.baud_frame, textvariable=self.port1_baud_var)
        self.port1_baud_label.grid(row=0, column=0, sticky='e')
        self.port1_baud_entry.grid(row=0, column=1, sticky='w')
        self.port2_baud_label = tk.Label(self.baud_frame, text='Port 2')
        self.port2_baud_entry = tk.Entry(self.baud_frame, textvariable=self.port2_baud_var)
        self.port2_baud_label.grid(row=1, column=0, sticky='e')
        self.port2_baud_entry.grid(row=1, column=1, sticky='w')

        # Set up buttons for 'Configure' and 'Cancel'
        self.button_frame = tk.Frame(self.main_frame, padx=self.hor_pad, pady=self.ver_pad)
        self.button_frame.grid(row=2, column=0, columnspan=2)
        self.querylogger_button = tk.Button(self.button_frame, text='Query Logger', command=self.on_querylogger)
        self.querylogger_button.grid(row=0, column=0, sticky="ew")
        self.setlogger_button = tk.Button(self.button_frame, text='Set Logger', command=self.on_setlogger)
        self.setlogger_button.grid(row=0, column=1, sticky="ew")
        self.getdefaults_button = tk.Button(self.button_frame, text='Get Defaults', command=self.on_getdefaults)
        self.getdefaults_button.grid(row=0, column=2, sticky="ew")
        self.setdefaults_button = tk.Button(self.button_frame, text='Set Defaults', command=self.on_setdefaults)
        self.setdefaults_button.grid(row=0, column=3, sticky="ew")
        self.load_button = tk.Button(self.button_frame, text='Load Config', command=self.on_load)
        self.load_button.grid(row=0, column=4, sticky="ew")
        self.save_button = tk.Button(self.button_frame, text='Save Config', command=self.on_save)
        self.save_button.grid(row=0, column=5, sticky="ew")
        self.dismiss_button = tk.Button(self.button_frame, text='Dismiss', command=self.on_dismiss)
        self.dismiss_button.grid(row=0, column=6, sticky="ew")

        with open('assets/default_config.json', 'r') as f:
            config = json.load(f)
        self.configure(config)

    def on_uuid_generate(self):
        uniqueid = self.__default_providerid__ + '-' + str(uuid4())
        self.uniqueid_var.set(uniqueid)
    
    def on_querylogger(self):
        interface = LoggerInterface(self.server_address, self.server_port)
        success, info = interface.execute_command('setup')
        if success:
            config = json.loads(info)
            self.configure(config)
        else:
            self.record(info + '\n')

    def on_setlogger(self):
        config = self.getconfig()
        # The configuration doesn't have version information, but the logger needs this in order
        # to know whether it's going to be able to interpret the JSON or not.  We add whatever's
        # configured here, rather than what's coming from anywhere else.
        config['version'] = { 'commandproc': self.__default_commandproc_version__ }
        json_text = json.dumps(config)
        command = 'setup ' + json_text
        interface = LoggerInterface(self.server_address, self.server_port)
        success, info = interface.execute_command(command)
        if success:
            mbox.showinfo(title='Logger Setup', message='Logger configuration completed successfully.')
        else:
            mbox.showerror(title='Logger Setup', message='Logger configuration failed.')
        self.record(info + '\n')

    def on_load(self):
        filename = filedialog.askopenfilename(title='Open Configuration', filetypes=[('JSON Files', '*.json')])
        if filename:
            with open(filename, 'r') as f:
                data = json.load(f)
            if data:
                self.configure(data)

    def on_save(self):
        config = self.getconfig()
        config['version'] = { 'commandproc': self.__default_commandproc_version__ }
        config_name=f'{config["uniqueID"]}.json'
        filename = filedialog.asksaveasfilename(title='Save Configuration', initialfile=config_name, defaultextension='json', confirmoverwrite=True)
        if filename:
            with open(filename, 'w') as f:
                json.dump(config, f, indent=4)
    
    def on_getdefaults(self):
        interface = LoggerInterface(self.server_address, self.server_port)
        status, info = interface.execute_command('lab defaults')
        if status:
            json_data = json.loads(info)
            if 'version' not in json_data or 'commandproc' not in json_data['version']:
                self.record('ERR: lab defaults JSON text not valid ({json_data})\n')
                return
            if json_data['version']['commandproc'] != self.__default_commandproc_version__:
                self.record(f'ERR: lab defaults JSON version is not compatible ({json_data["version"]})\n')
                return
            self.configure(json_data)
        else:
            self.record(f'ERR: failed to extract lab defaults from logger\n{info}\n')

    def on_setdefaults(self):
        interface = LoggerInterface(self.server_address, self.server_port)
        current_config = self.getconfig()
        current_config['version'] = { 'commandproc': self.__default_commandproc_version__ }
        json_config = json.dumps(current_config)
        status, info = interface.execute_command(f'lab defaults {json_config}')
        if status:
            self.record('INF: set lab defaults on logger.\n')
        else:
            self.record(f'ERR: failed to set lab defaults on logger\n{info}\n')

    def on_dismiss(self):
        self.root.destroy()

    def record(self, message: str) -> None:
        self.output_widget.insert(tk.END, message)
        self.output_widget.yview_moveto(1.0)
    
    def getconfig(self) -> Dict[str, Any]:
        rtn = {
            'enable': {
                'nmea0183':     self.map_checkbutton(self.log_nmea0183_var.get()),
                'nmea2000':     self.map_checkbutton(self.log_nmea2000_var.get()),
                'imu':          self.map_checkbutton(self.log_imu_var.get()),
                'powermonitor': self.map_checkbutton(self.powermonitor_var.get()),
                'sdmmc':        self.map_checkbutton(self.sdmmc_var.get()),
                'udpbridge':    self.map_checkbutton(self.udpbridge_var.get()),
                'webserver':    self.map_checkbutton(self.webserver_var.get()),
                'upload':       self.map_checkbutton(self.upload_var.get())
            },
            'wifi': {
                'mode': self.wifi_mode_var.get(),
                'station': {
                    'delay':    self.retry_delay_var.get(),
                    'retries':  self.retry_count_var.get(),
                    'timeout':  self.join_timeout_var.get(),
                    'mdns':     self.mdns_name_var.get()
                },
                'ssids': {
                    'ap':       self.ap_ssid_var.get(),
                    'station':  self.station_ssid_var.get()
                },
                'passwords': {
                    'ap':       self.ap_passwd_var.get(),
                    'station':  self.station_passwd_var.get()
                }
            },
            'uniqueID': self.uniqueid_var.get(),
            'shipname': self.shipname_var.get(),
            'baudrate': {
                'port1':    self.port1_baud_var.get(),
                'port2':    self.port2_baud_var.get()
            },
            'udpbridge':    self.udpbridge_port_var.get(),
            'upload': {
                'server':   self.upload_server_var.get(),
                'port':     self.upload_port_var.get(),
                'timeout':  self.upload_timeout_var.get(),
                'interval': self.upload_interval_var.get(),
                'duration': self.upload_duration_var.get()
            }
        }
        return rtn
    
    def map_checkbutton(self, button_val: int) -> bool:
        if button_val:
            return True
        else:
            return False

    def configure(self, config: Dict[str, Any]):
        if 'version' in config:
            if 'commandproc' not in config['version']:
                self.record(f'ERR: missing command processor version information in JSON configuration.\n{config}\n')
                return
            self.command_var.set(config['version']['commandproc'])
            if 'firmware' in config['version']:
                self.firmware_var.set(config['version']['firmware'])
            if 'nmea0183' in config['version']:
                self.nmea0183_var.set(config['version']['nmea0183'])
            if 'nmea2000' in config['version']:
                self.nmea2000_var.set(config['version']['nmea2000'])
            if 'imu' in config['version']:
                self.imu_var.set(config['version']['imu'])
            if 'serialiser' in config['version']:
                self.serialiser_var.set(config['version']['serialiser'])
        self.log_nmea0183_var.set(config['enable']['nmea0183'])
        self.log_nmea2000_var.set(config['enable']['nmea2000'])
        self.log_imu_var.set(config['enable']['imu'])
        self.powermonitor_var.set(config['enable']['powermonitor'])
        self.sdmmc_var.set(config['enable']['sdmmc'])
        self.udpbridge_var.set(config['enable']['udpbridge'])
        self.webserver_var.set(config['enable']['webserver'])
        self.wifi_mode_var.set(config['wifi']['mode'])
        self.upload_var.set(config['enable']['upload'])
        if 'address' in config['wifi']:
            self.wifi_address_var.set(config['wifi']['address'])
        self.retry_delay_var.set(config['wifi']['station']['delay'])
        self.retry_count_var.set(config['wifi']['station']['retries'])
        self.join_timeout_var.set(config['wifi']['station']['timeout'])
        self.mdns_name_var.set(config['wifi']['station']['mdns'])
        self.ap_ssid_var.set(config['wifi']['ssids']['ap'])
        self.ap_passwd_var.set(config['wifi']['passwords']['ap'])
        self.station_ssid_var.set(config['wifi']['ssids']['station'])
        self.station_passwd_var.set(config['wifi']['passwords']['station'])
        self.uniqueid_var.set(config['uniqueID'])
        self.shipname_var.set(config['shipname'])
        self.port1_baud_var.set(config['baudrate']['port1'])
        self.port2_baud_var.set(config['baudrate']['port2'])
        self.udpbridge_port_var.set(config['udpbridge'])
        self.upload_server_var.set(config['upload']['server'])
        self.upload_port_var.set(config['upload']['port'])
        self.upload_timeout_var.set(config['upload']['timeout'])
        self.upload_interval_var.set(config['upload']['interval'])
        self.upload_duration_var.set(config['upload']['duration'])
