/*! \file DataMetrics.h
 *  \brief Track information about the data being received.
 *
 * In order to provide debugging and management information either to installers or interested
 * (and more sophisticated) users, this module provides the means to track useful information
 * about the data being received (what, when, how well, etc.) so that this can be reported
 * through the 'status' command and otherwise.
 *
 * Copyright (c) 2023, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#ifndef __DATA_METRICS_H__
#define __DATA_METRICS_H__

#include <stdint.h>
#include <Arduino.h>
#include "ArduinoJson.h"

namespace logger {

enum DataIf {
    INT_NONE,
    INT_NMEA0183,
    INT_NMEA2000
};

enum DataObsType {
    DATA_DEPTH = 0,
    DATA_POSITION = 1,
    DATA_TIME = 2,
    DATA_UNKNOWN = 3
};

const int MaximumDataObsRender = 256;
const int MaximumRenderOverhead = 1024;

class DataObs {
public:
    DataObs(void);
    DataObs(uint32_t elapsed, const char *message);
    DataObs(uint32_t elapsed, double lon, double lat, double altitude);
    DataObs(uint32_t elapsed, double depth, double offset);
    DataObs(uint32_t elapsed, uint16_t date, double time);

    DynamicJsonDocument Render(void) const;
    DataIf Interface(void) const { return m_interface; }
    DataObsType ObsType(void) const { return m_obsType; }
    bool Valid(void) const;
    int Size(void) const;

private:
    DataIf      m_interface;
    DataObsType m_obsType;
    String      m_name;
    String      m_tag;
    uint32_t    m_receivedTime;
    String      m_display;

    void Blank(void);
};

class DataMetrics {
public:
    DataMetrics(void);
    ~DataMetrics(void);

    void RegisterObs(DataObs const& obs);
    DynamicJsonDocument LastKnownGood(void) const;
    void SupplyVoltage(double voltage) { m_supplyVoltage = voltage; }
    double SupplyVoltage(void) const { return m_supplyVoltage; }

private:
    DataObs m_nmea0183[3];
    DataObs m_nmea2000[3];
    double m_supplyVoltage;
};

extern DataMetrics Metrics;

} // namespace logger

#endif
