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

private:
    SFE_UBLOX_GNSS *m_sensor;
    logger::Manager *m_logManager;
    bool m_verbose;

    void configureDevice(void);
    void logGPSData(void);
};

} // namespace gps

#endif // __GPS_LOGGER_H__ 