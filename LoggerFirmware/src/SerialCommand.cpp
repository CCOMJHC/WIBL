/*! \file SerialCommand.cpp
 * \brief Implementation for command line processing for the application
 *
 * The logger takes commands on the serial input line from the user application (or
 * the user if it's connected to a terminal).  This code generates the implementation for executing
 * executing those commands.
 *
 * Copyright (c) 2019, University of New Hampshire, Center for Coastal and Ocean Mapping.
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
#include "ArduinoJson.h"
#include "WiFiAdapter.h"
#include "SerialCommand.h"
#include "IncrementalBuffer.h"
#include "OTAUpdater.h"
#include "Configuration.h"
#include "HeapMonitor.h"
#include "NVMFile.h"
#include "IMULogger.h"
#include "DataMetrics.h"
#include "Status.h"

const uint32_t CommandMajorVersion = 1;
const uint32_t CommandMinorVersion = 4;
const uint32_t CommandPatchVersion = 1;

/// Default constructor for the SerialCommand object.  This stores the pointers for the logger and
/// status LED controllers for reference, and then generates a BLE service object.  This turns on
/// advertising for the BLE UART service, allowing for data to the sent and received over the air.
///
/// \param CANLogger    Pointer to the NMEA2000 data source
/// \param serialLogger Pointer to the NMEA0183 data source
/// \param logManager   Pointer to the object used to access the log files
/// \param led          Pointer to the status LED controller object

SerialCommand::SerialCommand(nmea::N2000::Logger *CANLogger, nmea::N0183::Logger *serialLogger,
                             logger::Manager *logManager, StatusLED *led)
: m_CANLogger(CANLogger), m_serialLogger(serialLogger), m_logManager(logManager), m_led(led), m_echoOn(true), m_passThrough(false)
{
    logger::HeapMonitor heap;

    Serial.printf("DBG: Before SerialCommand setup, heap free = %d B\n", heap.CurrentSize());

    m_serialBuffer.ResetLength(1024);

    // WiFi always gets created, since we'll need it eventually to get data off.  The only question is
    // whether it gets started when the system first somes up or not.
    m_wifi = WiFiAdapterFactory::Create();

    Serial.printf("DBG: After WiFi interface create, heap free = %d B, delta = %d B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());
    bool start_wifi;
    if (logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_WEBSERVER_B, start_wifi)
        && start_wifi) {
        if (m_wifi->Startup()) {
            Serial.printf("DBG: After WiFi interface start, heap free = %d B, delta = %d B\n",
                heap.CurrentSize(), heap.DeltaSinceLast());

            bool start_bridge;
            logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_BRIDGE_B, start_bridge);
            if (start_bridge) {
                m_bridge = new nmea::N0183::PointBridge();

                Serial.printf("DBG: After UDP bridge start, heap free = %d B, delta = %d B\n",
                    heap.CurrentSize(), heap.DeltaSinceLast());
            } else {
                m_bridge = nullptr;
            }

            bool start_autoupload;
            logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_UPLOAD_B, start_autoupload);
            if (start_autoupload) {
                m_uploadManager = new net::UploadManager(m_logManager);
                Serial.printf("DBG: After UploadManager start, heap free = %d B, delta = %d B\n",
                    heap.CurrentSize(), heap.DeltaSinceLast());
            } else {
                m_uploadManager = nullptr;
            }
        } else {
            Serial.printf("ERR: Failed to start WiFi interface.\n");
        }
    }
}

/// Default destructor for the SerialCommand object.  This deallocates the BLE service object,
/// which will force a disconnect.  Note that the pointer references for the logger and status LED
/// objects are not deallocated.

SerialCommand::~SerialCommand()
{
    delete m_uploadManager;
    delete m_bridge;
    delete m_wifi;
}

/// Generate a string representation of the version information for the
/// command processor.
///
/// \return String for the version information

String SerialCommand::SoftwareVersion(void)
{
    char buffer[32];
    snprintf(buffer, 32, "%d.%d.%d", CommandMajorVersion, CommandMinorVersion, CommandPatchVersion);
    return String(buffer);
}

/// Generate a copy of the console log (/console.log in the root directory of the attached SD card)
/// on the output serial stream, and the BLE stream if there is something connected to it.  Sending
/// things to the BLE stream can be slow since there needs to be a delay between packets to avoid
/// congestion on the stack.
///
/// \param src  Stream by which the command arrived

void SerialCommand::ReportConsoleLog(CommandSource src)
{
    switch (src) {
        case CommandSource::SerialPort:
            Serial.println("*** Current console log start.");
            m_logManager->DumpConsoleLog(Serial);
            Serial.println("*** Current console log end.");
            break;
        case CommandSource::WirelessPort:
            Serial.println("ERR: cannot stream console log to WiFi web server.");
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}

/// Report the version string for the current logger implementation.  This also goes out on
/// the BLE interface if there's a client connected.
///
/// \param src  Stream by which the command arrived

void SerialCommand::ReportSoftwareVersion(CommandSource src)
{
    EmitMessage(String("Firmware:          ") + logger::FirmwareVersion() + "\n", src);
    EmitMessage(String("Serialiser:        ") + Serialiser::SoftwareVersion() + "\n", src);
    EmitMessage(String("Command Processor: ") + SoftwareVersion() + "\n", src);
    EmitMessage(String("NMEA2000:          ") + nmea::N2000::Logger::SoftwareVersion() + "\n", src);
    EmitMessage(String("NMEA0183:          ") + nmea::N0183::Logger::SoftwareVersion() + "\n", src);
    EmitMessage(String("IMU:               ") + imu::Logger::SoftwareVersion() + "\n", src);
}

/// Erase one, or all, of the log files currently on the SD card.  If the string is "all", all
/// files are removed, including the current one (i.e., the logger stops, removes the file,
/// then re-starts a new one).  Otherwise the string is converted to an integer, and that
/// file is removed if it exists.  Confirmation messages are send out to serial and BLE if
/// there is a client connected.
///
/// \param filenum  String representation of the file number of the log file to remove, or "all"
/// \param src      Stream by which the command arrived

void SerialCommand::EraseLogfile(String const& filenum, CommandSource src)
{
    bool success = true;
    long file_num = -1;
    if (filenum == "all") {
        m_logManager->RemoveAllLogfiles();
    } else {
        file_num = filenum.toInt();
        if (!m_logManager->RemoveLogFile(file_num)) {
            success = false;
        }
    }
    if (success) {
        ReportCurrentStatus(src);
    } else {
        String msg = String("Failed to erase log file ") + file_num + "\n";
        if (m_wifi != nullptr) m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::NOTFOUND);
        EmitMessage(msg, src);
    }
}

/// Set the state of the status LEDs.  One or more LEDs can be associated with the logger,
/// and a set of status colours and patterns can be set by the logger as it runs to indicate
/// different conditions.  For debugging purposes, this code allows the user to set the state
/// directly.  Allowed states are "normal", "error", "initialising", and "full".
///
/// \param command  Command string for LED status to set

void SerialCommand::ModifyLEDState(String const& command)
{
    if (command == "normal") {
        m_led->SetStatus(StatusLED::Status::sNORMAL);
    } else if (command == "error") {
        m_led->SetStatus(StatusLED::Status::sFATAL_ERROR);
    } else if (command == "initialising") {
        m_led->SetStatus(StatusLED::Status::sINITIALISING);
    } else if (command == "full") {
        m_led->SetStatus(StatusLED::Status::sCARD_FULL);
    } else if (command == "data") {
        m_led->TriggerDataIndication();
    } else if (command == "stopped") {
        m_led->SetStatus(StatusLED::Status::sSTOPPED);
    } else {
        Serial.println("ERR: LED status command not recognised.");
    }
}

/// Report the identification string that the user set for the logger.  This is expected to be
/// a unique ID that can be used to identify the logger, but the firmware does not enforce any
/// particular structure for the string.  The output goes to the BLE UART service if there is a
/// client connected.
///
/// \param src      Stream by which the command arrived

void SerialCommand::ReportIdentificationString(CommandSource src)
{
    if (src == CommandSource::SerialPort) EmitMessage("Module identification string: ", src);
    String id;
    if (logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_MODULEID_S, id)) {
        EmitMessage(id + "\n", src);
    } else {
        EmitMessage("UNKNOWN\n", src);
    }
}

/// Set the identification string for the logger.  This is expected to be a unique ID that can be
/// used to identify the logger, but the firmware does not enforce any particular structure for
/// the string, simply recording whatever is provided.  The string is persisted in non-volatile
/// memory on the board so that it is always available.
///
/// \param identifier   String to use to identify the logger

void SerialCommand::SetIdentificationString(String const& identifier, CommandSource src)
{
    if (logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_MODULEID_S, identifier)) {
        if (src == CommandSource::SerialPort) {
            EmitMessage("INF: UUID accepted.\n", src);
        } else {
            ReportConfigurationJSON(src);
        }
    } else {
        EmitMessage("ERR: module identification string file failed to write.", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr)
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
    }
}

/// Report the ship-name installed in the logger.  This is usually the actual name of the ship
/// hosting the logger, but can be "Anonymous", and if not set, reports "UNKNOWN".
///
/// @param src Channel on which to report the information
/// @return N/A

void SerialCommand::ReportShipname(CommandSource src)
{
    if (src == CommandSource::SerialPort) EmitMessage("Shipname: ", src);
    String id;
    if (logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_SHIPNAME_S, id)) {
        EmitMessage(id + "\n", src);
    } else {
        EmitMessage("UNKNOWN\n", src);
    }
}

/// Set the ship-name.  This is usually the actual name of the ship hosting the logger, but can be
/// anything the user requires, including "Anonymous" if required.  The code simply stores what's
/// provided, and imposes no required structure on the name.  The code generates an error message if
/// the name cannot be stored for any reason (that would usually be a NVM failure), but reports
/// confirmation (configuration JSON on WiFi) on success.
///
/// @param name Name to use for the host platform
/// @param src  Channel on which to report confimation
/// @return N/A

void SerialCommand::SetShipname(String const& name, CommandSource src)
{
    if (logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_SHIPNAME_S, name)) {
        if (src == CommandSource::SerialPort) {
            EmitMessage("INF: Shipname accepted.\n", src);
        } else {
            ReportConfigurationJSON(src);
        }
    } else {
        EmitMessage("ERR: shipname string failed to write.", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr)
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
    }
}

/// Set up for verbose reporting of messages received by the logger from the NMEA2000 bus.  This
/// is useful only for debugging, since it generates a lot of traffic on the serial output stream.  Allowable
/// options are "on" and "off".
///
/// \param mode String with "on" or "off" to configure verbose reporting mode

void SerialCommand::SetVerboseMode(String const& mode)
{
    if (mode == "on") {
        if (m_CANLogger != nullptr) m_CANLogger->SetVerbose(true);
        if (m_serialLogger != nullptr) m_serialLogger->SetVerbose(true);
        if (m_bridge != nullptr) m_bridge->SetVerbose(true);
    } else if (mode == "off") {
        if (m_CANLogger != nullptr) m_CANLogger->SetVerbose(false);
        if (m_serialLogger != nullptr) m_serialLogger->SetVerbose(false);
        if (m_bridge != nullptr) m_bridge->SetVerbose(false);
    } else {
        Serial.println("ERR: verbose mode not recognised.");
    }
}

/// Shut down the logger for safe removal of power (typically as part of the power monitoring)
/// so that the log files are completed before the power goes off.  This code shuts down the
/// current log file, and the console file, and then just busy waits for the power to go down.

void SerialCommand::Shutdown(void)
{
    m_logManager->CloseLogfile();
    Serial.println("info: Stopping under control for powerdown");
    m_logManager->Syslog("INF: Stopping under control for powerdown.");
    m_logManager->CloseConsole();
    m_led->SetStatus(StatusLED::Status::sSTOPPED);
    while (true) {
        delay(1000);
    }
    // Intentionally never completes - this is where the code halts
    // for power-down.
}

/// Specify the SSID string to use for the WiFi interface.
///
/// \param ssid SSID to use for the WiFi, when activated

void SerialCommand::SetWiFiSSID(String const& params, CommandSource src)
{
    int position = params.indexOf(" ") + 1;
    String ssid = params.substring(position);
    if (params.startsWith("ap")) {
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_AP_SSID_S, ssid);
    } else if (params.startsWith("station")) {
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, ssid);
    } else {
        EmitMessage("ERR: WiFi SSID must specify 'ap' or 'station' as first parameter.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr)
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        return;
    }
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src, true);
    }
}

/// Report the SSID for the WiFi on the output channel(s)
///
/// \param src      Stream by which the command arrived

void SerialCommand::GetWiFiSSID(CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        String ap_ssid, station_ssid;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_SSID_S, ap_ssid);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, station_ssid);
        EmitMessage("WiFi AP SSID: " + ap_ssid + "\n", src);
        EmitMessage("WiFi Station SSID: " + station_ssid + "\n", src);
    } else if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src, true);
    } else {
        EmitMessage("ERR: command source not recognised - who are you?\n", src);
    }
}

/// Specify the password to use for clients attempting to connect to the WiFi access
/// point offered by the module.
///
/// \param password Pre-shared password to expect from the client

void SerialCommand::SetWiFiPassword(String const& params, CommandSource src)
{
    int position = params.indexOf(" ") + 1;
    String password = params.substring(position);
    if (password.length() < 8 || password.length() > 64) {
        EmitMessage("ERR: WiFi password must be in range [8,64] characters.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    if (params.startsWith("ap")) {
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_AP_PASSWD_S, password);
    } else if (params.startsWith("station")) {
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_PASSWD_S, password);
    } else {
        EmitMessage("ERR: WiFi password must specify 'ap' or 'station' as first parameter.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src, true);
    }
}

/// Report the pre-shared password for the WiFi access point.
///
/// \param src      Stream by which the command arrived

void SerialCommand::GetWiFiPassword(CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        String ap_password, station_password;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_PASSWD_S, ap_password);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_PASSWD_S, station_password);
        EmitMessage("WiFi AP Password: " + ap_password + "\n", src);
        EmitMessage("WiFi Station Password: " + station_password + "\n", src);
    } else if (src == CommandSource::WirelessPort) {
         ReportConfigurationJSON(src, true);
    } else {
        EmitMessage("ERR: command source not recognised - who are you?\n", src);
    }
}

/// Set the mDNS responder name for the WiFi system
///
/// \param params   String containing the remainder of the parameters from the command
/// \param src      Stream by which the command arrived

void SerialCommand::SetMDNSName(String const& params, CommandSource src)
{
    if (params.length() < 2) {
        EmitMessage("ERR: mDNS responder name must be two or more characters.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_MDNS_NAME_S, params);
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src, true);
    }
}

/// Report the mDNS responder name for the WiFi system
///
/// \param src  Stream by which the command arrived

void SerialCommand::GetMDNSName(CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        String mdns_name;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_MDNS_NAME_S, mdns_name);
        EmitMessage("WiFi mDNS responder name: " + mdns_name + "\n", src);
    } else if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src, true);
    } else {
        EmitMessage("ERR: command source not recognised - who are you?!\n", src);
    }
}

/// Turn the WiFi interface on and off, as required by the user
///
/// \param  command     The remnant of the command string from the user
/// \param  src     Stream by which the command arrived

void SerialCommand::ManageWireless(String const& command, CommandSource src)
{
    if (command == "on") {
        if (src == CommandSource::SerialPort) {
            logger::HeapMonitor heap;
            Serial.printf("DBG: Before starting WiFi, heap free = %d B\n", heap.CurrentSize());
            if (m_wifi->Startup()) {
                EmitMessage("WiFi started on ", src);
                String ip_address;
                logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WIFIIP_S, ip_address);
                EmitMessage(ip_address + "\n", src);
                Serial.printf("DBG: After WiFi startup, heap fee = %d B, delta = %d B\n", heap.CurrentSize(), heap.DeltaSinceLast());
                
                bool start_bridge;
                logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_BRIDGE_B, start_bridge);
                if (start_bridge) {
                    if (m_bridge == nullptr)
                        m_bridge = new nmea::N0183::PointBridge();
                    Serial.printf("DBG: After UDP bridge start, heap free = %d B, delta = %d B\n", heap.CurrentSize(), heap.DeltaSinceLast());
                } else {
                    m_bridge = nullptr;
                }
            } else {
                Serial.println("ERR: WiFi startup failed");
            }
        } else {
            EmitMessage("ERR: manual wireless startup can only be done on serial line.", src);
            if (src == CommandSource::WirelessPort && m_wifi != nullptr)
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::UNAVAILABLE);
            return;
        }
    } else if (command == "off") {
        if (src == CommandSource::SerialPort) {
            logger::HeapMonitor heap;
            Serial.printf("DBG: Before stopping WiFi, heap free = %d B\n", heap.CurrentSize());

            m_wifi->Shutdown();
            Serial.println("WiFi stopped.");
            Serial.printf("DBG: After WiFi stopped, heap free = %d B, delta = %d B\n", heap.CurrentSize(), heap.DeltaSinceLast());
            if (m_bridge != nullptr) {
                delete m_bridge;
                m_bridge = nullptr;
                Serial.printf("DBG: After UDP bridge stopped, heap free = %d B, delta = %d B\n", heap.CurrentSize(), heap.DeltaSinceLast());
            }
        } else {
            EmitMessage("ERR: manual wireless shutdown can only be done on serial line.", src);
            if (src == CommandSource::WirelessPort && m_wifi != nullptr)
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::UNAVAILABLE);
            return;
        }
    } else if (command == "accesspoint") {
        m_wifi->SetWirelessMode(WiFiAdapter::WirelessMode::ADAPTER_SOFTAP);
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, "AP-Enabled");
    } else if (command == "station") {
        m_wifi->SetWirelessMode(WiFiAdapter::WirelessMode::ADAPTER_STATION);
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, "Station-Enabled");
    } else {
        EmitMessage("ERR: wireless management command not recognised.", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr)
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        return;
    }
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    }
}

/// Send a log file to the client (so long as it isn't on BLE, which is way too slow!).  This sends
/// plain binary 8-bit data to the client, which needs to know how to deal with that.  This
/// generally means it really only works on the WiFi connection.
///
/// \param filenum      Log file number to transfer
/// \param src      Stream by which the command arrived.

void SerialCommand::TransferLogFile(String const& filenum, CommandSource src)
{
    String          filename;
    uint32_t        filesize;
    uint16_t        uploadCount;
    uint32_t        file_number = filenum.toInt();
    logger::Manager::MD5Hash filehash;
    unsigned long   tx_start, tx_end, tx_duration;
   
    m_logManager->EnumerateLogFile(file_number, filename, filesize, filehash, uploadCount);
    if (filesize == 0) {
        // This implies File Not Found (since all log files have at least the serialiser
        // version information in them).
        EmitMessage("ERR: File " + filenum + " does not exist.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::NOTFOUND);
        }
        return;
    }
    if (filehash.Empty()) {
        // This can happen if the automated hash construction (in the logger::Manager::Inventory)
        // is not running for some reason.
        m_logManager->HashFile(file_number, filehash);
    }
    switch (src) {
        case CommandSource::SerialPort:
            m_logManager->TransferLogFile(file_number, filehash, Serial);
            break;
        case CommandSource::WirelessPort:
            Serial.printf("DBG: Transferring \"%s\", total %u bytes.\n", filename.c_str(), filesize);
            tx_start = millis();
            m_wifi->TransferFile(filename, filesize, filehash);
            tx_end = millis();
            tx_duration = (tx_end - tx_start) / 1000;
            Serial.printf("DBG: Transferred in %lu seconds.\n", tx_duration);
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}

/// Configure whether to invert the bits on either of the NMEA0183 serial ports, in hardware, prior
/// to reception.   This can be used to compensate for reverse polarity connections on the NMEA0183
/// inputs, which is a common problem in intallation.
///
/// \param params   Parameters string for the command: on | off <port-number>
/// \param src      Channel to report information on (Serial, WiFi, BLE)

void SerialCommand::ConfigureSerialPortInvert(String const& params, CommandSource src)
{
    uint32_t    port;
    bool        invert;
    
    if (m_serialLogger == nullptr) {
        EmitMessage("ERR: NMEA0183 logger disabled, cannot run command.\n", src);
        return;
    }
    if (params.startsWith("on")) {
        invert = true;
        port = params.substring(3).toInt();
    } else if (params.startsWith("off")) {
        invert = false;
        port = params.substring(4).toInt();
    } else {
        EmitMessage("ERR: bad command; Syntax: invert on|off <port>\n", src);
        return;
    }
    m_serialLogger->SetRxInvert(port, invert);
}

/// Set up the baud rate for either of the NMEA0183 serial ports.  By default, this should be
/// 4800 baud, as specified in NMEA0183, but some systems run at different rates, and it's
/// possible that this might need to configured.
///
/// \param params   Parameters for the command: <port-number> <baud-rate>
/// \param src      Channel to report information on (Serial, WiFi, BLE)

void SerialCommand::ConfigureSerialPortSpeed(String const& params, CommandSource src)
{
    uint32_t port;
    String baud_rate_str;
    uint32_t baud_rate;
    logger::Config::ConfigParam channel;
    
    if (m_serialLogger == nullptr) {
        EmitMessage("WARN: NMEA0183 logger disabled, expect no effect from this command.\n", src);
    }
    port = params.substring(0,1).toInt();
    if (port == 1 || port == 2) {
        if (port == 1)
            channel = logger::Config::ConfigParam::CONFIG_BAUDRATE_1_S;
        else
            channel = logger::Config::ConfigParam::CONFIG_BAUDRATE_2_S;
    } else {
        EmitMessage("ERR: serial channel must be in {1,2}.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    baud_rate_str = params.substring(2);
    baud_rate = static_cast<uint32_t>(baud_rate_str.toInt());
    if (baud_rate < 4800 || baud_rate > 115200) {
        EmitMessage("ERR: baud rate implausible; ignoring command.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    logger::LoggerConfig.SetConfigString(channel, baud_rate_str);
    if (src == CommandSource::SerialPort) {
        EmitMessage("INFO: speed set, remember to reboot to have this take effect.\n", src);
    } else if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    } else {
        EmitMessage("ERR: command source not recognised - who are you?\n", src);
    }
}

/// General interface to set up whether the various data interfaces and optional modules are actually
/// actively being recorded or used, respecitvely, on the logger.  Interfaces include:
///     nmea2000    on | off                NMEA2000 CAN-bus data
///     nmea0183    on | off                NMEA0183 RS-422 data
///     imu         on | off                MPU-6050 motion sensor data
///     power       on | off                Power monitoring and emergency shutdown
///     sdio        on | off                SD/MMC interface for SD card (otherwise SPI)
///     bridge      on <port-number> | off  UDP->RS-422 bridge (port number for the UDP broadcast packet)
///
/// \param params   Parameters for the command: on|off <optional>
/// \param src      Channel to report information on (Serial, WiFi, BLE)

void SerialCommand::ConfigureLoggers(String const& params, CommandSource src)
{
    String  logger;
    bool    state;
    int     position;

    if (params.startsWith("on")) {
        state = true;
        position = 3;
    } else if (params.startsWith("off")) {
        state = false;
        position = 4;
    } else {
        EmitMessage("ERR: loggers can be configured 'on' or 'off' only.\n", src);
        return;
    }
    logger = params.substring(position);

    if (logger.startsWith("nmea2000")) {
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA2000_B, state);
    } else if (logger.startsWith("nmea0183")) {
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA0183_B, state);
    } else if (logger.startsWith("imu")) {
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_MOTION_B, state);
    } else if (logger.startsWith("power")) {
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_POWMON_B, state);
    } else if (logger.startsWith("sdio")) {
#ifndef DEBUG_NEMO30
        if (!state) {
            EmitMessage("ERR: cannot turn off SDIO memory card interface for this logger.\n", src);
            state = true;
        }
#endif
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_SDMMC_B, state);
    } else if (logger.startsWith("bridge")) {
        if (state) {
            // If we're configuring on, then there should also be a port number
            String port = logger.substring(7);
            uint16_t port_number = port.toInt();
            if (port_number < 1024) {
                EmitMessage("ERR: UDP bridge port is not valid.\n", src);
                return;
            }
            logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_BRIDGE_PORT_S, port);
        }
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_BRIDGE_B, state);
    } else {
        EmitMessage("ERR: logger name not recognised.\n", src);
    }
}

/// Set whether the logger echos back characters to the host on the interface so that humans can see
/// what they're typing.
///
/// \param params   Parameters for the command: on | off
/// \param src      Channel on which to report the results (Serial, WiFi, BLE)

void SerialCommand::ConfigureEcho(String const& params, CommandSource src)
{
    if (params.startsWith("on")) {
        EchoOn();
    } else if (params.startsWith("off")) {
        EchoOff();
    } else {
        EmitMessage("ERR: echo can be turned 'on' or 'off' only.\n", src);
    }
}

/// Stealth command to turn on "pass through" mode for the logger, which allows the serial interface host
/// computer to send data through the ESP32's UART0, which then gets sent out the TX1 serial interface as
/// an RS-422 signal.  This can be used either to have the logger act as a transmitter without having to
/// reflash with the hardware simulator firmware, or to act as its own data source by looping back TX1 A/B
/// to one of the RX inputs.  The special mode ends when the user sends the string "passthrough" exactly
/// to the interface.  It's wise to also send "echo off" before and "echo on" afterwards to avoid all of
/// the data the host's sending coming back up the USB line.
///
/// \param params   Parameters for the command: [on] (no parameter => switch back to standard operation)
/// \param src      Channel on which to report the results of the command.

void SerialCommand::ConfigurePassthrough(String const& params, CommandSource src)
{
    if (params == "on") {
        m_passThrough = true;
    } else {
        m_passThrough = false;
    }
    EmitMessage("INF: passthrough mode set to: " + params + "\n", src);
}

/// Report the current configuration of the logger using JSON formatting.  This can
/// be much more efficient if you want to grab a configuration and transfer to
/// another system.  For output on the serial channel (where there's a human behind
/// the wheel), the JSON if formatted; for output on the WiFi channel (where there's
/// a computer behind the terminal), it's unformatted.
///
/// @param src  Command channel that provided the command (and therefore gets the result)
/// @param secure Flag: true if the channel is trusted, and password information can be given
/// @return N/A

void SerialCommand::ReportConfigurationJSON(CommandSource src, bool secure)
{
    DynamicJsonDocument json(logger::ConfigJSON::ExtractConfig());
    if (src == CommandSource::SerialPort) {
        String s;
        serializeJsonPretty(json, s);
        EmitMessage(s + "\n", src);
    } else {
        if (m_wifi != nullptr)
            m_wifi->SetMessage(json);
    }
}

/// Provide summary report of all of the configuration parameters being managed by the Confgiuration
/// module.  Some of this information can be determined from other locations, but this might be simpler
/// for some purposes (e.g., getting a synoptic list of all of the configuration parameters to set up
/// a GUI for configuration purposes).
///
/// \param src  Channel on which to report the configuration (Serial, WiFi, BLE)

void SerialCommand::ReportConfiguration(CommandSource src)
{
    bool bin_param;
    String string_param;

    EmitMessage("Configuration Parameters:\n", src);
    EmitMessage("  NMEA0183 Logger: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA0183_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);
    EmitMessage("  NMEA2000 Logger: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA2000_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);
    EmitMessage("  IMU Logger: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_MOTION_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);
    EmitMessage("  Power Monitor: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_POWMON_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);
    EmitMessage("  SDIO-MMC Interface: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_SDMMC_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);
    EmitMessage("  Bridge UDP: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_BRIDGE_B, bin_param);
    EmitMessage(bin_param ? "on\n" : "off\n", src);

    EmitMessage("  Webserver: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_WEBSERVER_B, bin_param);
    EmitMessage(bin_param ? "on" : "off", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_DELAY_S, string_param);
    EmitMessage(" " + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_RETRIES_S, string_param);
    EmitMessage(" " + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_TIMEOUT_S, string_param);
    EmitMessage(" " + string_param + "\n", src);

    EmitMessage("  Upload: ", src);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_UPLOAD_B, bin_param);
    EmitMessage(bin_param ? "on" : "off", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_SERVER_S, string_param);
    EmitMessage(" " + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_PORT_S, string_param);
    EmitMessage(":" + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_TIMEOUT_S, string_param);
    EmitMessage(" " + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_INTERVAL_S, string_param);
    EmitMessage(" " + string_param, src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_DURATION_S, string_param);
    EmitMessage(" " + string_param + "\n", src);

    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_MODULEID_S, string_param);
    EmitMessage("  Module ID String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_SHIPNAME_S, string_param);
    EmitMessage("  Shipname String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_SSID_S, string_param);
    EmitMessage("  WiFi AP SSID String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_PASSWD_S, string_param);
    EmitMessage("  WiFi AP Password String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, string_param);
    EmitMessage("  WiFi Client SSID String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_PASSWD_S, string_param);
    EmitMessage("  WiFi Client Password String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WIFIIP_S, string_param);
    EmitMessage("  WiFi IP Address String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WIFIMODE_S, string_param);
    EmitMessage("  WiFi Mode String: " + string_param + "\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_BAUDRATE_1_S, string_param);
    EmitMessage("  Serial Channel 1 Speed: " + string_param + " baud\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_BAUDRATE_2_S, string_param);
    EmitMessage("  Serial Channel 2 Speed: " + string_param + " baud\n", src);
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_BRIDGE_PORT_S, string_param);
    EmitMessage("  Bridge UDP Port: " + string_param + "\n", src);
}

/// This pulls from a JSON-format specification all of the parameters required to
/// configure the logger.  This is generally used to do initial configuration through
/// the web server interface.
///
/// \param spec String containing the JSON-format specification to work from
/// \param src  Command interface that provided the specification
/// \return N/A

void SerialCommand::SetupLogger(String const& spec, CommandSource src)
{
    if (logger::ConfigJSON::SetConfig(spec)) {
        if (src == CommandSource::WirelessPort)
            ReportConfigurationJSON(src);
        else
            EmitMessage("INF: Accepted configuration from JSON input string.\n", src);
    } else {
        EmitMessage("ERR: Error accepting configuration from JSON input string.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr)
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
    }
}

/// Report the current state of heap usage in the system.  This reports the maximmum size of the heap,
/// the current free memory in the heap, the low-water mark (lowest free memory since boot), and the
/// largest available chunk of memory on the heap (allowing for monitoring of fragmentation).
///
/// \param src  Channel on which to report summary (Serial, WiFi, BLE).

void SerialCommand::ReportHeapSize(CommandSource src)
{
    logger::HeapMonitor heap;
    String msg = String("Current Heap: ") + heap.HeapSize() + " B total, free: " + heap.CurrentSize() + " B, low-water: "
                    + heap.LowWater() + " B, biggest chunk: " + heap.LargestBlock() + " B.\n";
    EmitMessage(msg, src);
}

/// Report the algorithms being recommended for use on the data, as stored in the logger.  This is
/// broken out because the system has to be able to report the algorithms either on demand, or as a
/// response to setting a new algorithm (or clearing the list), before finalising the file on the
/// NVM store.  (Otherwise, you get a race condition due to the RAII sematics for the store.)
///
/// @param store    Algorithm store object to report.
/// @param src      Channel on which to report the information (typically the same one that sent the command)
/// @return N/A

void SerialCommand::DisplayAlgorithmStore(logger::AlgoRequestStore& store, CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        String algorithms(store.JSONRepresentation(true));
        EmitMessage(algorithms + '\n', src);
    } else if (src == CommandSource::WirelessPort) {
        DynamicJsonDocument doc(store.GetContents());
        m_wifi->SetMessage(doc);
    } else {
        EmitMessage("ERR: request for unknown CommandSource - who are you?\n", src);
    }
}

/// Report the list of algorithms that the logger would request that the post-processing applies to the data
/// from this system (e.g., de-duplication of depth, reputation computation, etc.).  There is no obligation
/// for the post-processing to do this, but knowing which to do, and in which order, is useful.  The algorithms
/// are specified directly by the user, and the logger does no checking: it just replicates what the user
/// requires.
///
/// \param src  Channel on which to report command results (Serial, WiFi, BLE)

void SerialCommand::ReportAlgRequests(CommandSource src)
{
    logger::AlgoRequestStore algstore;
    DisplayAlgorithmStore(algstore, src);
}

/// Set up the list of requests for algorithms to be run on the data at the post-processing stage.
/// Algorithms are specified by a simple string name, and a string of parameters, which can be in
/// any form that the algorithm can parse.
///
/// \param params   Parameters for the algorithm: <alg-name> <alg-params>
/// \param src      Channel on which to report results of command (Serial, WiFi, BLE)

void SerialCommand::ConfigureAlgRequest(String const& params, CommandSource src)
{
    logger::AlgoRequestStore algstore;

    if (params.startsWith("none")) {
        algstore.ClearAlgorithmList();
    } else {
        int split = params.indexOf(' ');
        String alg_name, alg_params;
        if (split < 0) {
            // No space in the string, so there's no parameters for the algorithm
            alg_name = params;
            alg_params = String("None");
        } else {
            alg_name = params.substring(0, split);
            alg_params = params.substring(split+1);
        }
        algstore.AddAlgorithm(alg_name, alg_params);
    }

    DisplayAlgorithmStore(algstore, src);
}

/// Set the string for additional metadata to be applied to the data when it's converted to GeoJSON
/// in post-processing.  The post-processing code can generate a default "platform" element, but if the user
/// sets up a string here, it can be used to completely replaces this (and provide a lot more information)
/// if required.  The code here does not check that the metadata is valid JSON, and just replicates it into
/// the output data files so that the post-processing code has the option to use it if appropriate.  Note
/// that the JSON should be collapsed into a single line so that there are no \r\n in the data (otherwise
/// it'll get split into multiple WIBL commands, and will not be recognised).
///
/// \param params   Parameters for the command: <arbitrary-text>
/// \param src      Channel on which to report results of the command (Serial, WiFi, BLE)

void SerialCommand::StoreMetadataElement(String const& params, CommandSource src)
{
    logger::MetadataStore metastore;
    metastore.SetMetadata(params);
    if (src == CommandSource::SerialPort) {
        EmitMessage("INF: added metadata element to local configuration.\n", src);
    } else {
        EmitJSON(params, src);
    } 
}

/// Report the user-specified string for auxiliary metadata generation, if set.  This metadata
/// element is optional, but if available, is reported verbatuim, without interpretation.
///
/// \param src  Channel on which to report command results (Serial, WiFi, BLE)

void SerialCommand::ReportMetadataElement(CommandSource src)
{
    logger::MetadataStore metastore;
    String metadata = metastore.JSONRepresentation();
    if (src == CommandSource::SerialPort) {
        EmitMessage("Metadata element: |" + metadata + "|\n", src);
    } else {
        if (metadata.length() == 0) {
            EmitMessage("No metadata element stored in logger.", src);
        } else {
            EmitJSON(metadata, src);
        }
    }
}

void SerialCommand::DisplayNMEAFilter(logger::N0183IDStore& filter, CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        EmitMessage("NMEA0183 message IDs accepted for logging:\n", src);
        String filter_ids(filter.JSONRepresentation(true));
        EmitMessage(filter_ids + '\n', src);
    } else if (src == CommandSource::WirelessPort) {
        DynamicJsonDocument doc(filter.GetContents());
        m_wifi->SetMessage(doc);
    } else {
         EmitMessage("ERR: request for unknown CommandSource - who are you?\n", src);
    }
}

/// Report the currently configured set of NMEA0183 message IDs that are acceptable for logging.
/// All sentences with a message ID in the list will be written to the log; all others are rejected
/// after reception.
///
/// \param src  Channel on which to report the IDs configured for logging (Serial, WiFi, BLE)

void SerialCommand::ReportNMEAFilter(CommandSource src)
{
    logger::N0183IDStore filter;
    DisplayNMEAFilter(filter, src);
}

/// Add to the list of NMEA0183 sentence message IDs that are allowed to be logged to SD card on
/// reception.  Any sentence with a message ID on the list will be logged; all others will be
/// rejected.  Note that the code does not check the syntax of the message IDs, or that they are
/// exactly three characters, etc. --- that's up to the user.  The string is therefore case
/// sensitive.  The special ID "any" will reset the filter back to the default state where
/// everything is logged.  Note that the code does not consider the talker ID, so INGGA and
/// GPGGA will both be logged if GGA is on the list.
///
/// \param params   Parameters for the command: all | <arbitrary-text>
/// \param src      Channel on which to report the results of the command (Serial, WiFi, BLE)

void SerialCommand::AddNMEAFilter(String const& params, CommandSource src)
{
    logger::N0183IDStore filter;
    if (params == "all") {
        filter.ClearIDList();
    } else {
        filter.AddIDs(params);
    }
    DisplayNMEAFilter(filter, src);
}

/// Report the set of scales set for any on-board sensors that record binary data that needs to be
/// scaled to useful units and/or into a float in the first place.  This reports the sensor elements
/// specified in the store as JSON fragments, which should be convertable as usual in any language
/// supporting JSON objects.
///
/// \param src      Channel on which to report the results of the command (Serial, WiFi, BLE)

void SerialCommand::ReportScalesElement(CommandSource src)
{
    logger::ScalesStore scales;
    switch(src) {
        case CommandSource::SerialPort:
            EmitMessage("Sensor scales for on-board sensors:\n", src);
            EmitMessage(scales.JSONRepresentation(true) + '\n', src);
            break;
        case CommandSource::WirelessPort:
            EmitJSON(scales.JSONRepresentation(), src);
            break;
        default:
            EmitMessage("ERR: request for unknown CommandSource - who are you?\n", src);
            if (src == CommandSource::WirelessPort && m_wifi != nullptr)
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            break;
    }
}

/// Report the number of files that are available on the SD card for transfer.
///
/// \param src      Channel on which to report the results of the command (Serial, WiFi, BLE)

void SerialCommand::ReportFileCount(CommandSource src)
{
    uint32_t file_count = m_logManager->CountLogFiles();
    EmitMessage(String(file_count) + "\n", src);
}

void SerialCommand::ReportWebserverConfig(CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        bool enable;
        String station_delay, station_retries, station_timeout;
        logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_WEBSERVER_B, enable);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_DELAY_S, station_delay);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_RETRIES_S, station_retries);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_TIMEOUT_S, station_timeout);
        EmitMessage(String("Webserver is ") + (enable ? "on" : "off") +
            " with connection delay " + station_delay +
            ", connection timeout " + station_timeout +
            ", and " + station_retries + " retries.\n", src);
    } else if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    } else {
        EmitMessage("ERR: request for unknown CommandSource - who are you?\n", src);
    }
}

/// Set up the configuration for the webserver started by the logger, including timeouts
/// for station bring-up and retries for joining an existing network before reverting to
/// "safe" mode, bringing up a soft access point.
///
/// \param params String containing the delay between join tries (seconds) and retries (int)
/// \return N/A

void SerialCommand::ConfigureWebserver(String const& params, CommandSource src)
{
    bool state;

    if (params.startsWith("on")) {
        state = true;
    } else if (params.startsWith("off")) {
        state = false;
    } else {
        EmitMessage("ERR: webserver can be configured 'on' or 'off' on boot only.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    int delay_position = params.indexOf(' ') + 1;
    int retries_position = params.indexOf(' ', delay_position) + 1;
    int timeout_position = params.indexOf(' ', retries_position) + 1;
    String station_delay = params.substring(delay_position, retries_position-1);
    String station_retries = params.substring(retries_position, timeout_position-1);
    String station_timeout = params.substring(timeout_position);
    // TODO: Do some range checking on these parameters before accepting them.
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_DELAY_S, station_delay);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_RETRIES_S, station_retries);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_TIMEOUT_S, station_timeout);
    logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_WEBSERVER_B, state);
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    }
}

/// Report on the current status of the logger, including the WiFi status, the number of files available,
/// and their sizes.  Reporting is done in JSON format, pretty-printed if on the serial stream, as compact
/// as possible if on the WiFi.
///
/// \param src  CommandSource for the stream that generated the request
/// \return N/A

void SerialCommand::ReportCurrentStatus(CommandSource src)
{
    DynamicJsonDocument status(logger::status::CurrentStatus(m_logManager));

    if (src == CommandSource::SerialPort) {
        String json;
        serializeJsonPretty(status, json);
        EmitMessage(json+"\n", src);
    } else {
        if (m_wifi != nullptr) {
            m_wifi->SetMessage(status);
        }
    }
}

/// Report the current set of "lab default" configuration parameters set on the logger.  These
/// are the backup parameters that you can reset with the "lab reset" command to give you some
/// sane set of configurations when it all goes wrong.
///
/// \param src  Channel on which this command was received
/// \return N/A

void SerialCommand::ReportLabDefaults(CommandSource src)
{
    String spec;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DEFAULTS_S, spec);
    EmitJSON(spec, src);
    if (spec.length() == 0 && src == CommandSource::WirelessPort && m_wifi != nullptr) {
        m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::UNAVAILABLE);
    }
}

/// Set the JSON-formatted configuration set to use when the user wants to attempt to reset
/// the configuration of the logger to a "known good" state.  Note that the logger does not
/// attempt to validate the JSON data at this stage, so it's entirely possible for the user
/// to mess up the configuration and then have a problem when trying to reset ...
///
/// \param spec JSON-formatted serialised \a String with default configuration
/// \param src  Channel on which this command was received
/// \return N/A

void SerialCommand::SetLabDefaults(String const& spec, CommandSource src)
{
    logger::LoggerConfig.SetConfigString(logger::Config::CONFIG_DEFAULTS_S, spec);
    if (src == CommandSource::SerialPort) {
        EmitMessage("INF: set lab defaults.\n", src);
    } else if (m_wifi != nullptr) {
        if (!EmitJSON(spec, src)) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            m_wifi->AddMessage("Invalid input JSON string");
        }
    }
}

/// Reset the configuration of the logger to the previous-stored default configuration.  Note
/// that the configuration may be bad (the code here doesn't attempt to validate it when stored),
/// and therefore this configuration may not take.  It's also possible that some of the configurations
/// (such as which loggers are logging) may not take effect until the system is rebooted.
///
/// \param src  Channel on which this command was received
/// \return N/A

void SerialCommand::ResetLabDefaults(CommandSource src)
{
    String spec;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DEFAULTS_S, spec);
    if (spec.length() > 0) {
        logger::ConfigJSON::SetConfig(spec);
        if (src == CommandSource::SerialPort) {
            EmitMessage("INF: lab default configuration reset; you may need to reboot for some changes to take effect.\n", src);
        } else if (m_wifi != nullptr) {
            if (!EmitJSON(spec, src)) {
                EmitMessage("Invalid lab defaults JSON", src);
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            } else {
                EmitMessage("Defaults reset; reboot may be required for some changes to take effect.", src);
            }
        }
    } else {
        if (src == CommandSource::SerialPort) {
            EmitMessage("ERR: no lab default configuration set!\n", src);
        } else if (m_wifi != nullptr) {
            m_wifi->AddMessage("No lab defaults stored on logger to reset to.");
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::UNAVAILABLE); // "Service Unavailable"
        }
    }
}

/// Get and report the upload authorisation stored in the logger (if it exists).  This is used to handshake
/// with the upload server if the logger is sending data directly over WiFi to the outside world.
///
/// @param src  CommandSource channel on which the command was received
/// @return N/A

void SerialCommand::GetAuthorisation(CommandSource src)
{
    if (src != CommandSource::SerialPort && src != CommandSource::WirelessPort) {
        EmitMessage("ERR: Request for upload token from unrecognised CommandSource - who are you?\n", src);
        return;
    }
    String token, cert;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_TOKEN_S, token);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_CERT_S, cert);
    if (token.length() == 0 && cert.length() == 0) {
        if (src == CommandSource::SerialPort) {
            EmitMessage("ERR: no upload authorisation stored on logger to report.\n", src);
        } else {
            m_wifi->AddMessage("No upload authorisation stored on logger to report.");
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::UNAVAILABLE);
        }
        return;
    }
    if (src == CommandSource::SerialPort) {
        EmitMessage("Upload token: |" + token + "|\n", src);
        EmitMessage("Upload cert: |" + cert + "|\n", src);
    } else {
        m_wifi->AddMessage(token);
        m_wifi->AddMessage(cert);
    }
}

/// Set the upload authorisation info (used for handshakes with the upload server if the logger is sending
/// data directly to the outside world).  The firmware does no validation on the info, except in that
/// it has to be ASCII-encoded, and just stores what's provided.  On success, the code issues a
/// GetAuthorisation() so that the user has positive confirmation that the update was done.
///
/// @param data    String to store in the NVM for uploads
/// @param src      CommandSource channel on which the command was received.
/// @return N/A

void SerialCommand::SetAuthorisation(String const& data, CommandSource src)
{
    if (src != CommandSource::SerialPort && src != CommandSource::WirelessPort) {
        EmitMessage("ERR: Request to set upload token from unrecognised CommandSource - who are you?\n", src);
        return;
    }

    if (data.startsWith("token")) {
        if (!logger::LoggerConfig.SetConfigString(logger::Config::CONFIG_UPLOAD_TOKEN_S, data.substring(6))) {
            if (src == CommandSource::SerialPort) {
                EmitMessage("ERR: Failed to set upload token.  Probably an internal error.\n", src);
            } else {
                EmitMessage("Failed to set upload token.  Probably an internal error.", src);
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            }
            return;
        }
    } else if (data.startsWith("cert")) {
         if (!logger::LoggerConfig.SetConfigString(logger::Config::CONFIG_UPLOAD_CERT_S, data.substring(5))) {
            if (src == CommandSource::SerialPort) {
                EmitMessage("ERR: Failed to set upload certificate.  Probably an internal error.\n", src);
            } else {
                EmitMessage("Failed to set upload certificate.  Probably an internal error.", src);
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            }
            return;
        }
    } else {
        if (src == CommandSource::SerialPort) {
            EmitMessage("ERR: auth command must contain 'token' or 'cert' as first element.\n", src);
        } else {
            EmitMessage("auth command must contain 'token' or 'cert' as first element.", src);
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
    }
    GetAuthorisation(src);
}

/// Generate a downloadable snapshot of the given resource in the log space (i.e., on the SD card) so that
/// it's exposed in the webserver and therefore capable of being downloaded by the browser directly (and
/// therefore automatically downloads to local storage).  The command responds with a JSON description of
/// the URL at which to find the resource that's converted, or empty URL if the conversion was not completed.
///     The known resources might vary by variant of the firmware, but include at least:
///         'catalog'   The list of all known files on the logger, their MD5 hash, size, and names
///         'config'    The current running configuration of the logger
///         'default'   The "lab default" configuration of the logger
///
/// @param resource Target resource from the known list
/// @param src      CommandSource channel on which the command was received
/// @return N/A

void SerialCommand::SnapshotResource(String const& resource, CommandSource src)
{
    String url;
    bool rc;

    if (resource == "config") {
        DynamicJsonDocument json(logger::ConfigJSON::ExtractConfig());
        String contents;
        serializeJson(json, contents);
        rc = m_logManager->WriteSnapshot("config.jsn", contents, url);
    } else if (resource == "defaults") {
        String defaults;
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DEFAULTS_S, defaults);
        if (defaults.isEmpty())
            defaults = String("{}");
        rc = m_logManager->WriteSnapshot("defaults.jsn", defaults, url);
    } else if (resource == "catalog") {
        DynamicJsonDocument files(logger::status::GenerateFilelist(m_logManager));
        String contents;
        serializeJson(files, contents);
        rc = m_logManager->WriteSnapshot("catalog.jsn", contents, url);
    } else if (resource == "archive") {
        String contents;
        DynamicJsonDocument json(logger::ConfigJSON::ExtractConfig());
        serializeJson(json, contents);
        m_logManager->WriteSnapshot("config.jsn", contents, url);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DEFAULTS_S, contents);
        if (contents.isEmpty())
            contents = String("{}");
        m_logManager->WriteSnapshot("defaults.jsn", contents, url);
        json = DynamicJsonDocument(logger::status::GenerateFilelist(m_logManager));
        serializeJson(json, contents);
        m_logManager->WriteSnapshot("catalog.jsn", contents, url);
        url = "/archive";
        rc = true;
    } else {
        EmitMessage("ERR: unknown snapshot resource requested.\n", src);
    }

    StaticJsonDocument<256> responseJson;
    if (rc)
        responseJson["url"] = url;
    else
        responseJson["url"] = "";
    String response;
    serializeJson(responseJson, response);
    EmitJSON(response, src);
}

void SerialCommand::ReportUploadConfig(CommandSource src)
{
    if (src == CommandSource::SerialPort) {
        bool enable;
        String upload_address, upload_port, upload_timeout, upload_interval, upload_duration;
        logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_UPLOAD_B, enable);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_SERVER_S, upload_address);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_PORT_S, upload_port);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_TIMEOUT_S, upload_timeout);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_INTERVAL_S, upload_interval);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_DURATION_S, upload_duration);
        EmitMessage(String("Upload is ") + (enable ? "on" : "off") +
            " with URL http://" + upload_address + ":" + upload_port +
            ", connection timeout " + upload_timeout + "s" +
            ", upload interval " + upload_interval + "s" +
            ", and upload duration " + upload_duration + "s\n", src);
    } else if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    } else {
        EmitMessage("ERR: request from unknown CommandSource - who are you?\n", src);
    }
}

void SerialCommand::ConfigureUpload(String const& command, CommandSource src)
{
    if (command == "on" || command == "off") {
        // Change of upload enable state only
        bool state;
        if (command == "on") {
            state = true;
        } else if (command == "off") {
            state = false;
        } else {
            EmitMessage("ERR: unrecognised 'upload' enable state (only 'on' and 'off' are allowed).\n", src);
            if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
                m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
            }
            return;
        }
        logger::LoggerConfig.SetConfigBinary(logger::Config::ConfigParam::CONFIG_UPLOAD_B, state);
        return;
    }

    // Note that anything like "upload on x y" will drop through since the test is for equivalence above.

    int addr_position = 0; // Address should be first in the command, but this helps clarity below.
    int port_position = command.indexOf(' ', addr_position) + 1;
    int timeout_position = command.indexOf(' ', port_position) + 1;
    int interval_position = command.indexOf(' ', timeout_position) + 1;
    int duration_position = command.indexOf(' ', interval_position) + 1;

    if (port_position == 0 || timeout_position == 0 || interval_position == 0 || duration_position == 0) {
        EmitMessage("ERR: malformed upload specification; see syntax for details.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }
    String addr(command.substring(addr_position, port_position-1));
    String port(command.substring(port_position, timeout_position-1));
    String timeout(command.substring(timeout_position, interval_position-1));
    String interval(command.substring(interval_position, duration_position-1));
    String duration(command.substring(duration_position));

    // We need to check that the components of the specification are valid, although we can't do much
    // about the address.
    long port_value = port.toInt(),
         timeout_value = timeout.toInt(), interval_value = interval.toInt(), duration_value = duration.toInt();
    
    if (port_value <= 0 || port_value > 65535 || timeout_value <= 0 || interval_value <= 0 || duration_value <= 0) {
        EmitMessage("ERR: malformed upload specification; see syntax for details.\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::BADREQUEST);
        }
        return;
    }

    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_SERVER_S, addr);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_PORT_S, port);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_TIMEOUT_S, timeout);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_INTERVAL_S, interval);
    logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_DURATION_S, duration);
    
    if (src == CommandSource::WirelessPort) {
        ReportConfigurationJSON(src);
    }
}

/// Output a list of known commands, since there are now enough of them to make remembering them
/// all a little difficult.

void SerialCommand::Syntax(CommandSource src)
{
    EmitMessage(String("Command Syntax (V") + SoftwareVersion() + "):\n", src);
    EmitMessage("  accept [NMEA0183-ID | all]          Configure which NMEA0183 messages to accept.\n", src);
    EmitMessage("  algorithm [name params | none]      Add (or report) an algorithm request to the cloud processing.\n", src);
    EmitMessage("  auth [cert|token data]              Set or report the upload authentication information.\n", src);
    EmitMessage("  configure [on|off logger-name]      Configure individual loggers on/off (or report config).\n", src);
    EmitMessage("  echo on|off                         Control character echo on serial line.\n", src);
    EmitMessage("  erase file-number|all               Remove a specific [file-number] or all log files.\n", src);
    EmitMessage("  filecount                           Report the number of log files currently available for transfer.\n", src);
    EmitMessage("  heap                                Report current free heap size.\n", src);
    EmitMessage("  help|syntax                         Generate this list.\n", src);
    EmitMessage("  invert 1|2                          Invert polarity of RS-422 input on port 1|2.\n", src);
    EmitMessage("  lab defaults [specification]        Report, or set, lab default configuration in JSON format.\n", src);
    EmitMessage("  lab reset                           Reset configuration to the stored lab defaults, if any.\n", src);
    EmitMessage("  led normal|error|initialising|full|data|stopped\n", src);
    EmitMessage("                                      [Debug] Set the indicator LED status.\n", src);
    EmitMessage("  log                                 Output the contents of the console log.\n", src);
    EmitMessage("  mdns [name]                         Report or set the mDNS responder name for the logger.\n", src);
    EmitMessage("  metadata [platform-specific]        Store or report a platform-specific metadata JSON element.\n", src);
    EmitMessage("  ota                                 Start Over-the-Air update sequence for the logger.\n", src);
    EmitMessage("  password ap|station [wifi-password] Set the WiFi password.\n", src);
    EmitMessage("  restart                             Restart the logger module hardware.\n", src);
    EmitMessage("  scales                              Report any registered sensor-specific scale factors.\n", src);
    EmitMessage("  setup [json-specification]          Report the configuration of the logger, or set it, using JSON specifications.\n", src);
    EmitMessage("  shipname name                       Set the name of the host ship carrying the logger.\n", src);
    EmitMessage("  sizes                               Output list of the extant log files, and their sizes in bytes.\n", src);
    EmitMessage("  snapshot catalog|config|defaults|archive\n", src);
    EmitMessage("                                      Prepare a downloadable version of the specified resource in /logs\n", src);
    EmitMessage("  speed 1|2 baud-rate                 Set the baud rate for the RS-422 input channels.\n", src);
    EmitMessage("  ssid ap|station [wifi-ssid]         Set the WiFi SSID.\n", src);
    EmitMessage("  status                              Generate JSON-format status message for current dynamic configuration\n", src);
    EmitMessage("  steplog                             Close current log file, and move to the next in sequence.\n", src);
    EmitMessage("  stop                                Close files and go into self-loop for power-down.\n", src);
    EmitMessage("  transfer file-number                Transfer log file [file-number] (WiFi and serial only).\n", src);
    EmitMessage("  uniqueid [logger-name]              Set or report the logger's unique identification string.\n", src);
    EmitMessage("  upload [on|off]|[srvaddr srvport timeout interval duration]\n", src);
    EmitMessage("                                      Control whether files are auto-updated when connected\n", src);
    EmitMessage("  verbose on|off                      Control verbosity of reporting for serial input strings.\n", src);
    EmitMessage("  version                             Report NMEA0183 and NMEA2000 logger version numbers.\n", src);
    EmitMessage("  webserver on|off delay reties timeout\n", src);
    EmitMessage("                                      Configure web-server interface with given retry delay (seconds), retries (int), and connection timeout (seconds).\n", src);
    EmitMessage("  wireless on|off|accesspoint|station Control WiFi activity [on|off] and mode [accesspoint|station].\n", src);
}

/// Execute the command strings received from the serial interface(s).  This tests the
/// string for known commands, and passes on the options from the string (if any) to
/// the particular methods used for command implementation.  Note that this interface
/// is pretty fragile, since it doesn't check for partial commands, or differences in case,
/// etc.  The expectation is that commands either come from developers, or through an
/// app, and therefore it shouldn't need to be particularly strong.
///
/// \param cmd  String with the user command to execute.
/// \param src      Stream by which the command arrived

void SerialCommand::Execute(String const& cmd, CommandSource src)
{
    if (cmd.startsWith("accept")) {
        if (cmd.length() == 6) {
            ReportNMEAFilter(src);
        } else {
            AddNMEAFilter(cmd.substring(7), src);
        }
    } else if (cmd.startsWith("algorithm")) {
        if (cmd.length() == 9) {
            ReportAlgRequests(src);
        } else {
            ConfigureAlgRequest(cmd.substring(10), src);
        }
    } else if (cmd.startsWith("auth")) {
        if (cmd.length() == 4) {
            GetAuthorisation(src);
        } else {
            SetAuthorisation(cmd.substring(5), src);
        }
    } else if (cmd.startsWith("configure")) {
        if (cmd.length() == 9) {
            ReportConfiguration(src);
        } else {
            ConfigureLoggers(cmd.substring(10), src);
        }
    } else if (cmd.startsWith("echo")) {
        ConfigureEcho(cmd.substring(5), src);
    } else if (cmd.startsWith("erase")) {
        EraseLogfile(cmd.substring(6), src);
    } else if (cmd == "filecount") {
        ReportFileCount(src);
    } else if (cmd == "heap") {
        ReportHeapSize(src);
    } else if (cmd == "help" || cmd == "syntax") {
        Syntax(src);
    } else if (cmd.startsWith("invert")) {
        ConfigureSerialPortInvert(cmd.substring(7), src);
    } else if (cmd.startsWith("lab defaults")) {
        if (cmd.length() == 12) {
            ReportLabDefaults(src);
        } else {
            SetLabDefaults(cmd.substring(13), src);
        }
    } else if (cmd.startsWith("lab reset")) {
        ResetLabDefaults(src);
    } else if (cmd.startsWith("led")) {
        ModifyLEDState(cmd.substring(4));
    } else if (cmd == "log") {
        ReportConsoleLog(src);
    } else if (cmd.startsWith("mdns")) {
        if (cmd.length() == 4) {
            GetMDNSName(src);
        } else {
            SetMDNSName(cmd.substring(5), src);
        }
    } else if (cmd.startsWith("metadata")) {
        if (cmd.length() == 8) {
            ReportMetadataElement(src);
        } else {
            StoreMetadataElement(cmd.substring(9), src);
        }
    } else if (cmd.startsWith("ota")) {
        EmitMessage("Starting OTA update sequence ...\n", src);
        OTAUpdater updater; // This puts the logger into a loop which ends with a full reset
    } else if (cmd == "passthrough") {
        // Note that this is intentionally not defined in the syntax list, or elsewhere: it
        // really is just for debugging.
        ConfigurePassthrough("on", src);
    } else if (cmd.startsWith("password")) {
        if (cmd.length() == 8)
            GetWiFiPassword(src);
        else
            SetWiFiPassword(cmd.substring(9), src);
    } else if (cmd == "restart") {
        ESP.restart();
    } else if (cmd == "scales") {
        ReportScalesElement(src);
    } else if (cmd.startsWith("setup")) {
        if (cmd.length() == 5) {
            ReportConfigurationJSON(src);
        } else {
            SetupLogger(cmd.substring(6), src);
        }
    } else if (cmd.startsWith("shipname")) {
        if (cmd.length() == 8) {
            ReportShipname(src);
        } else {
            SetShipname(cmd.substring(9), src);
        }
    } else if (cmd == "sizes") {
        ReportCurrentStatus(src);
    } else if (cmd.startsWith("snapshot")) {
        SnapshotResource(cmd.substring(9), src);
    } else if (cmd.startsWith("speed")) {
        ConfigureSerialPortSpeed(cmd.substring(6), src);
    } else if (cmd.startsWith("ssid")) {
        if (cmd.length() == 4)
            GetWiFiSSID(src);
        else
            SetWiFiSSID(cmd.substring(5), src);
    } else if (cmd == "status") {
        ReportCurrentStatus(src);
    } else if (cmd == "steplog") {
        m_logManager->CloseLogfile();
        m_logManager->StartNewLog();
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            ReportCurrentStatus(src);
        }
    } else if (cmd == "stop") {
        Shutdown();
    } else if (cmd.startsWith("transfer")) {
        TransferLogFile(cmd.substring(9), src);
    } else if (cmd.startsWith("uniqueid")) {
        if (cmd.length() == 8) {
            ReportIdentificationString(src);
        } else {
            SetIdentificationString(cmd.substring(9), src);
        }
    } else if (cmd.startsWith("upload")) {
        if (cmd.length() == 6) {
            ReportUploadConfig(src);
        } else {
            ConfigureUpload(cmd.substring(7), src);
        }
    } else if (cmd.startsWith("verbose")) {
        SetVerboseMode(cmd.substring(8));
    } else if (cmd == "version") {
        ReportSoftwareVersion(src);
    } else if (cmd.startsWith("webserver")) {
        if (cmd.length() == 9) {
            ReportWebserverConfig(src);
        } else {
            ConfigureWebserver(cmd.substring(10), src);
        }
    } else if (cmd.startsWith("wireless")) {
        ManageWireless(cmd.substring(9), src);
    } else {
        EmitMessage("ERR: command not recognised: \"" + cmd + "\".\n", src);
        if (src == CommandSource::WirelessPort && m_wifi != nullptr) {
            m_wifi->SetStatusCode(WiFiAdapter::HTTPReturnCodes::NOTFOUND);
        }
    }
}

/// User-level routine to get commands from any number of sources, and attempt to execute
/// them.  The system uses the Serial input by defult, but will also check for commands from the
/// Bluetooth LE UART service if there is a client connected.
///
/// This routine has to be executed regularly to keep the processing rate going, since commands
/// will be ignored if this code does not run.  Running this periodically in the loop() is appropriate.

void SerialCommand::ProcessCommand(void)
{
    if (Serial.available() > 0) {
        int c = Serial.read();
        if (m_echoOn) Serial.printf("%c", c);
        if (c == '\b') {
            // Delete (or at least backspace) character
            m_serialBuffer.RemoveLastCharacter();
        } else {
            m_serialBuffer.AddCharacter(c);
        }
        if (c == '\n') {
            String cmd(m_serialBuffer.Contents());
            m_serialBuffer.Reset();
            if (m_passThrough) {
                if (cmd.startsWith("passthrough")) {
                    ConfigurePassthrough("off", CommandSource::SerialPort);
                } else {
                    Serial1.print(cmd);
                }
            } else {
                cmd.trim();
                
                Serial.printf("Found console command: \"%s\"\n", cmd.c_str());

                Execute(cmd, CommandSource::SerialPort);
            }
        }
    }
    if (m_wifi != nullptr) {
        m_wifi->RunLoop();
        String cmd = m_wifi->ReceivedString();
        if (cmd.length() != 0) {
            cmd.trim();
            Serial.printf("Found WiFi command: \"%s\"\n", cmd.c_str());
            Execute(cmd, CommandSource::WirelessPort);
            m_wifi->TransmitMessages();
        }
        if (m_uploadManager != nullptr) {
            m_uploadManager->UploadCycle();
        }
    }
}

/// Provide an external interface to the shutdown HCF so that we log the fact that the emergency
/// power has been activated, and therefore the system is going down.

void SerialCommand::EmergencyStop(void)
{
    Serial.println("WARN: Emergency power activated, shutting down.");
    m_logManager->Syslog("warning: emergency power activated, shutting down.");
    Shutdown();
}

/// Generate a message on the output stream associated with the source given.
///
/// \param  msg     Message to output
/// \param  src     Source of the input command that generated this message

void SerialCommand::EmitMessage(String const& msg, CommandSource src)
{
    switch (src) {
        case CommandSource::SerialPort:
            Serial.print(msg);
            break;
        case CommandSource::WirelessPort:
            m_wifi->AddMessage(msg);
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}

/// Generate a message on the output stream associated with the given source, with
/// the message in JSON format.  This often happens with metadata, configuration,
/// and status information.  The code decodes the JSON, which de facto validates
/// the JSON string.  Deserialisation errors are reported with a single message on
/// the appropriate output stream (on WiFi, this is JSON with a "messages" tag).
///
/// @param source   JSON document, stringified.
/// @param chan     Input channel on which the command arrived
/// @return True if the deserialisation worked; false on error

bool SerialCommand::EmitJSON(String const& source, CommandSource chan)
{
    if (source.length() == 0) {
        EmitMessage("No data in JSON.\n", chan);
        return false;
    }
    DynamicJsonDocument json(logger::status::GenerateJSON(source));
    switch (chan) {
        case CommandSource::SerialPort:
            serializeJsonPretty(json, Serial);
            break;
        case CommandSource::WirelessPort:
            if (m_wifi != nullptr) {
                m_wifi->SetMessage(json);
            }
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
    return true;
}
