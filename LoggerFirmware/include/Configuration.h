/*! \file Configuration.h
 *  \brief Provide configuration checks for the module
 *
 * There are a number of parameters that need to be set to configure the logger, including
 * things like which logger functionality to bring up (NMEA0183, NMEA2000, Motion Sensor,
 * Power Monitoring, etc.).  These parameters are managed by the ParamStore module, but need
 * to be checked in a number of different locations.  In order to avoid magic strings appearing
 * everywhere in the code, the Config object centralises these requirements.
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

#ifndef __CONFIGURATION_H__
#define __CONFIGURATION_H__

#include <Arduino.h>
#include "ParamStore.h"

namespace logger {

/// \class Config
/// \brief Encapsulate configuration parameter management
///
/// The logger needs to store a number of parameters related to the operation (e.g., which data sources to log,
/// which memory bus to use, the WiFi SSD, etc.)  In order to standardise and encapsulate this, this class
/// provides a standard interface for both binary flags and strings (the binary flags being converted into a
/// standard string, that being the only thing that ParamStore will store).  Note that there is no mechanism to
/// store anything other than a string, so if you want to store numbers, you have to convert first, and then
/// again on return.  That isn't very efficient, but it does keep things simple, and this sort of parameter
/// lookup should only happen rarely anyway.

class Config {
    public:
        /// \brief Default constructor
        Config(void);
        /// \brief Default destructor
        ~Config(void);

        /// \enum ConfigParam
        /// \brief Provide a list of configuration parameters supported by the module
        enum ConfigParam {
            CONFIG_NMEA0183_B = 0,  /* Binary: NMEA0183 logging configured on */
            CONFIG_NMEA2000_B,      /* Binary: NMEA2000 logging configured on */
            CONFIG_MOTION_B,        /* Binary: Motion sensor logging configured on */
            CONFIG_POWMON_B,        /* Binary: Power monitoring configured on */
            CONFIG_SDMMC_B,         /* Binary: SD-MMC (SDIO) interface for log files */
            CONFIG_BOOT_BLE_B,      /* Binary: Boot the BLE interface on start, or WiFi */
            CONFIG_BRIDGE_B,        /* Binary: Bridge UDP broadcast packets to NMEA0183 */
            CONFIG_WEBSERVER_B,     /* Binary: Use web server interface to configure system */
            CONFIG_MODULEID_S,      /* String: User-specified unique identifier for the module */
            CONFIG_BLENAME_S,       /* String: BLE advertising name for the module */
            CONFIG_WIFISSID_S,      /* String: WiFi SSID to use for AP/Station */
            CONFIG_WIFIPSWD_S,      /* String: WiFi password to use */
            CONFIG_WIFIIP_S,        /* String: WiFi IP address assigned */
            CONFIG_WIFIMODE_S,      /* String: WiFi mode (Station, SoftAP) */
            CONFIG_BAUDRATE_1_S,    /* String: baud rate for NMEA0183 input channel 1 */
            CONFIG_BAUDRATE_2_S,    /* String: baud rate for NMEA0183 input channel 2 */
            CONFIG_BRIDGE_PORT_S    /* String: UDP broadcast port to bridge to NMEA0183 */
        };

        /// \brief Extract a configuration string for the specified parameter
        bool GetConfigString(ConfigParam const param, String& value);
        /// \brief Set a configuration string for the specified parameter
        bool SetConfigString(ConfigParam const param, String const& value);

        /// \brief Extract a configuration flag for the specified parameter
        bool GetConfigBinary(ConfigParam const param, bool& value);
        /// \brief Set a configuration flag for the specified parameter
        bool SetConfigBinary(ConfigParam const param, bool value);

    private:
        ParamStore  *m_params;  ///< Underlying key-value store implementation

        /// \brief Convert external parameter name to the key string used for lookup
        void Lookup(ConfigParam const param, String& key);
};

extern Config LoggerConfig; ///< Declaration of a global pre-allocated instance for lookup

}

#endif
