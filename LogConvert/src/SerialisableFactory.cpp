/*! \file SerialisableFactory.cpp
 *  \brief Convert from various data packet types to a Serialisable
 *
 *  This object constructs a Serialisable from a number of different input packets
 *  so that the user doesn't have to fret about the details of the conversion.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping and
 * NOAA/UNH Joint Hydrographic Center.  All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
 * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#include <set>

#include "SerialisableFactory.h"
#include "N2kMessages.h"
#include "N2kMsg.h"
#include "nlohmann/json.hpp"
#include <fstream>
#include <cstdint>
#include <iostream>

using namespace nlohmann;

/// \class DummyTimestamp
/// \brief Helper class to provide serialisation services for timestamp information
///
/// When converting data without timestamps, we occasionally need to be able to hold an elapsed time
/// when there isn't a date or real-world timestamp.  This class provides serialisation services for
/// this type of timestamp.

class DummyTimestamp
{
public:
    /// \brief Set timestamp to a given elapsed time
    ///
    /// Default constructor for a give elapsed time.  Typically this is the time since the logger
    /// booted in milliseconds, but the code doesn't really care what the units are.
    ///
    /// \param elapsed  Time since start of recording for the data (typically milliseconds)

    DummyTimestamp(uint32_t elapsed)
    : m_elapsed(elapsed) {}
    
    /// \brief Generate a binary representation of the timestamp
    ///
    /// Convert the elapsed time (and a default date and timestamp) into binary format in a \a Serialisable
    /// so that it can be added to an output WIBL file.
    ///
    /// \param target   Shared pointer for the output \a Serialisable object

    void Serialise(std::shared_ptr<Serialisable> target)
    {
        uint16_t date = 0;
        double timestamp = -1.0;
        *target += date;
        *target += timestamp;
        *target += m_elapsed;
    }
    
    /// \brief Compute the size of the output packet of binary data
    ///
    /// This computes the size in bytes of the data that is going to be written to the binary
    /// packet, allowing for buffers to be allocated.
    ///
    /// \return Size of the output packet in bytes

    uint32_t SerialisationSize(void)
    {
        return sizeof(uint16_t) + sizeof(double) + sizeof(uint32_t);
    }
    
private:
    uint32_t    m_elapsed;  ///< Elapsed time for the packet since the logger booted
};

/// \brief Translate a NMEA2000 SystemTime packet
///
/// Convert from a standard NMEA2000 SystemTime packet into a \a Serialisable.
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleSystemTime(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char   SID;
    uint16_t        date = 0;
    double          timestamp = -1.0;
    tN2kTimeSource  source;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kSystemTime(msg, SID, date, timestamp, source)) {
        if (source != N2ktimes_LocalCrystalClock) {
            if (N2kIsNA(date) || N2kIsNA(timestamp) || N2kIsNA((uint32_t)msg.MsgTime) || N2kIsNA((uint8_t)source)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(sizeof(uint16_t) + sizeof(double) + sizeof(unsigned long) + sizeof(uint8_t)*2));
            *rtn += date;
            *rtn += timestamp;
            *rtn += static_cast<uint32_t>(msg.MsgTime);
            *rtn += (uint8_t)msg.Source;
            *rtn += (uint8_t)source;
        }
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Attitude packet
///
/// Convert from a standard NMEA2000 Attitude packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleAttitude(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char   SID;
    uint16_t        day;
    double          timestamp, yaw, pitch, roll;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kAttitude(msg, SID, yaw, pitch, roll)) {
        DummyTimestamp t(msg.MsgTime);
        if (N2kIsNA(yaw) || N2kIsNA(pitch) || N2kIsNA(roll)) {
            no_data_detected = true;
        }

        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + sizeof(uint8_t) + 3*sizeof(double)));
        t.Serialise(rtn);
        *rtn += (uint8_t)msg.Source;
        *rtn += yaw;
        *rtn += pitch;
        *rtn += roll;
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Depth packet
///
/// Convert from a standard NMEA2000 Depth packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleDepth(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char SID;
    double depth, offset, range;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kWaterDepth(msg, SID, depth, offset, range)) {
        DummyTimestamp t(msg.MsgTime);
        if (N2kIsNA(depth) || N2kIsNA(offset) || N2kIsNA(range)) {
            no_data_detected = true;
        }

        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + sizeof(uint8_t) + 3*sizeof(double)));
        t.Serialise(rtn);
        *rtn += (uint8_t)msg.Source;
        *rtn += depth;
        *rtn += offset;
        *rtn += range;
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Course Over Ground packet
///
/// Convert from a standard NMEA2000 Course Over Ground packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleCOG(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char SID;
    tN2kHeadingReference ref;
    double  cog, sog;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kCOGSOGRapid(msg, SID, ref, cog, sog)) {
        if (ref == N2khr_true) {
            DummyTimestamp t(msg.MsgTime);
            if (N2kIsNA(cog) || N2kIsNA(sog)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + sizeof(uint8_t) + 2*sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)msg.Source;
            *rtn += cog;
            *rtn += sog;
        }
    }
    return rtn;
}

/// \brief Translate a NMEA2000 GNSS positioning packet
///
/// Convert from a standard NMEA2000 GNSS positioning packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleGNSS(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char   SID;
    uint16_t        datestamp;
    double          timestamp;
    double          latitude, longitude, altitude;
    tN2kGNSStype    rec_type;
    tN2kGNSSmethod  rec_method;
    unsigned char   nSvs;
    double          hdop, pdop, sep;
    unsigned char   nRefStations;
    tN2kGNSStype    refStationType;
    uint16_t        refStationID;
    double          correctionAge;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kGNSS(msg, SID, datestamp, timestamp, latitude, longitude, altitude,
                     rec_type, rec_method, nSvs, hdop, pdop, sep, nRefStations,
                     refStationType, refStationID, correctionAge)) {
        DummyTimestamp t(msg.MsgTime);
        if (N2kIsNA(datestamp) || N2kIsNA(timestamp) || N2kIsNA(latitude) || N2kIsNA(longitude) || N2kIsNA(altitude)
            || N2kIsNA((uint8_t)rec_type) || N2kIsNA((uint8_t)rec_method) || N2kIsNA(nSvs) || N2kIsNA(hdop) || N2kIsNA(pdop)
            || N2kIsNA(sep) || N2kIsNA(nRefStations) || N2kIsNA((uint8_t)refStationType) || N2kIsNA(refStationID) || N2kIsNA(correctionAge)) {
            no_data_detected = true;
        }
        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + sizeof(uint8_t) + 2*sizeof(uint16_t) + 8*sizeof(double) + 5));
        t.Serialise(rtn); // Put in the standard timestamp, as well as the in-message one.
        *rtn += (uint8_t)msg.Source;
        *rtn += datestamp; *rtn += timestamp;
        *rtn += latitude; *rtn += longitude; *rtn += altitude;
        *rtn += (uint8_t)rec_type; *rtn += (uint8_t)rec_method;
        *rtn += nSvs;
        *rtn += hdop; *rtn += pdop;
        *rtn += sep;
        *rtn += nRefStations;
        *rtn += (uint8_t)refStationType;
        *rtn += refStationID;
        *rtn += correctionAge;
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Environment (temperature, humidity, and pressure) packet
///
/// Convert from a standard NMEA2000 Environment (temperature, humidity, and pressure) packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleEnvironment(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char SID;
    tN2kTempSource      t_source;
    tN2kHumiditySource  h_source;
    double              temp, humidity, pressure;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kEnvironmentalParameters(msg, SID, t_source, temp, h_source, humidity, pressure)) {
        DummyTimestamp t(msg.MsgTime);
        if (N2kIsNA((uint8_t)t_source) || N2kIsNA(temp) || N2kIsNA((uint8_t)h_source) || N2kIsNA(humidity) || N2kIsNA(pressure)) {
            no_data_detected = true;
        }

        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + sizeof(uint8_t) +
                                            3*sizeof(double) + 2*sizeof(uint8_t)));
        t.Serialise(rtn);
        *rtn += (uint8_t)msg.Source;
        *rtn += (uint8_t)t_source;
        *rtn += temp;
        *rtn += (uint8_t)h_source;
        *rtn += humidity;
        *rtn += pressure;
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Temperature packet
///
/// Convert from a standard NMEA2000 Temperature packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleTemperature(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char   SID;
    unsigned char   temp_instance;
    tN2kTempSource  t_source;
    double          temp, set_temp;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kTemperature(msg, SID, temp_instance, t_source, temp, set_temp)) {
        if (t_source == N2kts_SeaTemperature || t_source == N2kts_OutsideTemperature) {
            DummyTimestamp t(msg.MsgTime);
            if (N2kIsNA((uint8_t)t_source) || N2kIsNA(temp)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() +
                                                2*sizeof(uint8_t) + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)msg.Source;
            *rtn += (uint8_t)t_source;
            *rtn += temp;
        }
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Humidity packet
///
/// Convert from a standard NMEA2000 Humidity packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleHumidity(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char       SID;
    unsigned char       humidity_instance;
    tN2kHumiditySource  h_source;
    double              humidity;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kHumidity(msg, SID, humidity_instance, h_source, humidity)) {
        if (h_source == N2khs_OutsideHumidity) {
            DummyTimestamp t(msg.MsgTime);
            if (N2kIsNA((uint8_t)h_source) || N2kIsNA(humidity)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 2*sizeof(uint8_t) + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)msg.Source;
            *rtn += (uint8_t)h_source;
            *rtn += humidity;
        }
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Pressure packet
///
/// Convert from a standard NMEA2000 Pressure packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandlePressure(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char       SID;
    unsigned char       pressure_instance;
    tN2kPressureSource  p_source;
    double              pressure;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kPressure(msg, SID, pressure_instance, p_source, pressure)) {
        if (p_source == N2kps_Atmospheric) {
            DummyTimestamp t(msg.MsgTime);
            if (N2kIsNA((uint8_t)p_source) || N2kIsNA(pressure)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 2*sizeof(uint8_t) + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)msg.Source;
            *rtn += (uint8_t)p_source;
            *rtn += pressure;
        }
    }
    return rtn;
}

/// \brief Translate a NMEA2000 Extended Temperature packet
///
/// Convert from a standard NMEA2000 Extended Temperature packet into a \a Serialisable
///
/// \param msg  Reference for the SystemTime packet to convert for serialisation
/// \return Shared pointer to the \a Serialisable packet

std::shared_ptr<Serialisable> HandleExtTemperature(tN2kMsg& msg, bool& no_data_detected)
{
    unsigned char   SID;
    unsigned char   temp_instance;
    tN2kTempSource  t_source;
    double          temp, set_temp;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kTemperatureExt(msg, SID, temp_instance, t_source, temp, set_temp)) {
        if (t_source == N2kts_SeaTemperature || t_source == N2kts_OutsideTemperature) {
            DummyTimestamp t(msg.MsgTime);
            if (N2kIsNA((uint8_t)t_source) || N2kIsNA(temp)) {
                no_data_detected = true;
            }

            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 2*sizeof(uint8_t) + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)msg.Source;
            *rtn += (uint8_t)t_source;
            *rtn += temp;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleBinary(tN2kMsg& msg)
{
    std::shared_ptr<Serialisable> rtn;
    DummyTimestamp t(msg.MsgTime);
    rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 5 + msg.DataLen));
    t.Serialise(rtn);
    *rtn += static_cast<uint32_t>(msg.PGN);
    *rtn += static_cast<uint32_t>(msg.DataLen);
    for (int n = 0; n < msg.DataLen; ++n) {
        *rtn += static_cast<uint8_t>(msg.Data[n]);
    }
    return rtn;
}

/// \brief Handle conversion of a NMEA2000 packet into a \a Serialisable
///
/// This dispatches the packet provided into a specific format converter that translates into a
/// \a Serialisable packet, and adds the payload-id tag required to serialise it.
///
/// \param msg          NMEA2000 packet to convert to \a Serialisable
/// \param payload_id   Reference (output) for the payload-id number for the packet
/// \return Shared pointer for the \a Serialisable object containing the binary data

std::shared_ptr<Serialisable> SerialisableFactory::Convert(tN2kMsg& msg,
    std::set<uint32_t> const& pgns, bool const& all_pgn,
    PayloadID& payload_id, bool& no_data_detected)
{
    std::shared_ptr<Serialisable> rtn;
    payload_id = Pkt_Version;   // Invalid for normal users (can only be added by serialisation code)
    
    switch (msg.PGN) {
        case 126992UL:  rtn = HandleSystemTime(msg, no_data_detected);        payload_id = Pkt_SystemTime;    break;
        case 127257UL:  rtn = HandleAttitude(msg, no_data_detected);          payload_id = Pkt_Attitude;      break;
        case 128267UL:  rtn = HandleDepth(msg, no_data_detected);             payload_id = Pkt_Depth;         break;
        case 129026UL:  rtn = HandleCOG(msg, no_data_detected);               payload_id = Pkt_COG;           break;
        case 129029UL:  rtn = HandleGNSS(msg, no_data_detected);              payload_id = Pkt_GNSS;          break;
        case 130311UL:  rtn = HandleEnvironment(msg, no_data_detected);       payload_id = Pkt_Environment;   break;
        case 130312UL:  rtn = HandleTemperature(msg, no_data_detected);       payload_id = Pkt_Temperature;   break;
        case 130313UL:  rtn = HandleHumidity(msg, no_data_detected);          payload_id = Pkt_Humidity;      break;
        case 130314UL:  rtn = HandlePressure(msg, no_data_detected);          payload_id = Pkt_Pressure;      break;
        case 130316UL:  rtn = HandleExtTemperature(msg, no_data_detected);    payload_id = Pkt_Temperature;   break;
        default:
            if (all_pgn || pgns.find(msg.PGN) != pgns.end()) {
                no_data_detected = false; // Since we don't parse the packet, we can't detect this
                rtn = HandleBinary(msg);
                payload_id = Pkt_N2kBinary;
            }
            break;
    }
    return rtn;
}

/// \brief Handle conversion of a NMEA0183 sentence into a \a Serialisable
///
/// This does a simple conversion of the NMEA0183 sentence string into a \a Serialisable packet (of the NMEAString type).
///
/// \param elapsed_time Time since logger boot at which the NMEA sentence was received
/// \param nmea_string  NMEA10183 string received
/// \param payload_id   Reference (output) for the payload-id number for the packet
/// \return Shared pointer for the \a Serialisable object containing the binary data

std::shared_ptr<Serialisable> SerialisableFactory::Convert(uint32_t elapsed_time, std::string& nmea_string, PayloadID& payload_id)
{
    std::shared_ptr<Serialisable> rtn(new Serialisable(nmea_string.length() + 4));
    *rtn += elapsed_time;
    *rtn += nmea_string.c_str();
    
    payload_id = Pkt_NMEAString;
    return rtn;
}

std::shared_ptr<Serialisable> SerialisableFactory::Convert(std::string const& metadata_filename, PayloadID& payload_id)
{
    std::ifstream metadata(metadata_filename);
    json params = json::parse(metadata);
    std::string encoded = params.dump();
    std::shared_ptr<Serialisable> rtn(new Serialisable(encoded.length() + 4));
    *rtn += static_cast<uint32_t>(encoded.length());
    *rtn += encoded.c_str();
    payload_id = Pkt_JSONMetadata;
    return rtn;
}