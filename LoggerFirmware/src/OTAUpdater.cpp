/*!\file OTAUpdater.cpp
 * \brief Adapter to put ESP32 into "over the air" update mode
 *
 * The ESP32 module allows for the firmware to be updated through the WiFi interface
 * through a particular protocol over a standard port.  This module generates the
 * appropriate server objects to allow this to take place.  Note that this is a
 * terminal condition, since the last thing that happens after OTA update is that
 * the system reboots for the new firmware.  Once the system goes into OTA mode,
 * therefore, it does not return.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense,
 * and/or sell copies of the Software, and to permit persons to whom the Software is furnished
 * to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 * IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS
 * FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS
 * OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
 * WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF
 * OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <Arduino.h>
#include "WiFi.h"
#include "ESPmDNS.h"
#include "WiFiUdp.h"
#include "ArduinoOTA.h"
#include "OTAUpdater.h"
#include "WiFiAdapter.h"
#include "SerialCommand.h"
#include "LogManager.h"
#include "Configuration.h"

extern nmea::N2000::Logger *N2000Logger;        ///< Pointer to the NMEA2000 logger object (for shutdown)
extern nmea::N0183::Logger *N0183Logger;        ///< Pointer to the NMEA0183 logger object (for shutdown)
extern logger::Manager     *logManager;         ///< Pointer to the log manager (for shutdown)
extern SerialCommand       *CommandProcessor;   ///< Pointer to the current command processor (for shutdown)

/// Set up for over-the-air update of the logger firmware.  This is a one-way street: once the OTA starts,
/// the only way back is to reset the logger at the end of the update.  The system also takes down the
/// various loggers, the command processor, and the log manager to recover enough memory to allow the update
/// to take place (there's apparently some limit based on available heap).

OTAUpdater::OTAUpdater(void)
{
    // Setting up the OTA with all of the services running can cause problems
    // with having enough RAM to do processing.  These therefore need to go
    // down before starting.  Since the whole system is going to reboot afterwards,
    // this isn't a major problem.
    Serial.println("Stopping logger services for update ...");
    delete CommandProcessor;
    delete N2000Logger;
    delete N0183Logger;
    delete logManager;
    Serial.println("Configuring WiFi Adapter ...");
    WiFiAdapter *wifi = WiFiAdapterFactory::Create(nullptr);
    Serial.println("Starting WiFi interface ...");
    if (wifi->Startup()) {
        String ip_address;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WIFIIP_S, ip_address);
        Serial.printf("WiFi started up on IP %s\n", ip_address.c_str());
    } else {
        Serial.printf("WiFi startup failed, rebooting.\n");
        ESP.restart();
    }
    Serial.println("Configuring OTA server ...");
    ArduinoOTA
        .onStart([]() {
        String type;
        if (ArduinoOTA.getCommand() == U_FLASH)
            type = "sketch";
        else
            type = "filesystem";
        Serial.println("Start updating " + type);
        })
        .onEnd([]() {
        Serial.println("\nEnd.");
        })
        .onProgress([](unsigned int progress, unsigned int total) {
        Serial.printf("Progress: %u%%\r", (progress / (total / 100)));
        })
        .onError([](ota_error_t error) {
        Serial.printf("Error[%u]: ", error);
        if (error == OTA_AUTH_ERROR) Serial.println("Auth failed");
        else if (error == OTA_BEGIN_ERROR) Serial.println("Begin failed");
        else if (error == OTA_CONNECT_ERROR) Serial.println("Connect failed");
        else if (error == OTA_RECEIVE_ERROR) Serial.println("Receive failed");
        else if (error == OTA_END_ERROR) Serial.println("End failed");
    });

    Serial.println("Starting OTA updater service ...");
    ArduinoOTA.begin();

    Serial.println("Waiting for OTA update on WiFi ...");
    while (true) {
        ArduinoOTA.handle();
    }
}
