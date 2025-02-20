#ifndef __GPS_LOGGER_H__
#define __GPS_LOGGER_H__

#include <Arduino.h>
#include <SparkFun_u-blox_GNSS_Arduino_Library.h>
#include "LogManager.h"

namespace gps {

class Logger {
public:
    Logger(logger::Manager *logManager);
    ~Logger(void);
    
    bool begin(void);
    void update(void);
    bool data_available(void);
    bool runCalibration(void);
    bool isCalibrating(void);
    void stopCalibration(void);

private:
    SFE_UBLOX_GNSS *m_sensor;
    logger::Manager *m_logManager;
    bool m_isCalibrating;
    static const uint32_t I2C_BUFFER_SIZE = 2048;
    static const uint32_t I2C_CLOCK_SPEED = 400000;

    void configureDevice(void);
    bool logGPSData(void);
    void configureCalibration(void);
};

} // namespace gps

#endif // __GPS_LOGGER_H__ 