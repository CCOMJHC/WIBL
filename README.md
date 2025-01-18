# Low-cost Data Logger System

## Purpose

This repository contains the hardware designs, firmware source code, and supporting applications and libraries for a low-cost data logger aimed at the NMEA ([National Marine Electronics Association](https://www.nmea.org)) 0183 and 2000 protocols, as used in many marine electronics systems.  The goal is to provide a minimally-functional system to record the data appearing on NMEA0183 and NMEA2000 busses on board ships, which can be used to provide volunteer depth observations (and many other things) to assist in mapping the oceans.

## Why Have Another Logger?

There is a robust infrastructure of data loggers for both NMEA0183 and NMEA2000 busses, but they are often intended for different purposes (e.g., voyage data recorders, WiFi gateways, etc.), and they are typically order US$250 [2020] or more.  This project came out of efforts within the [Seabed 2030](https://seabed2030.gebco.net) project to map the world ocean completely by 2030, where large-scale mapping is required if the goals of the programme are to be met.  Consequently, while volunteer data is a part of the solution, it has to be something that can be scaled to very large data collections.  Since it has proven hard to sustain open data collection of this type (most of the sustained efforts have been closed, with data only going back to the collectors, and not to open databases), we believe that the only viable financial model for this purpose is to give the hardware away for free, rather than attempting to sell it for profit.  That is, the hardware is free to the data collector, who is asked just to host the hardware on their ship.  Because of this model, we need the hardware to be as low-cost as possible.

This project is therefore aimed at designing as simple, and low-cost, a logger as possible, so that as many as possible can be built and distributed to assist in mapping the oceans.  The target price is order US$30 [2020] for one interface (either NMEA0183 or NMEA2000), or US$40 [2020] for both interfaces.

At the same time, we recognise that getting data from the loggers into the national and international databases can be difficult, and ask a lot of the volunteer data collectors.  The project is therefore also attempting to define a workflow for submission of data to the [International Hydrographic Office](https://iho.int)'s [Data Center for Digital Bathymetry](https://www.ngdc.noaa.gov/iho/), hosted by the [National Centers for Environmental Information](https://www.ngdc.noaa.gov) in Boulder, CO.  The goal is to have a "Trusted Node in a Box", so that anyone wanting to support collection of data of this kind has everything they need to support a very basic data flowpath direct from the loggers through the cloud to DCDB.  (Developers are then free to add on anything else they need.)

## What Does the Logger Do?

The logger's functionality is deliberately constrained.  During normal operations, the logger monitors the NMEA0183 and/or NMEA2000 busses to which it is attached, and records any valid data packet received to local storage.  Timestamps are provided through the elapsed time counter on the microcontroller used, and although a pseudo-time is computed from NMEA2000 data packets if they are available, there is no expectation that timestamps will be assigned until the data is uploaded for processing.

The logger provides an always-on Bluetooth Low Energy service that acts as a software UART.  Client software can connect to this service and pass ASCII commands to the logger to control logging, determine the files that have been logged and their sizes, manage log files, set non-volatile parameters for the system, and so on.  Critically, the BLE service can also be used to start and stop the logger's WiFi service, which is used to give higher-speed transfer of data (although it also responds to all of the same commands).  This avoids having another WiFi network on board the ship if it is not required.

After upload to a mobile collection device (e.g., a cell-phone or tablet), the data is then sent to Amazon Web Services at the first stable communications connection of the mobile device, at which point it is processed, reformatted, packaged, and transmitted to DCDB for archive.

## Concept of Operations

This logger is designed for supported, focussed, data collections.  In this mode, loggers would be provided by an organisation in a specific geographic location to support data collection in a particular area.  The goal here is to provide density of observations in an area, which greatly assists in processing the data, and making useful products.  In addition to providing the loggers (and recruiting the volunteer observers), the organisation would also provide local support personnel to visit the volunteer observers, pick up the collected data (via mobile device), and make sure that the loggers were still collecting data.  Having local support also ensures that there is continued communication with the observers, which is useful in sustaining the community in the long term.

After each visit, all of the data collected (potentially from multiple observers) on the mobile device can be uploaded to any available service that implements the cloud segment of the software suite.  This could be something set up specifically for the organisation using the model provided here, or it could be a third-party that provides an equivalent.

## Licensing and Distribution

In order to provide for the widest possible use (and to avoid excuses ...) the hardware designs, firmware source, and supporting libraries are all released as Open Source under the MIT license.  The cloud segment is released under the MIT License for non-commercial use; for commercial licenses, please contact info@ccom.unh.edu.

## Where to Start
See the "Logger firmware" section below to get started with the WIBL loggers. 
See the "Data management" section below to get started using WIBL and 
`wibl-python` tools to manage and process data generated by WIBL loggers.


### Logger firmware

The source for the system is maintained in a [BitBucket repository](https://bitbucket.org/brian_r_calder/sb2030logger), which also includes a Wiki for details of the design and system development.

To build the system, you will need at least:

1. A functional Python interpreter (at least 3.6).

2. A working [Arduino](https://www.arduino.cc) development environment (at least 1.8.12), or equivalent (e.g., [embedXcode](https://embedxcode.weebly.com) 11.8.8).

3. Support for [Espressif](https://www.espressif.com) ESP32 development (with Arduino 1.8.12 this can be installed from the IDE, see [here](https://github.com/espressif/arduino-esp32) for instructions).

4. Support for NMEA2000 handling on ESP32 (you need the [base library](https://github.com/ttlappalainen/NMEA2000) and [ESP-specific](https://github.com/ttlappalainen/NMEA2000_esp32) extensions).

5. Eagle CAD (at least 9.5.2) for the hardware designs.

6. A working C++11 (at least) compiler for the software data simulator.

With these prerequisites, the recommended place to start is with the logger firmware, followed with the data parser Python, which will allow you to demonstrate that your logger is actually logging data.  For benchtop testing, the hardware data simulator can be used (with the development board) to generate simulated data on both NMEA0183 and NMEA2000 for testing logger modifications.  The WiFi Command GUI can be used to interact with a logger once WiFi is enabled, allowing you to transfer files, and decode them.


### Data management

The included [wibl-python](wibl-python/README.md) tools allow data from WIBL 
loggers to be processed into GeoJSON format and to be submitted to 
[DCDB](https://www.ngdc.noaa.gov/iho/). There is also a tool called 
[LogConvert](LogConvert) that allows data from TeamSurv and Yacht Devices
loggers to be converted to WIBL format for further processing using 
`wibl-python`.

An easy way to use both `wibl-python` and `LogConvert` is to use the official
WIBL [container images](DataManagement/containers/README.md).
