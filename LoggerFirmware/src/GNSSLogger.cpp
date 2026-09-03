/*!\file GNSSLogger.cpp
 * \brief WIBL interface to the U-blox ZED-F9P GNSS module
 *
 * This provides an abstraction over the details of the ZED-F9P GNSS module so that it's simpler
 * to use within the logger firmware.  This sets up the module to run with as many constellations as
 * possible, but to use GPS (NavStar) as primary.  The real-time position and time is used as for
 * position records (in case the post-processing fails for any reason), and time synchronisation
 * through a 1PPS signal routed to an ESP32 pin for the interrupt routine.  The real-time position and
 * time go into the output data stream in the same way as NMEA2000 messages, with tags to indicate that
 * they should be the preferred solutions for processing reconstruction if the post-processed data cannot
 * be used for any reason.
 * 
 * Copyright (c) 2026, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include <Wire.h>
#include "N2kTypes.h"
#include "N2kLogger.h"
#include "GNSSLogger.h"

namespace gnss {

const int SoftwareVersionMajor = 1; ///< Software major version for the logger
const int SoftwareVersionMinor = 0; ///< Software minor version for the logger
const int SoftwareVersionPatch = 0; ///< Software patch version for the logger

const int RawDataPacketSize = 1024; ///< Size of raw byte packets transferred from the GNSS
const int ReceiverDataBufferSize = 16384; ///< Size of internal logging buffer for GNSS

logger::Manager *_log_output = nullptr;
nmea::N2000::Logger *_n2k_logger = nullptr;
bool _generate_realtime_debug = false;

int32_t get_utc_days_since_epoch(int32_t year, int32_t month, int32_t day) {
    // Shift calendar so the year begins in March (makes leap year math clean)
    year -= (month <= 2) ? 1 : 0;
    
    int32_t era = (year >= 0 ? year : year - 399) / 400;
    uint32_t yofE = static_cast<uint32_t>(year - era * 400);            // Year of Era
    uint32_t mp = (153 * (month + (month > 2 ? -3 : 9)) + 2) / 5;       // Month Day Prefix
    uint32_t doe = yofE * 365 + yofE / 4 - yofE / 100 + mp + (day - 1);  // Day of Era
    
    int32_t days_since_0000 = era * 146097 + static_cast<int32_t>(doe);
    
    // 719468 is the exact number of days between 0000-03-01 and 1970-01-01
    return days_since_0000 - 719468; 
}

void sfrbx_rcv(UBX_RXM_SFRBX_data_t *data)
{

}

void rawx_rcv(UBX_RXM_RAWX_data_t *data)
{

}

void tim_rcv(UBX_TIM_TP_data_t *data)
{

}

void Logger::setup_tim_rcv(void)
{
    /* Configure the TP for appropriate edge direction, duration, etc. */
}

// TODO: Establish ISR for 1PPS input, which finally marries up the TP_data_t information
// with the micros() number associated with the interrupt.

// Call-back for the GNSS library to report the real-time position, velocity, and time information
// from the module.  This is unlikely to be of a level of accuracy that's of interest for TCB use,
// but is a valuable auxiliary source of data, given the quality of the antenna and receiver, and therefore
// can be written to the output (if valid).
//
// \param data  Structure with broken-out information on the current position solution.
void pvt_rcv(UBX_NAV_PVT_data_t * data)
{
    if (_generate_realtime_debug) {
        Serial.printf("GNSS at %d-%d-%d/%d:%d:%d.%09d (valid date: %d time: %d) acc: %d ns\n",
            data->year, (int)data->month, (int)data->day, (int)data->hour, (int)data->min, (int)data->sec,
            data->nano, (int)data->valid.bits.validDate, (int)data->valid.bits.validTime,
            data->tAcc);
        Serial.printf("GNSS at %.6f E, %.6f N, %.3f U pDOP %.2f nSV: %d type: %d valid: %d\n",
            data->lon/1.0e7, data->lat/1.0e7, data->height/1000.0, data->pDOP/100.0,
            (int)data->numSV, (int)data->fixType, (int)data->flags.bits.gnssFixOK);
        Serial.printf("GNSS at vel. %.3f N, %.3f E, %.3f D acc: %.3f m/s\n",
            data->velN/1000.0, data->velE/1000.0, data->velD/1000.0, data->sAcc/1000.0);
    }

    if (data->valid.bits.validDate == 0 || data->valid.bits.validTime == 0) {
        // Only process the data if at least the time's marked as valid
        if (_generate_realtime_debug) {
            Serial.printf("WARN: GNSS time not valid; ignoring all data.\n",
                data->year, (int)data->month, (int)data->day,
                (int)data->hour, (int)data->min, (int)data->sec, data->nano);
        }
        return;
    }
    if (data->flags.bits.gnssFixOK == 0) {
        // Only generate the position packet if it's marked as valid
        if (_generate_realtime_debug) {
            Serial.printf("WARN: GNSS position not valid; ignored.\n",
                data->lon/1.0e7, data->lat/1.0e7, data->height/1000.0, data->pDOP/100.0,
                (int)data->numSV, (int)data->fixType);
        }
        return;
    }

    // Note that the time in the packet is meant to be the validity time of the observation, not
    // when it was sent.  So we convert this for metadata on the position, but get a separate
    // timestamp from the time source for the header.
    uint32_t epoch_days = get_utc_days_since_epoch(data->year, data->month, data->day);
    double   seconds_in_day = data->hour * 3600.0 + data->min * 60.0 + data->sec +
                              data->nano / 1.0e9;
    
    // TODO: We need to get a TimeDatum for when we think the packet arrived
    nmea::N2000::Timestamp::TimeDatum time_datum;

    Serialisable position(time_datum.SerialisationSize() +
                    sizeof(uint8_t) +   // talker
                    2*sizeof(uint16_t) + // days since epoch and reference station ID
                    8*sizeof(double) + // seconds in day, position and associated metrics
                    6*sizeof(uint8_t) // qualifiers, station ID, correction age, etc.
                    );
    time_datum.Serialise(position);
    position += (uint8_t)0xFF; // Means "me"
    position += (uint16_t)epoch_days;
    position += seconds_in_day;
    position += data->lat / 1.0e7;
    position += data->lon / 1.0e7;
    position += data->height / 1000.0;
    position += (uint8_t)tN2kGNSStype::N2kGNSSt_GPS; // Signal source (GPS, GLONASS, Galileo, etc.); assume GPS
    position += (uint8_t)tN2kGNSSmethod::N2kGNSSm_GNSSfix; // We're always operating unaided, so if it's valid ...
    position += data->numSV;
    position += data->hAcc / 1000.0; // Don't have HDOP so substitute hor. acc in metres.
    position += data->pDOP / 100.0; // Denormalise; integer scaling is 0.01 units
    position += (data->height  - data->hMSL) / 1000.0; // Separation isn't reported, but this should be the difference
    position += (uint8_t)0; // Number of reference stations: we're acting unaided
    position += (uint8_t)0; // Reference station type: N/A
    position += (uint16_t)0; // Reference station ID: N/A
    position += (double)0.0; // Correction age: we're acting unaided

    _log_output->Record(logger::Manager::PacketIDs::Pkt_GNSS, position);
}

void Logger::SetVerbose(bool verbose)
{
    m_verbose = verbose;
    _generate_realtime_debug = verbose;
}

Logger::Logger(logger::Manager *output, nmea::N2000::Logger *n2k)
: m_output(output), m_verbose(false)
{
    _log_output = output; // !ick!
    _n2k_logger = n2k;
    _generate_realtime_debug = m_verbose;

    m_sensor = new SFE_UBLOX_GNSS();
    if (!Wire.begin()) {
        Serial.println("ERROR: Failed to initialise Wire interface for GNSS module; logging disabled.");
        delete m_sensor; m_sensor = nullptr; m_output = nullptr;
        return;
    }
    if (!m_sensor->setPacketCfgPayloadSize(3000)) {
        Serial.println("ERROR: failed to set receive packet size for GNSS module; logging disabled.");
        delete m_sensor; m_sensor = nullptr; m_output = nullptr;
        return;
    }
    m_sensor->setFileBufferSize(ReceiverDataBufferSize);
    if (!m_sensor->begin()) {
        Serial.println("ERROR: failed to start GNSS module; logging disabled.");
        delete m_sensor; m_sensor = nullptr; m_output = nullptr;
        return;
    }

    // Configuration for real-time TP, PVT and raw observations for post-processing
    setup_tim_rcv();
    m_sensor->setI2COutput(COM_TYPE_UBX);
    m_sensor->saveConfigSelective(VAL_CFG_SUBSEC_IOPORT);
    m_sensor->setAutoRXMSFRBXcallbackPtr(&sfrbx_rcv);
    m_sensor->logRXMSFRBX();
    m_sensor->setAutoRXMRAWXcallbackPtr(&rawx_rcv);
    m_sensor->logRXMRAWX();
    m_sensor->setAutoPVTcallbackPtr(&pvt_rcv);
    m_sensor->logNAVPVT();
    m_sensor->setAutoTIMTPcallbackPtr(&tim_rcv);
    m_sensor->logTIMTP();
    m_sensor->setDynamicModel(DYN_MODEL_SEA);
    m_sensor->setNavigationFrequency(1); // RAWX is a lot of data; we don't need more than 1Hz
    m_pktBuffer = new uint8_t[RawDataPacketSize];
}

Logger::~Logger(void)
{
    delete m_sensor;
    delete m_pktBuffer;
}

bool Logger::isAvailable(void)
{
    return m_sensor != nullptr;
}

void Logger::TransferData(void)
{
    if (!isAvailable()) return;
    m_sensor->checkUblox();
    m_sensor->checkCallbacks();
    while (m_sensor->fileBufferAvailable() >= RawDataPacketSize) {
        Serialisable pkt(RawDataPacketSize);
        m_sensor->extractFileBufferData(m_pktBuffer, RawDataPacketSize);
        pkt.add(RawDataPacketSize, m_pktBuffer);
        m_output->Record(logger::Manager::PacketIDs::Pkt_RawGNSS, pkt);
        m_sensor->checkUblox();
        m_sensor->checkCallbacks();
    }
}

/// Assemble a logger version string
///
/// \return Printable version of the version information

String Logger::SoftwareVersion(void)
{
    String rtn;
    rtn = String(SoftwareVersionMajor) + "." + String(SoftwareVersionMinor) +
            "." + String(SoftwareVersionPatch);
    return rtn;
}

void Logger::SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch)
{
    major = SoftwareVersionMajor;
    minor = SoftwareVersionMinor;
    patch = SoftwareVersionPatch;   
}

}
