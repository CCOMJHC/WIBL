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
#include <SD.h>
#include "BluetoothAdapter.h"
#include "WiFiAdapter.h"
#include "SerialCommand.h"
#include "IncrementalBuffer.h"
#include "OTAUpdater.h"

const uint32_t CommandMajorVersion = 1;
const uint32_t CommandMinorVersion = 0;
const uint32_t CommandPatchVersion = 0;

/// Default constructor for the SerialCommand object.  This stores the pointers for the logger and
/// status LED controllers for reference, and then generates a BLE service object.  This turns on
/// advertising for the BLE UART service, allowing for data to the sent and received over the air.
///
/// \param CANLogger    Pointer to the NMEA2000 data source
/// \param serialLogger Pointer to the NMEA0183 data source
/// \param logManager   Pointer to the object used to access the log files
/// \param led      Pointer to the status LED controller object

SerialCommand::SerialCommand(nmea::N2000::Logger *CANLogger, nmea::N0183::Logger *serialLogger,
                             logger::Manager *logManager, StatusLED *led)
: m_CANLogger(CANLogger), m_serialLogger(serialLogger), m_logManager(logManager), m_led(led)
{
    m_ble = BluetoothFactory::Create();
    m_wifi = WiFiAdapterFactory::Create();
}

/// Default destructor for the SerialCommand object.  This deallocates the BLE service object,
/// which will force a disconnect.  Note that the pointer references for the logger and status LED
/// objects are not deallocated.

SerialCommand::~SerialCommand()
{
    delete m_wifi;
    delete m_ble;
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
        case CommandSource::BluetoothPort:
            Serial.println("ERR: cannot output console log on BLE.");
            break;
        case CommandSource::WirelessPort:
            m_logManager->DumpConsoleLog(m_wifi->Client());
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}

/// Report the sizes of all of the log files that exist in the /logs directory on
/// the attached SD card.  This incidentally reports all of the log files that are
/// ready for transfer.  The report goes out onto the Stream associated with
/// the source of the command.
///
/// \param src  Stream by which the command arrived

void SerialCommand::ReportLogfileSizes(CommandSource src)
{
    EmitMessage("Current log file sizes:\n", src);
    
    int     filenumber[logger::MaxLogFiles];
    int     file_count = m_logManager->CountLogFiles(filenumber);
    String  filename;
    int     filesize;
    for (int f = 0; f < file_count; ++f) {
        m_logManager->EnumerateLogFile(filenumber[f], filename, filesize);
        String line = String("    ") + filename + " " + filesize + " B\n";
        EmitMessage(line, src);
    }
}

/// Report the version string for the current logger implementation.  This also goes out on
/// the BLE interface if there's a client connected.
///
/// \param src  Stream by which the command arrived

void SerialCommand::ReportSoftwareVersion(CommandSource src)
{
    EmitMessage(String("NMEA2000: ") + m_CANLogger->SoftwareVersion() + String("\n"), src);
    EmitMessage(String("NMEA0183: ") + m_serialLogger->SoftwareVersion() + String("\n"), src);
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
    if (filenum == "all") {
        EmitMessage("Erasing all log files ...\n", src);
        m_logManager->RemoveAllLogfiles();
        EmitMessage("All log files erased.\n", src);
    } else {
        long file_num;
        file_num = filenum.toInt();
        EmitMessage(String("Erasing log file ") + file_num + String("\n"), src);
        if (m_logManager->RemoveLogFile(file_num)) {
            String msg = String("Log file ") + file_num + String(" erased.\n");
            EmitMessage(msg, src);
        } else {
            String msg = String("Failed to erase log file ") + file_num + "\n";
            EmitMessage(msg, src);
        }
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
    EmitMessage(m_ble->LoggerIdentifier() + "\n", src);
}

/// Set the identification string for the logger.  This is expected to be a unique ID that can be
/// used to identify the logger, but the firmware does not enforce any particular structure for
/// the string, simply recording whatever is provided.  The string is persisted in non-volatile
/// memory on the board so that it is always available.
///
/// \param identifier   String to use to identify the logger

void SerialCommand::SetIdentificationString(String const& identifier)
{
    m_ble->IdentifyAs(identifier);
}

/// Set the advertising name for the Bluetooth LE UART service established by the module on
/// start.  This is persisted in non-volatile memory on the logger so that it comes up the same
/// on every start.
///
/// \param name String to use for the advertising name of the logger's BLE interface

void SerialCommand::SetBluetoothName(String const& name)
{
    m_ble->AdvertiseAs(name);
}

/// Set up for verbose reporting of messages received by the logger from the NMEA2000 bus.  This
/// is useful only for debugging, since it generates a lot of traffic on the serial output stream.  Allowable
/// options are "on" and "off".
///
/// \param mode String with "on" or "off" to configure verbose reporting mode

void SerialCommand::SetVerboseMode(String const& mode)
{
    if (mode == "on") {
        m_CANLogger->SetVerbose(true);
        m_serialLogger->SetVerbose(true);
    } else if (mode == "off") {
        m_CANLogger->SetVerbose(false);
        m_serialLogger->SetVerbose(false);
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
    m_logManager->Console().println("info: Stopping under control for powerdown.");
    m_logManager->CloseConsole();
    while (true) {
        delay(1000);
    }
    // Intentionally never completes - this is where the code halts
    // for power-down.
}

/// Specify the SSID string to use for the WiFi interface.
///
/// \param ssid SSID to use for the WiFi, when activated

void SerialCommand::SetWiFiSSID(String const& ssid)
{
    m_wifi->SetSSID(ssid);
}

/// Report the SSID for the WiFi on the output channel(s)
///
/// \param src      Stream by which the command arrived

void SerialCommand::GetWiFiSSID(CommandSource src)
{
    String ssid = m_wifi->GetSSID();
    if (src != CommandSource::BluetoothPort) EmitMessage("WiFi SSID: ", src);
    EmitMessage(ssid + "\n", src);
}

/// Specify the password to use for clients attempting to connect to the WiFi access
/// point offered by the module.
///
/// \param password Pre-shared password to expect from the client

void SerialCommand::SetWiFiPassword(String const& password)
{
    m_wifi->SetPassword(password);
}

/// Report the pre-shared password for the WiFi access point.
///
/// \param src      Stream by which the command arrived

void SerialCommand::GetWiFiPassword(CommandSource src)
{
    String password = m_wifi->GetPassword();
    if (src != CommandSource::BluetoothPort) EmitMessage("WiFi Password: ", src);
    EmitMessage(password + "\n", src);
}

/// Turn the WiFi interface on and off, as required by the user
///
/// \param  command     The remnant of the command string from the user
/// \param  src     Stream by which the command arrived

void SerialCommand::ManageWireless(String const& command, CommandSource src)
{
    if (command == "on") {
        if (m_wifi->Startup()) {
            if (src != CommandSource::BluetoothPort)
                EmitMessage("WiFi started on ", src);
            EmitMessage(m_wifi->GetServerAddress() + "\n", src);
        } else {
            EmitMessage("ERR: WiFi startup failed.\n", src);
        }
    } else if (command == "off") {
        m_wifi->Shutdown();
        EmitMessage("WiFi stopped.\n", src);
    } else if (command == "accesspoint") {
        m_wifi->SetWirelessMode(WiFiAdapter::WirelessMode::ADAPTER_SOFTAP);
    } else if (command == "station") {
        m_wifi->SetWirelessMode(WiFiAdapter::WirelessMode::ADAPTER_STATION);
    } else {
        Serial.println("ERR: wireless management command not recognised.");
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
    int file_number = filenum.toInt();
    switch (src) {
        case CommandSource::SerialPort:
            m_logManager->TransferLogFile(file_number, Serial);
            break;
        case CommandSource::BluetoothPort:
            EmitMessage("ERR: not available.\n", src);
            break;
        case CommandSource::WirelessPort:
            m_logManager->TransferLogFile(file_number, m_wifi->Client());
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}

void SerialCommand::ConfigureSerialPort(String const& params, CommandSource src)
{
    uint32_t    port;
    bool        invert;
    
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

/// Output a list of known commands, since there are now enough of them to make remembering them
/// all a little difficult.

void SerialCommand::Syntax(CommandSource src)
{
    EmitMessage(String("Command Syntax (V") + CommandMajorVersion + "." + CommandMinorVersion + "." + CommandPatchVersion + "):\n", src);
    EmitMessage("  advertise bt-name                   Set BLE advertising name.\n", src);
    EmitMessage("  erase file-number|all               Remove a specific [file-number] or all log files.\n", src);
    EmitMessage("  help|syntax                         Generate this list.\n", src);
    EmitMessage("  identify                            Report the logger's unique identification string.\n", src);
    EmitMessage("  invert 0|1                          Invert polarity of RS-422 input on port 0|1.\n", src);
    EmitMessage("  led normal|error|initialising|full  [Debug] Set the indicator LED status.\n", src);
    EmitMessage("  log                                 Output the contents of the console log.\n", src);
    EmitMessage("  password [wifi-password]            Set the WiFi password.\n", src);
    EmitMessage("  setid logger-name                   Set the logger's unique identification string.\n", src);
    EmitMessage("  sizes                               Output list of the extant log files, and their sizes in bytes.\n", src);
    EmitMessage("  ssid [wifi-ssid]                    Set the WiFi SSID.\n", src);
    EmitMessage("  steplog                             Close current log file, and move to the next in sequence.\n", src);
    EmitMessage("  stop                                Close files and go into self-loop for power-down.\n", src);
    EmitMessage("  transfer file-number                Transfer log file [file-number] (WiFi and serial only).\n", src);
    EmitMessage("  version                             Report NMEA0183 and NMEA2000 logger version numbers.\n", src);
    EmitMessage("  verbose on|off                      Control verbosity of reporting for serial input strings.\n", src);
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
    if (cmd == "log") {
        ReportConsoleLog(src);
    } else if (cmd == "sizes") {
        ReportLogfileSizes(src);
    } else if (cmd == "version") {
        ReportSoftwareVersion(src);
    } else if (cmd.startsWith("verbose")) {
        SetVerboseMode(cmd.substring(8));
    } else if (cmd.startsWith("erase")) {
        EraseLogfile(cmd.substring(6), src);
    } else if (cmd == "steplog") {
        m_logManager->CloseLogfile();
        m_logManager->StartNewLog();
    } else if (cmd.startsWith("led")) {
        ModifyLEDState(cmd.substring(4));
    } else if (cmd.startsWith("advertise")) {
        SetBluetoothName(cmd.substring(10));
    } else if (cmd.startsWith("identify")) {
        ReportIdentificationString(src);
    } else if (cmd.startsWith("setid")) {
        SetIdentificationString(cmd.substring(6));
    } else if (cmd == "stop") {
        Shutdown();
    } else if (cmd.startsWith("ssid")) {
        if (cmd.length() == 4)
            GetWiFiSSID(src);
        else
            SetWiFiSSID(cmd.substring(5));
    } else if (cmd.startsWith("password")) {
        if (cmd.length() == 8)
            GetWiFiPassword(src);
        else
            SetWiFiPassword(cmd.substring(9));
    } else if (cmd.startsWith("wireless")) {
        ManageWireless(cmd.substring(9), src);
    } else if (cmd.startsWith("transfer")) {
        TransferLogFile(cmd.substring(9), src);
    } else if (cmd.startsWith("invert")) {
        ConfigureSerialPort(cmd.substring(7), src);
    } else if (cmd == "ota") {
        OTAUpdater updater(); // This puts the logger into a loop which ends with a full reset
    } else if (cmd == "help" || cmd == "syntax") {
        Syntax(src);
    } else {
        Serial.print("Command not recognised: ");
        Serial.println(cmd);
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
        m_serialBuffer.AddCharacter(c);
        if (c == '\n') {
            String cmd(m_serialBuffer.Contents());
            m_serialBuffer.Reset();
            
            cmd.trim();
            
            Serial.print("Found console command: \"");
            Serial.print(cmd);
            Serial.println("\"");

            Execute(cmd, CommandSource::SerialPort);
        }
    }
    if (m_ble->IsConnected() && m_ble->DataAvailable()) {
        String cmd = m_ble->ReceivedString();
        cmd.trim();

        Serial.print("Found BLE command: \"");
        Serial.print(cmd);
        Serial.println("\"");

        Execute(cmd, CommandSource::BluetoothPort);
    }
    if (m_wifi->IsConnected() && m_wifi->DataAvailable()) {
        String cmd = m_wifi->ReceivedString();
        cmd.trim();
        
        Serial.print("Found WiFi command: \"");
        Serial.print(cmd);
        Serial.println("\"");
        
        Execute(cmd, CommandSource::WirelessPort);
    }
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
        case CommandSource::BluetoothPort:
            if (m_ble->IsConnected())
                m_ble->WriteString(msg);
            break;
        case CommandSource::WirelessPort:
            m_wifi->Client().print(msg);
            break;
        default:
            Serial.println("ERR: command source not recognised.");
            break;
    }
}