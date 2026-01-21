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

#include <functional>
#include <Wire.h>
#include "GNSSLogger.h"

namespace gnss {

const int SoftwareVersionMajor = 1; ///< Software major version for the logger
const int SoftwareVersionMinor = 0; ///< Software minor version for the logger
const int SoftwareVersionPatch = 0; ///< Software patch version for the logger

const int RawDataPacketSize = 1024; ///< Size of raw byte packets transferred from the GNSS
const int ReceiverDataBufferSize = 16384; ///< Size of internal logging buffer for GNSS

logger::Manager *callback_log_output = nullptr;

void sfrbx_rcv(UBX_RXM_SFRBX_data_t *ubxDataStruct)
{

}

void rawx_rcv(UBX_RXM_RAWX_data_t *ubxDataStruct)
{

}

void pvt_rcv(UBX_NAV_PVT_data_t * ubxDataStruct)
{

}

Logger::Logger(logger::Manager *output)
: m_output(output), m_verbose(false)
{
    m_sensor = new SFE_UBLOX_GNSS();
    if (!Wire.begin()) {
        Serial.println("Error: Failed to initialise Wire interface for GNSS module; logging disabled.");
        delete m_sensor;  m_sensor = nullptr; m_output = nullptr;
        return;
    }
    if (!m_sensor->setPacketCfgPayloadSize(3000)) {
        Serial.println("Error: failed to set receive packet size for GNSS module; logging disabled.");
        delete m_sensor;  m_sensor = nullptr; m_output = nullptr;
        return;
    }
    m_sensor->setFileBufferSize(ReceiverDataBufferSize);
    callback_log_output = output; // !ick!
    if (!m_sensor->begin()) {
        Serial.println("Error: failed to start GNSS module; logging disabled.");
        delete m_sensor;  m_sensor = nullptr; m_output = nullptr;
        return;
    }

    // Configuration for real-time PVT and raw observations for post-processing
    m_sensor->setI2COutput(COM_TYPE_UBX);
    m_sensor->saveConfigSelective(VAL_CFG_SUBSEC_IOPORT);
    m_sensor->setAutoRXMSFRBXcallbackPtr(&sfrbx_rcv);
    m_sensor->logRXMSFRBX();
    m_sensor->setAutoRXMRAWXcallbackPtr(&rawx_rcv);
    m_sensor->logRXMRAWX();
    m_sensor->setAutoPVTcallbackPtr(&pvt_rcv);
    m_sensor->logNAVPVT();
    m_sensor->setDynamicModel(DYN_MODEL_SEA);
    m_sensor->setNavigationFrequency(1); // RAWX is a lot of data; we don't need more than 1Hz
    m_pktBuffer = new uint8_t[RawDataPacketSize];
}

Logger::~Logger(void)
{
    delete m_sensor;
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
        pkt.deposit(m_pktBuffer, RawDataPacketSize);
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
