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
    Wire.setClock(400000); // Set I2C clock to 400kHz for faster data transfer
    Wire.setBufferSize(2048); // Increase buffer size for larger RAWX messages

    if (!m_sensor->begin(Wire)) {
        Serial.println("Failed to initialize ZED-F9P GPS");
        return false;
    }

    // Set larger internal buffer for u-blox library
    m_sensor->setPacketCfgPayloadSize(2048); 

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
    
    // Enable messages needed for RINEX post-processing with optimized rates
    m_sensor->enableMessage(UBX_NAV_PVT, COM_PORT_I2C, 1);       // Position, Velocity, Time (1Hz)
    m_sensor->enableMessage(UBX_NAV_HPPOSLLH, COM_PORT_I2C, 1);  // High Precision Position (1Hz)
    m_sensor->enableMessage(UBX_NAV_TIMEUTC, COM_PORT_I2C, 1);   // UTC Time Solution (1Hz)
    m_sensor->enableMessage(UBX_RXM_RAWX, COM_PORT_I2C, 1);      // Raw GNSS Measurements (1Hz)
    
    // Configure additional settings for better data quality
    m_sensor->setMainTalkerID(SFE_UBLOX_MAIN_TALKER_ID_GP); // Set GPS as main constellation
    m_sensor->setHighPrecisionMode(true);                    // Enable high precision mode
    
    // Save configuration
    m_sensor->saveConfiguration();
}

bool Logger::data_available(void)
{
    return m_sensor->getPVT();
}

void Logger::update(void)
{
    static uint32_t lastI2CReset = 0;
    
    if (data_available()) {
        if (!logGPSData()) {
            // If logging fails, check if it's an I2C error
            if (Wire.getErrorCode() != 0) {
                // Only reset I2C every 5 seconds at most
                if (millis() - lastI2CReset > 5000) {
                    Serial.println("I2C error detected, resetting bus...");
                    Wire.flush();
                    Wire.begin(33, 36);
                    Wire.setClock(400000);
                    lastI2CReset = millis();
                }
            }
        }
    }
}

bool Logger::logGPSData(void)
{
    if (m_logManager == nullptr) return false;

    // Create JSON document for logging
    StaticJsonDocument<2048> doc;  // Further increased size for reliability
    
    doc["type"] = "GPS";
    
    // Standard PVT data
    doc["lat"] = m_sensor->getLatitude() / 10000000.0;
    doc["lon"] = m_sensor->getLongitude() / 10000000.0;
    doc["alt"] = m_sensor->getAltitude() / 1000.0;
    doc["fix"] = m_sensor->getFixType();
    doc["siv"] = m_sensor->getSIV();
    doc["acc_h"] = m_sensor->getHorizontalAccuracy() / 1000.0;
    doc["acc_v"] = m_sensor->getVerticalAccuracy() / 1000.0;
    
    // High precision position data
    if (m_sensor->getHPPOSLLH()) {
        doc["hp_lat"] = m_sensor->getHighResLatitude();
        doc["hp_lon"] = m_sensor->getHighResLongitude();
        doc["hp_alt"] = m_sensor->getHighResAltitude();
    }
    
    // UTC Time data
    if (m_sensor->getNAVTIMEUTC()) {
        doc["utc_year"] = m_sensor->getYear();
        doc["utc_month"] = m_sensor->getMonth();
        doc["utc_day"] = m_sensor->getDay();
        doc["utc_hour"] = m_sensor->getHour();
        doc["utc_min"] = m_sensor->getMinute();
        doc["utc_sec"] = m_sensor->getSecond();
        doc["utc_nano"] = m_sensor->getNano();
    }
    
    // Raw measurement data (for RINEX)
    if (m_sensor->getRXMRAWX()) {
        JsonArray rawx = doc.createNestedArray("rawx");
        for (int i = 0; i < m_sensor->getNumRXMRAWXmessages(); i++) {
            JsonObject meas = rawx.createNestedObject();
            meas["pr"] = m_sensor->getRXMRAWXPseudorange(i);
            meas["cp"] = m_sensor->getRXMRAWXCarrierPhase(i);
            meas["do"] = m_sensor->getRXMRAWXDoppler(i);
            meas["gnss"] = m_sensor->getRXMRAWXGNSSId(i);
            meas["sv"] = m_sensor->getRXMRAWXSvId(i);
            meas["cno"] = m_sensor->getRXMRAWXCNo(i);
        }
    }
    
    try {
        String output;
        serializeJson(doc, output);
        return m_logManager->LogData(output.c_str());
    } catch (const std::exception& e) {
        Serial.printf("Error serializing GPS data: %s\n", e.what());
        return false;
    }
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