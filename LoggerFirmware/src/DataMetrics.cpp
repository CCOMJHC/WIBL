/*! \file DataMetrics.cpp
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

#include "DataMetrics.h"

namespace logger {

void DataObs::Blank(void)
{
    m_interface = INT_NONE;
    m_obsType = DATA_UNKNOWN;
    m_receivedTime = 0;
}

DataObs::DataObs(void)
{
   Blank();
}

DataObs::DataObs(uint32_t elapsed, const char *message)
{
    m_interface = INT_NMEA0183;
    m_receivedTime = elapsed;
    m_display = String(message);
    m_tag = m_display.substring(3,6);
    if (m_tag == "DBT" || m_tag == "DPT") {
        m_obsType = DATA_DEPTH;
        m_name = String("Depth");
    } else if (m_tag == "GGA" || m_tag == "GLL") {
        m_obsType = DATA_POSITION;
        m_name = String("Position");
    } else if (m_tag == "ZDA" || m_tag == "RMC") {
        m_obsType = DATA_TIME;
        m_name = String("Time");
    } else {
        Serial.printf("DBG: metrics: NMEA0183 data with tag \"%s\" not recognised.  Ignoring message |%s|.\n", m_tag.c_str(), message);
        Blank();
    }
}

DataObs::DataObs(uint32_t elapsed, double lon, double lat, double altitude)
{
    m_interface = INT_NMEA2000;
    m_obsType = DATA_POSITION;
    m_name = String("Position");
    m_tag = m_name;
    m_receivedTime = elapsed;
    char hemi_lat, hemi_lon;
    if (lat >= 0)
        hemi_lat = 'N';
    else
        hemi_lat = 'S';
    if (lon >= 0)
        hemi_lon = 'E';
    else
        hemi_lon = 'W';
    m_display = String(fabs(lat)) + " " + hemi_lat + ", " + String(fabs(lon)) + " " + hemi_lon + ", " + String(altitude) + "m";
}

DataObs::DataObs(uint32_t elapsed, double depth, double offset)
{
    m_interface = INT_NMEA2000;
    m_obsType = DATA_DEPTH;
    m_name = String("Depth");
    m_tag = m_name;
    m_receivedTime = elapsed;
    m_display = String(depth) + "m/Offset " + String(offset) + "m";
}

DataObs::DataObs(uint32_t elapsed, uint16_t date, double time)
{
    const double seconds_per_day = 24.0 * 60.0 * 60.0;
    m_interface = INT_NMEA2000;
    m_obsType = DATA_TIME;
    m_name = String("Time");
    m_tag = m_name;
    m_receivedTime = elapsed;
    time_t timestamp = static_cast<time_t>(floor(seconds_per_day * date + time));
    m_display = String(asctime(gmtime(&timestamp)));
}

DynamicJsonDocument DataObs::Render(void) const
{
    // Note the fixed size of the document here.  This should be sufficient for one
    // observation, but you should re-assess if you add a lot more into the payload.
    DynamicJsonDocument summary(MaximumDataObsRender);
    uint32_t now = millis();
    uint32_t time_difference = now - m_receivedTime;
    summary["name"] = m_name;
    summary["tag"] = m_tag;
    summary["time"] = time_difference/1000;
    summary["time_units"] = "s";
    summary["display"] = m_display;

    return summary;
}

bool DataObs::Valid(void) const
{
    return m_interface != INT_NONE && m_obsType != DATA_UNKNOWN;
}

int DataObs::Size(void) const
{
    return MaximumDataObsRender;
}

DataMetrics::DataMetrics(void)
{
}

DataMetrics::~DataMetrics(void)
{
}

void DataMetrics::RegisterObs(DataObs const& obs)
{
    if (obs.Interface() == INT_NMEA0183) {
        if (obs.ObsType() != DATA_UNKNOWN) {
            m_nmea0183[obs.ObsType()] = obs;
        }
    } else if (obs.Interface() == INT_NMEA2000) {
        if (obs.ObsType() != DATA_UNKNOWN) {
            m_nmea2000[obs.ObsType()] = obs;
        }
    }
}

DynamicJsonDocument DataMetrics::LastKnownGood(void) const
{
    // The rendering of each DataObs is maximum 256 bytes, so if we compute
    // the number of valid outputs, then add a bit for the fixed overhead,
    // we should be able to estimate the total capacity required for the
    // document.
    int n_0183_valid = 0, n_2000_valid = 0;
    for (int n = 0; n < DATA_UNKNOWN; ++n) {
        if (m_nmea0183[n].Valid()) ++n_0183_valid;
        if (m_nmea2000[n].Valid()) ++n_2000_valid;
    }
    int capacity = m_nmea0183[0].Size()*(n_0183_valid + n_2000_valid) + MaximumRenderOverhead;
    DynamicJsonDocument summary(capacity);

    for (int n = 0; n < DATA_UNKNOWN; ++n) {
        if (m_nmea0183[n].Valid()) {
            summary["nmea0183"]["detail"][n] = m_nmea0183[n].Render();
        }
    }
    summary["nmea0183"]["count"] = n_0183_valid;
    
    for (int n = 0; n < DATA_UNKNOWN; ++n) {
        if (m_nmea2000[n].Valid()) {
            summary["nmea2000"]["detail"][n] = m_nmea2000[n].Render();
        }
    }
    summary["nmea2000"]["count"] = n_2000_valid;

    return summary;
}

DataMetrics Metrics;

};
