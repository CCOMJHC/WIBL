/*! \file Configuration.cpp
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

#include <Arduino.h>
#include "Configuration.h"
#include "ArduinoJson.h"
#include "N0183Logger.h"
#include "N2kLogger.h"
#include "SerialCommand.h"
#include "IMULogger.h"

namespace logger {

/// Generate a printable version of the software version for the logger firmware entire.  Note that
/// this is distinct from the version of the Command Processor, any of the loggers, and of the
/// serialiser.  This is mostly just to indicate what assembly of the components was present at the
/// time the firmware was released for "production".
///
/// @return String containing the major.minor.patch for the system

String FirmwareVersion(void)
{
    String r = String(firmware_major) + "." + String(firmware_minor) + "." + String(firmware_patch);
    return r;
}

// Lookup table to translate the Enums in logger::Config::ConfigParam into the strings used to look
// up the keys in ParamStore.  This list has to be in exactly the same order as the elements in the
// Enum, of course, or everything will fall apart.

const String lookup[] = {
    "N1Enable",         ///< Control logging of NMEA0183 data (binary)
    "N2Enable",         ///< Control logging of NMEA2000 data (binary)
    "IMUEnable",        ///< Control logging of motion sensor data (binary)
    "PowMon",           ///< Control whether power monitoring and emergency shutdown is done (binary)
    "MemModule",        ///< Control whether SD/MMC or SPI is used to access the SD card (binary)
    "Bridge",           ///< Control whether to start the UDP->RS-422 bridge on WiFi startup (binary)
    "WebServer",        ///< Control whether to use the web server interface to configure the system (binary)
    "Upload",           ///< Control whether to auto-upload files when online (binary)
    "WifiOpenConnect",  ///< Control whether to enable Open WiFi Connect fallback (binary)
    "modid",            ///< Set the module's Unique ID (string)
    "shipname",         ///< Set the ship's name (string)
    "ap_ssid",          ///< Set the WiFi SSID (string)
    "ap_password",      ///< Set the WiFi password (string)
    "station_ssid",     ///< Set the WiFi SSID (string)
    "station_password", ///< Set the WiFi password (string)
    "ipaddress",        ///< Set the IP address assigned to the WiFI module (string)
    "wifimode",         ///< Set the WiFi mode (access point, station) to start in (string)
    "baud1",            ///< Set the baud rate of NMEA0183 input channel 1
    "baud2",            ///< Set the baud rate of NMEA0183 input channel 2
    "BridgePort",       ///< Set the UDP port for broadcast packets to bridge to RS-422 (string)
    "StationDelay",     ///< Set the timeout between attempts of the webserver joining a client network
    "StationRetries",   ///< Set number of join attempts before the webserver reverts to safe mode
    "StationTimeout",   ///< Set the timeout for any connect attempt
    "WSStatus",         ///< The current status of the configuration webserver
    "WSBootStatus",     ///< The status of the webserver on boot
    "LabDefaults",      ///< A JSON string for lab-default configuration
    "UploadToken",      ///< An ASCII string to authenticate uploads
    "UploadServer",     ///< IPv4 address for the server to use for upload
    "UploadPort",       ///< IPc4 port for server to use for upload
    "UploadTimeout",    ///< Timeout (seconds) for the upload server to respond to probe
    "UploadInterval",   ///< Interval (seconds) between upload attempts
    "UploadDuration",   ///< Time (seconds) for upload activity before diverting back to other efforts
    "UploadCert",       ///< Certificate to pass to the upload server for TLS
    "UploadWifiSsid1",  ///< Preset WiFi SSID 1 for upload connectivity
    "UploadWifiSsid2",  ///< Preset WiFi SSID 2 for upload connectivity
    "UploadWifiSsid3",  ///< Preset WiFi SSID 3 for upload connectivity
    "UploadWifiSsid4",  ///< Preset WiFi SSID 4 for upload connectivity
    "UploadWifiSsid5",  ///< Preset WiFi SSID 5 for upload connectivity
    "UploadWifiPass1",  ///< Preset WiFi password 1 for upload connectivity
    "UploadWifiPass2",  ///< Preset WiFi password 2 for upload connectivity
    "UploadWifiPass3",  ///< Preset WiFi password 3 for upload connectivity
    "UploadWifiPass4",  ///< Preset WiFi password 4 for upload connectivity
    "UploadWifiPass5",  ///< Preset WiFi password 5 for upload connectivity
    "UploadIgnoredSsid1", ///< WiFi SSID 1 to ignore for upload
    "UploadIgnoredSsid2", ///< WiFi SSID 2 to ignore for upload
    "UploadIgnoredSsid3", ///< WiFi SSID 3 to ignore for upload
    "UploadIgnoredSsid4", ///< WiFi SSID 4 to ignore for upload
    "UploadIgnoredSsid5", ///< WiFi SSID 5 to ignore for upload
    "mDNSName"
};

/// Default constructor.  This sets up for a dummy parameter store, which is configured
/// on the first instance it's called, to avoid committing the memory until it's actually
/// required.

Config::Config(void)
{
    m_params = nullptr;
}

/// Default destructor.  Simply removes the parameter store interface, if configured.

Config::~Config(void)
{
    delete m_params;
}

bool Config::IsValid(void)
{
    String logger_uuid;
    GetConfigString(CONFIG_MODULEID_S, logger_uuid);
    if (logger_uuid == "") {
        return false;
    } else {
        return true;
    }
}

/// Extact a configuration string from the parameter store, if it exists (see ParamStore
/// for details).
///
/// \param param    Enum for the key to extract
/// \param value    Reference for where to store the associated value
/// \returns True if the key was successfully extracted, otherwise False

bool Config::GetConfigString(ConfigParam const param, String& value)
{
    String key;
    Lookup(param, key);
    return m_params->GetKey(key, value);
}

/// Set a configuration key's associated value string (see ParamStore for details).
///
/// \param param    Enum for the key to set
/// \param value    String to set as the key's associated value
/// \return True if the key was successfully extracted, otherwise False

bool Config::SetConfigString(ConfigParam const param, String const& value)
{
    String key;
    Lookup(param, key);
    return m_params->SetKey(key, value);
}

/// Extract a binary flag associated with the key provided, if it exists (see
/// ParamStore for details).
///
/// \param param    Enum for the key to extract
/// \param value    Reference for where to store the associated value
/// \return True if the key was extracted successfully, otherwise False

bool Config::GetConfigBinary(ConfigParam const param, bool& value)
{
    String key;
    Lookup(param, key);
    return m_params->GetBinaryKey(key, value);
}

/// Set a binary configuration key to the provided value.
///
/// \param param    Enum for the key to set
/// \param value    Value to set for the associated key
/// \return True if the key was set, otherwise False

bool Config::SetConfigBinary(ConfigParam const param, bool value)
{
    String key;
    Lookup(param, key);
    return m_params->SetBinaryKey(key, value);
}

/// Map from the Enum key for the parameter into the string used to look up the
/// parameter in the ParamStore.
///
/// \param param    Enum to convert into a standard string
/// \param key      Reference for where to store the key's string equivalent

void Config::Lookup(ConfigParam const param, String& key)
{
    if (m_params == nullptr) m_params = ParamStoreFactory::Create();
    key = lookup[static_cast<int>(param)];
}

Config LoggerConfig;    ///< Static parameter to use for lookups (rather than making them on the heap)

/// This reads all of the configuration parameters from the key-value store and structures them into
/// a JSON dictionary (e.g., keeping the WiFi parameters together), and then serialises them into a
/// \a String so that it can be readily sent to log files, or over WiFi, etc.  The serialisation can be
/// compact (e.g., for sending to files) or formatted (i.e., with indents) as required.
///
/// @param secure Set true to avoid writing password information into the output dictionary.
/// @return \a String object with the serialised JSON dictionary of configuration parameters.

DynamicJsonDocument ConfigJSON::ExtractConfig(bool secure)
{
    using namespace ArduinoJson;
    // Match SetConfig buffer: extended WiFi + upload preset fields need headroom.
    DynamicJsonDocument params(2048);
    params["version"]["firmware"] = FirmwareVersion();
    params["version"]["commandproc"] = SerialCommand::SoftwareVersion();
    params["version"]["nmea0183"] = nmea::N0183::Logger::SoftwareVersion();
    params["version"]["nmea2000"] = nmea::N2000::Logger::SoftwareVersion();
    params["version"]["imu"] = imu::Logger::SoftwareVersion();
    params["version"]["serialiser"] = Serialiser::SoftwareVersion();

    // Enable/disable for the various loggers and features
    bool nmea0183_enable, nmea2000_enable, imu_enable, powmon_enable, sdmmc_enable,
         udp_bridge_enable, webserver_on_boot, upload_online, wifi_openconnect;
    LoggerConfig.GetConfigBinary(Config::CONFIG_NMEA0183_B, nmea0183_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_NMEA2000_B, nmea2000_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_MOTION_B, imu_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_POWMON_B, powmon_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_SDMMC_B, sdmmc_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_BRIDGE_B, udp_bridge_enable);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_WEBSERVER_B, webserver_on_boot);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_UPLOAD_B, upload_online);
    LoggerConfig.GetConfigBinary(Config::ConfigParam::CONFIG_WIFI_OPENCONNECT_B, wifi_openconnect);
    params["enable"]["nmea0183"] = nmea0183_enable;
    params["enable"]["nmea2000"] = nmea2000_enable;
    params["enable"]["imu"] = imu_enable;
    params["enable"]["powermonitor"] = powmon_enable;
    params["enable"]["sdmmc"] = sdmmc_enable;
    params["enable"]["udpbridge"] = udp_bridge_enable;
    params["enable"]["webserver"] = webserver_on_boot;
    params["enable"]["upload"] = upload_online;

    // String configurations for the various parameters in configuration
    String wifi_station_delay, wifi_station_retries, wifi_station_timeout, wifi_ip_address, wifi_mode, wifi_status;
    String wifi_ap_ssid, wifi_ap_password, wifi_station_ssid, wifi_station_password, wifi_station_mdns_name;
    String moduleid, shipname, baudrate_port1, baudrate_port2, udp_bridge_port;

    LoggerConfig.GetConfigString(Config::CONFIG_STATION_DELAY_S, wifi_station_delay);
    LoggerConfig.GetConfigString(Config::CONFIG_STATION_RETRIES_S, wifi_station_retries);
    LoggerConfig.GetConfigString(Config::CONFIG_STATION_TIMEOUT_S, wifi_station_timeout);
    LoggerConfig.GetConfigString(Config::CONFIG_MODULEID_S, moduleid);
    LoggerConfig.GetConfigString(Config::CONFIG_SHIPNAME_S, shipname);
    LoggerConfig.GetConfigString(Config::CONFIG_AP_SSID_S, wifi_ap_ssid);
    LoggerConfig.GetConfigString(Config::CONFIG_AP_PASSWD_S, wifi_ap_password);
    LoggerConfig.GetConfigString(Config::CONFIG_STATION_SSID_S, wifi_station_ssid);
    LoggerConfig.GetConfigString(Config::CONFIG_STATION_PASSWD_S, wifi_station_password);
    LoggerConfig.GetConfigString(Config::CONFIG_MDNS_NAME_S, wifi_station_mdns_name);
    LoggerConfig.GetConfigString(Config::CONFIG_WIFIIP_S, wifi_ip_address);
    LoggerConfig.GetConfigString(Config::CONFIG_WIFIMODE_S, wifi_mode);
    LoggerConfig.GetConfigString(Config::CONFIG_WS_STATUS_S, wifi_status);
    LoggerConfig.GetConfigString(Config::CONFIG_BAUDRATE_1_S, baudrate_port1);
    LoggerConfig.GetConfigString(Config::CONFIG_BAUDRATE_2_S, baudrate_port2);
    LoggerConfig.GetConfigString(Config::CONFIG_BRIDGE_PORT_S, udp_bridge_port);
    params["wifi"]["mode"] = wifi_mode;
    params["wifi"]["openconnect"] = wifi_openconnect;
    params["wifi"]["address"] = wifi_ip_address;
    params["wifi"]["status"] = wifi_status;
    params["wifi"]["station"]["delay"] = wifi_station_delay.toInt();
    params["wifi"]["station"]["retries"] = wifi_station_retries.toInt();
    params["wifi"]["station"]["timeout"] = wifi_station_timeout.toInt();
    params["wifi"]["station"]["mdns"] = wifi_station_mdns_name;
    params["wifi"]["ssids"]["ap"] = wifi_ap_ssid;
    params["wifi"]["ssids"]["station"] = wifi_station_ssid;
    if (!secure) {
        params["wifi"]["passwords"]["ap"] = wifi_ap_password;
        params["wifi"]["passwords"]["station"] = wifi_station_password;
    }
    params["uniqueID"] = moduleid;
    params["shipname"] = shipname;
    params["baudrate"]["port1"] = baudrate_port1.toInt();
    params["baudrate"]["port2"] = baudrate_port2.toInt();
    params["udpbridge"] = udp_bridge_port.toInt();

    String upload_server, upload_port, upload_timeout, upload_interval, upload_duration;
    String upload_wifi_ssid1, upload_wifi_ssid2, upload_wifi_ssid3, upload_wifi_ssid4, upload_wifi_ssid5;
    String upload_wifi_pass1, upload_wifi_pass2, upload_wifi_pass3, upload_wifi_pass4, upload_wifi_pass5;
    String ignored_wifi_ssid1, ignored_wifi_ssid2, ignored_wifi_ssid3, ignored_wifi_ssid4, ignored_wifi_ssid5;
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_SERVER_S, upload_server);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_PORT_S, upload_port);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_TIMEOUT_S, upload_timeout);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_INTERVAL_S, upload_interval);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_DURATION_S, upload_duration);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID1_S, upload_wifi_ssid1);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID2_S, upload_wifi_ssid2);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID3_S, upload_wifi_ssid3);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID4_S, upload_wifi_ssid4);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID5_S, upload_wifi_ssid5);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS1_S, upload_wifi_pass1);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS2_S, upload_wifi_pass2);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS3_S, upload_wifi_pass3);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS4_S, upload_wifi_pass4);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS5_S, upload_wifi_pass5);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID1_S, ignored_wifi_ssid1);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID2_S, ignored_wifi_ssid2);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID3_S, ignored_wifi_ssid3);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID4_S, ignored_wifi_ssid4);
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID5_S, ignored_wifi_ssid5);
    params["upload"]["server"] = upload_server;
    params["upload"]["port"] = upload_port.toInt();
    params["upload"]["timeout"] = upload_timeout.toDouble();
    params["upload"]["interval"] = upload_interval.toDouble();
    params["upload"]["duration"] = upload_duration.toDouble();
    params["upload"]["wifiSsid1"] = upload_wifi_ssid1;
    params["upload"]["wifiSsid2"] = upload_wifi_ssid2;
    params["upload"]["wifiSsid3"] = upload_wifi_ssid3;
    params["upload"]["wifiSsid4"] = upload_wifi_ssid4;
    params["upload"]["wifiSsid5"] = upload_wifi_ssid5;
    if (!secure) {
        params["upload"]["wifiPass1"] = upload_wifi_pass1;
        params["upload"]["wifiPass2"] = upload_wifi_pass2;
        params["upload"]["wifiPass3"] = upload_wifi_pass3;
        params["upload"]["wifiPass4"] = upload_wifi_pass4;
        params["upload"]["wifiPass5"] = upload_wifi_pass5;
    }
    params["upload"]["ignoredWifiSsid1"] = ignored_wifi_ssid1;
    params["upload"]["ignoredWifiSsid2"] = ignored_wifi_ssid2;
    params["upload"]["ignoredWifiSsid3"] = ignored_wifi_ssid3;
    params["upload"]["ignoredWifiSsid4"] = ignored_wifi_ssid4;
    params["upload"]["ignoredWifiSsid5"] = ignored_wifi_ssid5;

    return params;
}

/// Set configuration for all values of the key-value store specified in the serialised JSON dictionary
/// provided at input.  The code here, to make sure that it knows what to expect in the JSON dictionary,
/// checks for a version string, which must match what the \a SerialCommand::SoftwareVersion() method
/// reports for the current firmware build to be acceptable.  The serialised dictionary can contain as
/// few or as many parameters as are required: only the parameters set are used for updating the current
/// configuration.
///
/// @param json_string \a String of the serialised JSON dictionary to use for configuration.
/// @return True if the configuration completed, otherwise false.

bool ConfigJSON::SetConfig(String const& json_string)
{
    // SSIDs, passwords, and upload fields can make the payload large.
    DynamicJsonDocument params(2048);
    if (deserializeJson(params, json_string) != DeserializationError::Ok)
        return false;

    if (!params.containsKey("version") || !params["version"].containsKey("commandproc")) {
        return false;
    }
    if (params["version"]["commandproc"].as<String>() == SerialCommand::SoftwareVersion()) {
        if (params.containsKey("enable")) {
            if (params["enable"].containsKey("nmea0183"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_NMEA0183_B, params["enable"]["nmea0183"].as<bool>());
            if (params["enable"].containsKey("nmea2000"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_NMEA2000_B, params["enable"]["nmea2000"].as<bool>());
            if (params["enable"].containsKey("imu"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_MOTION_B, params["enable"]["imu"].as<bool>());
            if (params["enable"].containsKey("powermonitor"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_POWMON_B, params["enable"]["powermonitor"].as<bool>());
            if (params["enable"].containsKey("sdmmc"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_SDMMC_B, params["enable"]["sdmmc"].as<bool>());
            if (params["enable"].containsKey("udpbridge"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_BRIDGE_B, params["enable"]["udpbridge"].as<bool>());
            if (params["enable"].containsKey("webserver"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_WEBSERVER_B, params["enable"]["webserver"].as<bool>());
            if (params["enable"].containsKey("upload"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_UPLOAD_B, params["enable"]["upload"].as<bool>());
        }
        if (params.containsKey("wifi")) {
            if (params["wifi"].containsKey("mode"))
                LoggerConfig.SetConfigString(Config::CONFIG_WIFIMODE_S, params["wifi"]["mode"].as<String>());
            if (params["wifi"].containsKey("openconnect"))
                LoggerConfig.SetConfigBinary(Config::CONFIG_WIFI_OPENCONNECT_B, params["wifi"]["openconnect"].as<bool>());
            if (params["wifi"].containsKey("station")) {
                if (params["wifi"]["station"].containsKey("delay"))
                    LoggerConfig.SetConfigString(Config::CONFIG_STATION_DELAY_S, params["wifi"]["station"]["delay"].as<String>());
                if (params["wifi"]["station"].containsKey("retries"))
                    LoggerConfig.SetConfigString(Config::CONFIG_STATION_RETRIES_S, params["wifi"]["station"]["retries"].as<String>());
                if (params["wifi"]["station"].containsKey("timeout"))
                    LoggerConfig.SetConfigString(Config::CONFIG_STATION_TIMEOUT_S, params["wifi"]["station"]["timeout"].as<String>());
                if (params["wifi"]["station"].containsKey("mdns"))
                    LoggerConfig.SetConfigString(Config::CONFIG_MDNS_NAME_S, params["wifi"]["station"]["mdns"].as<String>());
            }
            if (params["wifi"].containsKey("ssids")) {
                if (params["wifi"]["ssids"].containsKey("ap"))
                    LoggerConfig.SetConfigString(Config::CONFIG_AP_SSID_S, params["wifi"]["ssids"]["ap"].as<String>());
                if (params["wifi"]["ssids"].containsKey("station"))
                    LoggerConfig.SetConfigString(Config::CONFIG_STATION_SSID_S, params["wifi"]["ssids"]["station"].as<String>());
            }
            if (params["wifi"].containsKey("passwords")) {
                if (params["wifi"]["passwords"].containsKey("ap"))
                    LoggerConfig.SetConfigString(Config::CONFIG_AP_PASSWD_S, params["wifi"]["passwords"]["ap"].as<String>());
                if (params["wifi"]["passwords"].containsKey("station"))
                    LoggerConfig.SetConfigString(Config::CONFIG_STATION_PASSWD_S, params["wifi"]["passwords"]["station"].as<String>());
            }
        }
        if (params.containsKey("baudrate")) {
            if (params["baudrate"].containsKey("port1"))
                LoggerConfig.SetConfigString(Config::CONFIG_BAUDRATE_1_S, params["baudrate"]["port1"].as<String>());
            if (params["baudrate"].containsKey("port2"))
                LoggerConfig.SetConfigString(Config::CONFIG_BAUDRATE_2_S, params["baudrate"]["port2"].as<String>());
        }
        if (params.containsKey("uniqueID"))
            LoggerConfig.SetConfigString(Config::CONFIG_MODULEID_S, params["uniqueID"].as<String>());
        if (params.containsKey("shipname"))
            LoggerConfig.SetConfigString(Config::CONFIG_SHIPNAME_S, params["shipname"].as<String>());
        if (params.containsKey("udpbridge"))
            LoggerConfig.SetConfigString(Config::CONFIG_BRIDGE_PORT_S, params["udpbridge"].as<String>());
        if (params.containsKey("upload")) {
            if (params["upload"].containsKey("server"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_SERVER_S, params["upload"]["server"].as<String>());
            if (params["upload"].containsKey("port"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_PORT_S, params["upload"]["port"].as<String>());
            if (params["upload"].containsKey("timeout"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_TIMEOUT_S, params["upload"]["timeout"].as<String>());
            if (params["upload"].containsKey("interval"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_INTERVAL_S, params["upload"]["interval"].as<String>());
            if (params["upload"].containsKey("duration"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_DURATION_S, params["upload"]["duration"].as<String>());
            if (params["upload"].containsKey("wifiSsid1"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID1_S, params["upload"]["wifiSsid1"].as<String>());
            if (params["upload"].containsKey("wifiSsid2"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID2_S, params["upload"]["wifiSsid2"].as<String>());
            if (params["upload"].containsKey("wifiSsid3"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID3_S, params["upload"]["wifiSsid3"].as<String>());
            if (params["upload"].containsKey("wifiSsid4"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID4_S, params["upload"]["wifiSsid4"].as<String>());
            if (params["upload"].containsKey("wifiSsid5"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_SSID5_S, params["upload"]["wifiSsid5"].as<String>());
            if (params["upload"].containsKey("wifiPass1"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS1_S, params["upload"]["wifiPass1"].as<String>());
            if (params["upload"].containsKey("wifiPass2"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS2_S, params["upload"]["wifiPass2"].as<String>());
            if (params["upload"].containsKey("wifiPass3"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS3_S, params["upload"]["wifiPass3"].as<String>());
            if (params["upload"].containsKey("wifiPass4"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS4_S, params["upload"]["wifiPass4"].as<String>());
            if (params["upload"].containsKey("wifiPass5"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_WIFI_PASS5_S, params["upload"]["wifiPass5"].as<String>());
            if (params["upload"].containsKey("ignoredWifiSsid1"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID1_S, params["upload"]["ignoredWifiSsid1"].as<String>());
            if (params["upload"].containsKey("ignoredWifiSsid2"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID2_S, params["upload"]["ignoredWifiSsid2"].as<String>());
            if (params["upload"].containsKey("ignoredWifiSsid3"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID3_S, params["upload"]["ignoredWifiSsid3"].as<String>());
            if (params["upload"].containsKey("ignoredWifiSsid4"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID4_S, params["upload"]["ignoredWifiSsid4"].as<String>());
            if (params["upload"].containsKey("ignoredWifiSsid5"))
                LoggerConfig.SetConfigString(Config::CONFIG_UPLOAD_IGNORED_SSID5_S, params["upload"]["ignoredWifiSsid5"].as<String>());
        }
    } else {
        return false;
    }
    return true;
}

static const char *stable_config = "{\"version\": {\"commandproc\": \"1.4.2\"}, \"enable\": {\"nmea0183\": true, \"nmea2000\": true, \"imu\": false, \"powermonitor\": false, \"sdmmc\": false, \"udpbridge\": false, \"webserver\": true, \"upload\": false}, \"wifi\": {\"mode\": \"AP\", \"openconnect\": false, \"address\": \"192.168.4.1\", \"station\": {\"delay\": 20, \"retries\": 5, \"timeout\": 5, \"mdns\": \"wibl\"}, \"ssids\": {\"ap\": \"wibl-config\", \"station\": \"wibl-logger\"}, \"passwords\": {\"ap\": \"wibl-config-password\", \"station\": \"wibl-logger-password\"}}, \"uniqueID\": \"TNODEID\", \"shipname\": \"Anonymous\", \"baudrate\": {\"port1\": 4800, \"port2\": 4800}, \"udpbridge\": 12345, \"upload\": {\"server\": \"192.168.4.2\", \"port\": 80, \"timeout\": 5.0, \"interval\": 1800.0, \"duration\": 10.0, \"wifiSsid1\": \"\", \"wifiSsid2\": \"\", \"wifiSsid3\": \"\", \"wifiSsid4\": \"\", \"wifiSsid5\": \"\", \"wifiPass1\": \"\", \"wifiPass2\": \"\", \"wifiPass3\": \"\", \"wifiPass4\": \"\", \"wifiPass5\": \"\", \"ignoredWifiSsid1\": \"\", \"ignoredWifiSsid2\": \"\", \"ignoredWifiSsid3\": \"\", \"ignoredWifiSsid4\": \"\", \"ignoredWifiSsid5\": \"\"}}";

bool ConfigJSON::SetStableConfig(void)
{
    if (LoggerConfig.IsValid()) {
        return true;
    } else {
        Serial.println("INF: Configuration not valid; setting default configuration for first boot/bad config.");
        return SetConfig(String(stable_config));
    }
}

}