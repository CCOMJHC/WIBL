/*!\file LoggerFirmware.ino
 * \brief Arduino sketch for the NMEA2000 depth/position logger with network time
 *
 * This provides the Arduino-style interface to a NMEA2000 network data logger that's
 * suitable for recording data for Volunteer Geographic Information collection at sea
 * (in keeping with IHO Crowdsourced Bathymetry Working Group recommendations as defined
 * in IHO publication B-12).
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

// The ESP32 version of the CAN bus library used for NMEA2000 packets uses the following two defines
// in the prototype for the setup call to set the default pins.  You could in theory set these up
// directly if you were to construct your own tNMEA2000 object, but since we use the default NMEA2000
// object here, this is now we specify the pins used to talk to the CAN PHY.  TL/DR: Don't remove these
// definitions, even if you can't find any reference to them in the rest of the source code!  Also, don't
// move these after the include for NMEA2000_CAN.h!
#define ESP32_CAN_TX_PIN GPIO_NUM_16
#define ESP32_CAN_RX_PIN GPIO_NUM_17

#include <NMEA2000_CAN.h> /* This auto-generates the NMEA2000 global for bus control */
#include "ArduinoJson.h"

#include "N2kLogger.h"
#include "serial_number.h"
#include "timing.h"
#include "SerialCommand.h"
#include "StatusLED.h"
#include "MemController.h"
#include "IMULogger.h"
#include "GNSSLogger.h"
#include "SupplyMonitor.h"
#include "Configuration.h"
#include "HeapMonitor.h"
#include "DataMetrics.h"

/// Hardware version for the logger implementation (for NMEA2000 declaration)
#define LOGGER_HARDWARE_VERSION "2.5.2"

const unsigned long TransmitMessages[] PROGMEM={0}; ///< List of messages the logger transmits (null set)
const unsigned long ReceiveMessages[] PROGMEM =
  {126992UL /*System Time */,
   127257UL /* Attitude */,
   128267UL /* Water Depth */,
   129026UL /* Course and Speed Over Ground */,
   129029UL /* GNSS Position */,
   130311UL /* Environmental Parameters */,
   130312UL /* Temperature */,
   130313UL /* Humidity */,
   130314UL /* Pressure */,
   130316UL /* Extended Temperature */,
   0
  }; ///< List if messages that the logger expects to receive

timing::Timestamper     *timestamper = nullptr;     ///< Pointer to timestamping object
nmea::N2000::Logger     *N2000Logger = nullptr;     ///< Pointer for NMEA2000 CANbus logger object
nmea::N0183::Logger     *N0183Logger = nullptr;     ///< Pointer for serial NMEA data logger object
imu::Logger             *IMULogger = nullptr;       ///< Pointer for local IMU data logger
gnss::Logger            *GNSSLogger = nullptr;      ///< Pointer for local GNSS data logger
logger::Manager         *logManager = nullptr;      ///< SD log file manager object
StatusLED               *LEDs = nullptr;            ///< Pointer to the status LED manager object
SerialCommand           *CommandProcessor = nullptr;///< Pointer for the command processor object
mem::MemController      *memController = nullptr;   ///< Pointer for the storage abstraction
logger::SupplyMonitor   *supplyMonitor = nullptr;   ///< Pointer for the supply voltage monitoring code

/// \brief Primary setup code for the logger
///
/// Primary setup for the logger.  This needs to configure the hardware Serial object used
/// for reporting debug information (and taking commands), then setting up the primary objects,
/// then starting the NMEA2000 bus interface.  This should allow messages to start to be
/// received through the CAN bus controller.

void setup()
{
    logger::HeapMonitor heap;
    // We need to get these now, since starting the Serial interface might change things
    uint32_t heap_size = heap.HeapSize();
    uint32_t heap_free = heap.CurrentSize();

    Serial.begin(115200);

    Serial.printf("*\n*\n*\n* BOOTING WIBL DATA LOGGER, FIRMWARE VERSION %s\n*\n* For more information: http://wibl.ccom.unh.edu\n*\n*\n*\n", logger::FirmwareVersion().c_str());

    Serial.printf("DBG: At boot, heap is %ld B (%ld B free)\n", heap_size, heap_free);
    Serial.printf("DBG: ");
    heap.FlashMemoryReport(Serial);
    Serial.printf("\n");

    Serial.printf("DBG: After serial start, free heap = %ld B, delta = %ld B\n", heap.CurrentSize(), heap.DeltaSinceLast());

    Serial.println("Configuring LED indicators ...");
    LEDs = new StatusLED();

    Serial.println("Setting up LED indicator for initialising ...");
    LEDs->SetStatus(StatusLED::Status::sINITIALISING);
    Serial.printf("DBG: After LED start and configuration, free heap = %ld B, delta = %ld B\n", heap.CurrentSize(), heap.DeltaSinceLast());

    Serial.println("Checking for stable configuration ...");
    if (!logger::ConfigJSON::SetStableConfig()) {
        Serial.println("ERR: Failed to set stable configuration ... halting.");
        LEDs->SetStatus(StatusLED::Status::sFATAL_ERROR);
        while (1) {
            LEDs->ProcessFlash(); /* Busy loop to make sure the LED flashes */
            delay(100);
        }
    } else {
        Serial.println("INFO: Configuration is now:");
        JsonDocument config(logger::ConfigJSON::ExtractConfig(true));
        String config_str;
        serializeJsonPretty(config, config_str);
        Serial.println(config_str);
    }
    
    Serial.println("Bringing up Storage Controller ...");
    memController = mem::MemControllerFactory::Create();
    
    Serial.println("Starting memory interface ...");
    #ifdef DEBUG_LOG_MANAGER
    Serial.println("DBG: Ignoring memory sub-system for debug purposes.");
    #else
    if (!memController->Start()) {
        Serial.println("ERR: Memory system didn't start ... halting.");
        // Card is not present, or didn't start ... that's a fatal error
        LEDs->SetStatus(StatusLED::Status::sFATAL_ERROR);
        while (1) {
            LEDs->ProcessFlash(); /* Busy loop to make sure the LED flashes */
            delay(100);
        }
    }
    #endif

    Serial.printf("DBG: After memory interface start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());

    // Pull out configuration options early so we can work out whether to start the time-reference objects
    // before making the log manager.
    bool start_nmea_2000, start_nmea_0183, start_motion_sensor, start_gnss_sensor;
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA2000_B, start_nmea_2000);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_NMEA0183_B, start_nmea_0183);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_MOTION_B, start_motion_sensor);
    logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_GNSS_B, start_gnss_sensor);

    // Note that we make raw pointers here, but then transfer responsibility to the Timestamper object
    // for their management.  They're also shared with the specific logger (so the time references can
    // be updated when the appropriate message arrives).  Arguably this should be a std::shared_ptr<>,
    // but since it's an embedded system and very constrained, that seems like a little too much
    // overhead.  TL/DR: Yes, these are auto and therefore will disappear when the routine completes,
    // but that's OK because they still exist in the Timestamper.  These will also appear to be leaked
    // memory, but that's OK too.
    Serial.print("Configuring timestamping sub-system ...\n");
    nmea::N2000::N2KTimeSource *n2k_timesource = nullptr;
    nmea::N0183::N1KTimeSource *n1k_timesource = nullptr;
    gnss::GNSSTimeSource *gnss_timesource = nullptr;

    timestamper = new timing::Timestamper();
    if (start_nmea_2000) {
        n2k_timesource = new nmea::N2000::N2KTimeSource();
        timestamper->RegisterSource(n2k_timesource, timing::TIMING_HIGH);
    }
    if (start_nmea_0183) {
        n1k_timesource = new nmea::N0183::N1KTimeSource();
        timestamper->RegisterSource(n1k_timesource, timing::TIMING_LOW);
    }
    if (start_gnss_sensor) {
        gnss_timesource = new gnss::GNSSTimeSource();
        timestamper->RegisterSource(gnss_timesource, timing::TIMING_REFERENCE);
    }
    Serial.printf("DBG: After timestamper interface start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());

    Serial.println("Configuring logger manager ...");
    logManager = new logger::Manager(LEDs, timestamper, memController);
    Serial.printf("DBG: After log manager start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());
    logManager->AddInventory();
    Serial.printf("DBG: After inventory object start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());
    
    if (start_nmea_2000) {
        Serial.println("Configuring NEMA2000 logger ...");
        N2000Logger = new nmea::N2000::Logger(&NMEA2000, logManager, n2k_timesource);
        Serial.printf("DBG: After NMEA2000 logger start, free heap = %ld B, delta = %ld B\n",
            heap.CurrentSize(), heap.DeltaSinceLast());
    }
  
    if (start_nmea_0183) {
        Serial.println("Configuring NMEA0183 logger (and configuring serial ports)...");
        N0183Logger = new nmea::N0183::Logger(logManager, n1k_timesource);
        Serial.printf("DBG: After NMEA0183 logger start, free heap = %ld B, delta = %ld B\n",
            heap.CurrentSize(), heap.DeltaSinceLast());
    }

    if (start_motion_sensor) {
        Serial.println("Configuring IMU logger ...");
        IMULogger = new imu::Logger(logManager);
        Serial.printf("DBG: After IMU logger start, free heap = %ld B, delta = %ld B\n",
            heap.CurrentSize(), heap.DeltaSinceLast());
    }

    if (start_gnss_sensor) {
        Serial.println("Configuring GNSS logger ...");
        GNSSLogger = new gnss::Logger(logManager, gnss_timesource);
        GNSSLogger->SetVerbose(true);
        Serial.printf("DBG: After GNSS logger start, free heap = %ld B, delta = %ld B\n",
            heap.CurrentSize(), heap.DeltaSinceLast());
    }

    Serial.println("Configuring command processor ...");
    CommandProcessor = new SerialCommand(N2000Logger, N0183Logger, logManager, LEDs);

    Serial.printf("DBG: After SerialCommand start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());

    Serial.println("Starting log manager interface to SD card ...");
    logManager->StartNewLog();

    Serial.printf("DBG: After new log file start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());
  
    if (start_nmea_2000) {
        Serial.println("Starting NMEA2000 bus interface ...");
        NMEA2000.SetProductInformation(GetSerialNumberString(),
                                    1,
                                    "Seabed 2030 NMEA2000 Logger",
                                    N2000Logger->SoftwareVersion().c_str(),
                                    LOGGER_HARDWARE_VERSION
                                    );
        NMEA2000.SetDeviceInformation(GetSerialNumber(),
                                    130,  /* Device Function: PC gateway */
                                    25,   /* Device Class: Inter/Intranetwork Device */
                                    2046  /* */
                                    );
        NMEA2000.SetMode(tNMEA2000::N2km_ListenAndNode, 25);
        NMEA2000.EnableForward(false);
        NMEA2000.ExtendTransmitMessages(TransmitMessages);
        NMEA2000.ExtendReceiveMessages(ReceiveMessages);
        NMEA2000.AttachMsgHandler(N2000Logger);

        NMEA2000.Open();

        Serial.printf("DBG: After NMEA2000 interface start, free heap = %ld B, delta = %ld B\n",
            heap.CurrentSize(), heap.DeltaSinceLast());
    }

    Serial.println("Bringing up supply voltage monitoring ...");
    supplyMonitor = new logger::SupplyMonitor();

    Serial.printf("DBG: After voltage monitoring start, free heap = %ld B, delta = %ld B\n",
        heap.CurrentSize(), heap.DeltaSinceLast());

    Serial.println("Setup complete, setting status for normal operations.");
    LEDs->SetStatus(StatusLED::Status::sNORMAL);

    heap_free = heap.CurrentSize();
    Serial.printf("DBG: After boot and configuration, free heap = %ld B.\n", heap_free);
}

/// \brief General processing loop code for the logger.
///
/// General processing loop.  The code needs to service all of the objects that need
/// timely polling, including the NMEA2000 message stack, flashing the status LEDs,
/// if required, and then checking for (and executing) any commands provided by the
/// user either on the hardware Serial link or through the Bluetooth LE UART, if there's
/// a client configured.

void loop()
{
    if (N2000Logger != nullptr) {
        NMEA2000.ParseMessages();
    }
    if (N0183Logger != nullptr) {
        N0183Logger->ProcessMessages();
    }
    if (IMULogger != nullptr) {
        IMULogger->TransferData();
    }
    if (GNSSLogger != nullptr) {
        GNSSLogger->TransferData();
    }
    if (LEDs != nullptr) {
        LEDs->ProcessFlash();
    }
    if (CommandProcessor != nullptr) {
        CommandProcessor->ProcessCommand();
    }
    if (supplyMonitor->EmergencyPower()) {
        // Eek!  Power went out, so we need to stop logging ASAP
        Serial.printf("DBG: Supply voltage dropped to %f V\n", logger::Metrics.SupplyVoltage());
        CommandProcessor->EmergencyStop();
    }
}
