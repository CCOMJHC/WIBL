#include "GPSLogger.h"
#include "serialisation.h"
#include "LogManager.h"
#include "Wire.h"

namespace gps {

Logger::Logger(logger::Manager *logManager)
: m_logManager(logManager), m_verbose(false), m_isCalibrating(false)
{
    m_sensor = new SFE_UBLOX_GNSS();
}

Logger::~Logger(void)
{
    delete m_sensor;
}

bool Logger::begin(void)
{
    // Configure I2C pins for GPS
    Wire.begin(33, 36); // SDA, SCL

    if (!m_sensor->begin(Wire)) {
        Serial.println("Failed to initialize ZED-F9P GPS");
        return false;
    }

    configureDevice();
    return true;
}

void Logger::configureDevice(void)
{
    // Configure GPS settings
    m_sensor->setI2COutput(COM_TYPE_UBX);                 // Set the I2C port to output UBX only
    m_sensor->setNavigationFrequency(5);                  // Set output rate to 5 Hz
    m_sensor->setAutoPVT(true);                          // Enable automatic PVT messages
    m_sensor->setDynamicModel(DYN_MODEL_MARINE);         // Set dynamic model for marine applications
    
    // Configure RTCM message output
    m_sensor->enableRTCMmessage(UBX_RTCM_1005, COM_PORT_I2C, 1);   // Stationary RTK Reference
    m_sensor->enableRTCMmessage(UBX_RTCM_1077, COM_PORT_I2C, 1);   // GPS MSM7
    m_sensor->enableRTCMmessage(UBX_RTCM_1087, COM_PORT_I2C, 1);   // GLONASS MSM7
    m_sensor->enableRTCMmessage(UBX_RTCM_1127, COM_PORT_I2C, 1);   // BeiDou MSM7
    
    // Save configuration
    m_sensor->saveConfiguration();
}

bool Logger::data_available(void)
{
    return m_sensor->getPVT();
}

void Logger::update(void)
{
    if (data_available()) {
        logGPSData();
    }
}

void Logger::logGPSData(void)
{
    if (m_logManager == nullptr) return;

    // Create JSON document for logging
    StaticJsonDocument<512> doc;
    
    doc["type"] = "GPS";
    doc["lat"] = m_sensor->getLatitude() / 10000000.0;
    doc["lon"] = m_sensor->getLongitude() / 10000000.0;
    doc["alt"] = m_sensor->getAltitude() / 1000.0;
    doc["fix"] = m_sensor->getFixType();
    doc["siv"] = m_sensor->getSIV();
    doc["acc_h"] = m_sensor->getHorizontalAccuracy() / 1000.0;
    doc["acc_v"] = m_sensor->getVerticalAccuracy() / 1000.0;
    
    String output;
    serializeJson(doc, output);
    m_logManager->LogData(output.c_str());
}

bool Logger::runCalibration(void)
{
    if (m_isCalibrating) return false;
    
    m_isCalibrating = true;
    configureCalibration();
    
    // Log calibration start
    if (m_logManager != nullptr) {
        StaticJsonDocument<256> doc;
        doc["type"] = "GPS_CAL";
        doc["event"] = "start";
        
        String output;
        serializeJson(doc, output);
        m_logManager->LogData(output.c_str());
    }
    
    return true;
}

void Logger::configureCalibration(void)
{
    // Set high precision mode
    m_sensor->setAutoPVT(false);
    m_sensor->setNavigationFrequency(1);  // Reduce to 1Hz during calibration
    
    // Enable Raw Measurements
    m_sensor->enableMeasurement(UBX_RXM_RAWX, true);
    m_sensor->enableMeasurement(UBX_RXM_SFRBX, true);
    
    // Configure Survey-In Mode
    m_sensor->enableSurveyMode(300, 2.0); // 300 seconds minimum, 2.0m precision
    
    // Save the calibration configuration
    m_sensor->saveConfiguration();
}

bool Logger::isCalibrating(void)
{
    if (!m_isCalibrating) return false;
    
    bool surveying = m_sensor->getSurveyInActive();
    bool valid = m_sensor->getSurveyInValid();
    
    if (!surveying && valid) {
        // Calibration completed successfully
        stopCalibration();
        return false;
    }
    
    // Log current calibration status
    if (m_logManager != nullptr) {
        StaticJsonDocument<256> doc;
        doc["type"] = "GPS_CAL";
        doc["event"] = "progress";
        doc["observations"] = m_sensor->getSurveyInObservationTime();
        doc["mean_accuracy"] = m_sensor->getSurveyInMeanAccuracy();
        
        String output;
        serializeJson(doc, output);
        m_logManager->LogData(output.c_str());
    }
    
    return true;
}

void Logger::stopCalibration(void)
{
    if (!m_isCalibrating) return;
    
    // Disable Survey-In Mode
    m_sensor->disableSurveyMode();
    
    // Restore normal operation settings
    configureDevice();
    
    m_isCalibrating = false;
    
    // Log calibration completion
    if (m_logManager != nullptr) {
        StaticJsonDocument<256> doc;
        doc["type"] = "GPS_CAL";
        doc["event"] = "complete";
        doc["valid"] = m_sensor->getSurveyInValid();
        doc["total_time"] = m_sensor->getSurveyInObservationTime();
        doc["final_accuracy"] = m_sensor->getSurveyInMeanAccuracy();
        
        String output;
        serializeJson(doc, output);
        m_logManager->LogData(output.c_str());
    }
}

} // namespace gps 