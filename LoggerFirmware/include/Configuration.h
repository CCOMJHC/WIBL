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
#include "ArduinoJson.h"
#include "ParamStore.h"

namespace logger {

// Firmware software version (i.e., overall firmware, rather than components like Command Processor, etc.)
const int firmware_major = 1;
const int firmware_minor = 6;
const int firmware_patch = 0;

/// @brief Stringify the version information for the firmware itself
String FirmwareVersion(void);

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

        /// \brief Checks whether the configuration is valid
        bool IsValid(void);

        /// \enum ConfigParam
        /// \brief Provide a list of configuration parameters supported by the module
        enum ConfigParam {
            CONFIG_NMEA0183_B = 0,  /* Binary: NMEA0183 logging configured on */
            CONFIG_NMEA2000_B,      /* Binary: NMEA2000 logging configured on */
            CONFIG_MOTION_B,        /* Binary: Motion sensor logging configured on */
            CONFIG_POWMON_B,        /* Binary: Power monitoring configured on */
            CONFIG_SDMMC_B,         /* Binary: SD-MMC (SDIO) interface for log files */
            CONFIG_BRIDGE_B,        /* Binary: Bridge UDP broadcast packets to NMEA0183 */
            CONFIG_WEBSERVER_B,     /* Binary: Use web server interface to configure system */
            CONFIG_UPLOAD_B,        /* Binary: enable auto-upload when online */
            CONFIG_MODULEID_S,      /* String: User-specified unique identifier for the module */
            CONFIG_SHIPNAME_S,      /* String: User-specific name for the ship hosting the WIBL */
            CONFIG_AP_SSID_S,       /* String: WiFi SSID for AP */
            CONFIG_AP_PASSWD_S,     /* String: WiFi password to use for AP */
            CONFIG_STATION_SSID_S,  /* String: WiFi SSID to use when acting as a station */
            CONFIG_STATION_PASSWD_S,/* String: WiFi password to use when acting as a station */
            CONFIG_WIFIIP_S,        /* String: WiFi IP address assigned */
            CONFIG_WIFIMODE_S,      /* String: WiFi mode (Station, SoftAP) */
            CONFIG_BAUDRATE_1_S,    /* String: baud rate for NMEA0183 input channel 1 */
            CONFIG_BAUDRATE_2_S,    /* String: baud rate for NMEA0183 input channel 2 */
            CONFIG_BRIDGE_PORT_S,   /* String: UDP broadcast port to bridge to NMEA0183 */
            CONFIG_STATION_DELAY_S, /* String: delay (seconds) before web-server attempts to re-joint a client network */
            CONFIG_STATION_RETRIES_S,/* String: retries (int) before web-server reverts to "safe-mode". */
            CONFIG_STATION_TIMEOUT_S,/* String: delay (seconds) before declaring a WiFi connection attempt failed */
            CONFIG_WS_STATUS_S,     /* String: status of the configuration web server */
            CONFIG_WS_BOOTSTATUS_S, /* String: status of the configuration web server at boot time */
            CONFIG_DEFAULTS_S,      /* String: JSON-format for default "lab reset" parameters */
            CONFIG_UPLOAD_TOKEN_S,  /* String: shared upload token for cloud transmission */
            CONFIG_UPLOAD_SERVER_S, /* String: server IP address to use for upload */
            CONFIG_UPLOAD_PORT_S,   /* String: port to use on server for upload */
            CONFIG_UPLOAD_TIMEOUT_S,/* String: timeout (seconds) before deciding that the server isn't available */
            CONFIG_UPLOAD_INTERVAL_S,/* String: interval (seconds) between upload attempts */
            CONFIG_UPLOAD_DURATION_S,/* String: duration (seconds) for each upload event */
            CONFIG_UPLOAD_CERT_S,   /* String: certificate to pass to upload server for authentication */
            CONFIG_MDNS_NAME_S      /* String: recognition name for mDNS responder (hostname: name.local) */
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

/// \class ConfigJSON
/// \brief Configuration adapter for JSON-format load/save
///
/// The configuration information is typically kept as a simple key-value store in the NVM of
/// the logger.  Getting that information out to the outside world (either through the serial or
/// WiFi interfaces, or into a log file) is difficult, however, at least if you want it to have
/// some sort of useful structure.  This class acts as an adapter to the key-value store so that
/// it can be packaged as a JSON-structured string (along with some versioning information) to
/// make external transport simpler.

class ConfigJSON {
public:
    /// @brief Generate a serialised JSON dictionary as a String for all of the configuration parameters
    static DynamicJsonDocument ExtractConfig(bool secure = false);
    /// @brief Configure the logger from a serialsed JSON dictionary of the configuration parameters
    static bool SetConfig(String const& json_string);
    /// \brief Establish a "known stable" configuration if the current configuration is not valid
    static bool SetStableConfig(void);
};

}

#endif
