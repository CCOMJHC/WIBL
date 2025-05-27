/*! \file SerialCommand.h
 *  \brief Interface for command line processing for the application
 *
 *  The logger takes commands on the serial input line from the user application (or
 *  the user if it's connected to a terminal).  This code generates the interface for
 *  executing those commands.
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

#ifndef __SERIAL_COMMAND_H__
#define __SERIAL_COMMAND_H__

#include <Arduino.h>
#include "N2kLogger.h"
#include "N0183Logger.h"
#include "PointBridge.h"
#include "LogManager.h"
#include "StatusLED.h"
#include "WiFiAdapter.h"
#include "IncrementalBuffer.h"
#include "NVMFile.h"
#include "AutoUpload.h"

/// \class SerialCommand
/// \brief Implement a simple ASCII command language for the logger
///
/// The \a SerialCommand object encapsulates a simple command language for the logger,
/// which relies on ASCII commands provided over the Arduino "Serial" object, or (if connected
/// to a client) the Bluetooth LE UART service.  Output from the commands is routed to the
/// Arduino "Serial" UART, and possibly the BLE UART if connected and appropriate.
///
/// The code stores copies of the pointers for the logger and status LED controllers, but does
/// not manage them.  The pointer for the BLE object is managed locally.
///
/// Like most Arduino code, the \a ProcessCommand method needs to be called regularly to
/// check for commands, and execute them.

class SerialCommand {
public:
    /// \brief Default constructor for the command processor
    SerialCommand(nmea::N2000::Logger *canLogger, nmea::N0183::Logger *serialLogger,
                  logger::Manager *logManager, StatusLED *led);
    /// \brief Default destructor
    ~SerialCommand();
    
    /// \brief Poll for commands, and execute if they've been received.
    void ProcessCommand(void);

    /// \brief Stop logging immediately for emergency power-down
    void EmergencyStop(void);
    
    /// \enum CommandSource
    /// \brief Identify the source of the command being processed
    
    enum CommandSource {
        SerialPort,     ///< The USB serial connection to a monitoring computer
        WirelessPort    ///< WiFi socket from a client
    };

    /// \brief Turn on character echo on the Serial interface so that the user can see what's being typed
    void EchoOn(void) { m_echoOn = true; }
    /// \brief Turn off character echo on the Serial interface
    void EchoOff(void) { m_echoOn = false; }
    
    /// \brief Provide a string representation of the command processor version
    static String SoftwareVersion(void);

private:
    nmea::N2000::Logger *m_CANLogger;   ///< Pointer for the logger object to use
    nmea::N0183::Logger *m_serialLogger;///< Pointer for the NMEA0183 message handler
    nmea::N0183::PointBridge *m_bridge; ///< Pointer for the WiFi/UDP -> NEMA0183 bridge
    net::UploadManager  *m_uploadManager; ///< Pointer to the auto-upload manager
    logger::Manager     *m_logManager;  ///< Object to write to SD files and console log
    StatusLED           *m_led;         ///< Pointer for the status LED controller
    WiFiAdapter         *m_wifi;        ///< Pointer for the WiFi interface, once it comes up
    logger::IncBuffer   m_serialBuffer; ///< Space to assemble serial commands that doesn't block runtime
    bool                m_echoOn;       ///< Flag: indicate that characters from serial should be echoed back
    bool                m_passThrough;  ///< Flag: indicate that strings should be passed through to NMEA0183 transmit

    /// \brief Print the console log on the output stream(s)
    void ReportConsoleLog(CommandSource src);
    /// \brief Report the logger software version string
    void ReportSoftwareVersion(CommandSource src);
    /// \brief Erase one or all of the data log files
    void EraseLogfile(String const& filenum, CommandSource src);
    /// \brief Set the state of the LEDs (primarily for testing)
    void ModifyLEDState(String const& command);
    /// \brief Report the logger's user-specified identification string
    void ReportIdentificationString(CommandSource src);
    /// \brief Set the logger's user-specified identification string
    void SetIdentificationString(String const& identifier, CommandSource src);
    /// \brief Report the host ship's name
    void ReportShipname(CommandSource src);
    /// \brief Set the host ship's name
    void SetShipname(String const& name, CommandSource src);
    /// \brief Turn on/off verbose information on messages received
    void SetVerboseMode(String const& mode);
    /// \brief Shut down logging for safe power removal
    void Shutdown(void);
    /// \brief Set the WiFi SSID string
    void SetWiFiSSID(String const& params, CommandSource src);
    /// \brief Get the WiFi SSID string
    void GetWiFiSSID(CommandSource src);
    /// \brief Set the WiFi password string
    void SetWiFiPassword(String const& params, CommandSource src);
    /// \brief Get the WiFi password string
    void GetWiFiPassword(CommandSource src);
    /// \brief Set the mDNS responder name for the WiFi system
    void SetMDNSName(String const& params, CommandSource src);
    /// \brief Get the mDNS responder name for the WiFi system
    void GetMDNSName(CommandSource src);
    /// \brief Turn the WiFi interface either on or off
    void ManageWireless(String const& command, CommandSource src);
    /// \brief Send a log file to the client
    void TransferLogFile(String const& command, CommandSource src);
    /// \brief Set up receiver on UARTs for inverting input (to deal with polarity problems)
    void ConfigureSerialPortInvert(String const& command, CommandSource src);
    /// \brief Set up baud rate for the UARTs
    void ConfigureSerialPortSpeed(String const& command, CommandSource src);
    /// \brief Configure whether to bring on individual loggers
    void ConfigureLoggers(String const& command, CommandSource src);
    /// \brief Configure whether to echo characters on Serial back to the host
    void ConfigureEcho(String const& command, CommandSource src);
    /// \brief Configure whether to pass through characters on Serial to NMEA0183
    void ConfigurePassthrough(String const& command, CommandSource src);
    /// \brief Set up algorithm requests for later post-processing
    void ConfigureAlgRequest(String const& command, CommandSource src);
    /// \brief Report configuration parameters as a JSON structure
    void ReportConfigurationJSON(CommandSource src, bool secure = false);
    /// \brief Report configuration parameters for the logger
    void ReportConfiguration(CommandSource src);
    /// \brief Set up all configuration parameters from a JSON string
    void SetupLogger(String const& spec, CommandSource src);
    /// \brief Report algorithms that the logger requests be run on the data
    void ReportAlgRequests(CommandSource src);
    /// \brief Report heap size during run-time
    void ReportHeapSize(CommandSource src);
    /// \brief Show a list of known commands
    void Syntax(CommandSource src);
    /// \brief Store a metdata element to be added to each data file
    void StoreMetadataElement(String const& command, CommandSource src);
    /// \brief Dump out the metadata element stored in the flash memory
    void ReportMetadataElement(CommandSource src);
    /// \brief Dump out the list of NMEA0183 messages that are accepted
    void ReportNMEAFilter(CommandSource src);
    /// \brief Add/reset the NMEA0183 messages accepted for logging
    void AddNMEAFilter(String const& command, CommandSource src);
    /// \brief Dump out the scales element stored in the flash memory
    void ReportScalesElement(CommandSource src);
    /// \brief Report the number of log files available on the SD card
    void ReportFileCount(CommandSource src);
    /// \brief Report the configuration of the web-server
    void ReportWebserverConfig(CommandSource src);
    /// \brief Configure the web-server for system config/management
    void ConfigureWebserver(String const& command, CommandSource src);
    /// \brief Report on the current status of the logger
    void ReportCurrentStatus(CommandSource src);
    /// \brief Report the lab-default configuration JSON string
    void ReportLabDefaults(CommandSource src);
    /// \brief Set the lab-default configuration JSON string
    void SetLabDefaults(String const& spec, CommandSource src);
    /// \brief Reset the configuration to lab-default configuration JSON string
    void ResetLabDefaults(CommandSource src);
    /// @brief Report the upload authorisation information
    void GetAuthorisation(CommandSource src);
    /// @brief Set the upload token used to authenticate transmissions
    void SetAuthorisation(String const& data, CommandSource src);
    /// @brief Generate a downloadable version of a given resource in /log directory
    void SnapshotResource(String const& resource, CommandSource src);
    /// @brief Report the auto-upload configuration status
    void ReportUploadConfig(CommandSource src);
    /// @brief Set the auto-upload configuration status
    void ConfigureUpload(String const& command, CommandSource src);
    /// \brief Check for commands, and execute them if found
    void Execute(String const& command, CommandSource src);
    
    /// \brief Generate a string on the appropriate output stream
    void EmitMessage(String const& msg, CommandSource src);
    /// \brief Convert a stringified JSON into a document, with error reporting
    bool EmitJSON(String const& source, CommandSource src);
    /// @brief Generate a list of files into a JSON document
    DynamicJsonDocument GenerateFilelist(void);
    /// @brief Display a NMEA0183 filter ID list
    void DisplayNMEAFilter(logger::N0183IDStore& filter, CommandSource src);
    /// @brief Display an Algorithm Store list
    void DisplayAlgorithmStore(logger::AlgoRequestStore& store, CommandSource src);
};

#endif
