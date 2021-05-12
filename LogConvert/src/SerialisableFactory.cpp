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

#include "SerialisableFactory.h"
#include "N2kMessages.h"

class DummyTimestamp
{
public:
    DummyTimestamp(uint32_t elapsed)
    : m_elapsed(elapsed) {}
    
    void Serialise(std::shared_ptr<Serialisable> target)
    {
        uint16_t date = 0;
        double timestamp = -1.0;
        *target += date;
        *target += timestamp;
        *target += m_elapsed;
    }
    
    uint32_t SerialisationSize(void)
    {
        return sizeof(uint16_t) + sizeof(double) + sizeof(uint32_t);
    }
    
private:
    uint32_t    m_elapsed;
};

std::shared_ptr<Serialisable> HandleSystemTime(tN2kMsg& msg)
{
    unsigned char   SID;
    uint16_t        date = 0;
    double          timestamp = -1.0;
    tN2kTimeSource  source;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kSystemTime(msg, SID, date, timestamp, source)) {
        if (source != N2ktimes_LocalCrystalClock) {
            rtn = std::shared_ptr<Serialisable>(new Serialisable(sizeof(uint16_t) + sizeof(double) + sizeof(unsigned long) + 1));
            *rtn += date;
            *rtn += timestamp;
            *rtn += static_cast<uint32_t>(msg.MsgTime);
            *rtn += (uint8_t)source;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleAttitude(tN2kMsg& msg)
{
    unsigned char   SID;
    uint16_t        day;
    double          timestamp, yaw, pitch, roll;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kAttitude(msg, SID, yaw, pitch, roll)) {
        DummyTimestamp t(msg.MsgTime);
        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 3*sizeof(double)));
        t.Serialise(rtn);
        *rtn += yaw;
        *rtn += pitch;
        *rtn += roll;
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleDepth(tN2kMsg& msg)
{
    unsigned char SID;
    double depth, offset, range;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kWaterDepth(msg, SID, depth, offset, range)) {
        DummyTimestamp t(msg.MsgTime);
        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 3*sizeof(double)));
        t.Serialise(rtn);
        *rtn += depth;
        *rtn += offset;
        *rtn += range;
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleCOG(tN2kMsg& msg)
{
    unsigned char SID;
    tN2kHeadingReference ref;
    double  cog, sog;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kCOGSOGRapid(msg, SID, ref, cog, sog)) {
        if (ref == N2khr_true) {
            DummyTimestamp t(msg.MsgTime);
            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 2*sizeof(double)));
            t.Serialise(rtn);
            *rtn += cog;
            *rtn += sog;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleGNSS(tN2kMsg& msg)
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
        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 2*sizeof(uint16_t) + 8*sizeof(double) + 5));
        t.Serialise(rtn); // Put in the standard timestamp, as well as the in-message one.
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

std::shared_ptr<Serialisable> HandleEnvironment(tN2kMsg& msg)
{
    unsigned char SID;
    tN2kTempSource      t_source;
    tN2kHumiditySource  h_source;
    double              temp, humidity, pressure;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kEnvironmentalParameters(msg, SID, t_source, temp, h_source, humidity, pressure)) {
        DummyTimestamp t(msg.MsgTime);
        rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 3*sizeof(double) + 2));
        t.Serialise(rtn);
        *rtn += (uint8_t)t_source;
        *rtn += temp;
        *rtn += (uint8_t)h_source;
        *rtn += humidity;
        *rtn += pressure;
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleTemperature(tN2kMsg& msg)
{
    unsigned char   SID;
    unsigned char   temp_instance;
    tN2kTempSource  t_source;
    double          temp, set_temp;
    std::shared_ptr<Serialisable> rtn;

    if (ParseN2kTemperature(msg, SID, temp_instance, t_source, temp, set_temp)) {
        if (t_source == N2kts_SeaTemperature || t_source == N2kts_OutsideTemperature) {
            DummyTimestamp t(msg.MsgTime);
            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 1 + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)t_source;
            *rtn += temp;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleHumidity(tN2kMsg& msg)
{
    unsigned char       SID;
    unsigned char       humidity_instance;
    tN2kHumiditySource  h_source;
    double              humidity;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kHumidity(msg, SID, humidity_instance, h_source, humidity)) {
        if (h_source == N2khs_OutsideHumidity) {
            DummyTimestamp t(msg.MsgTime);
            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 1 + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)h_source;
            *rtn += humidity;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandlePressure(tN2kMsg& msg)
{
    unsigned char       SID;
    unsigned char       pressure_instance;
    tN2kPressureSource  p_source;
    double              pressure;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kPressure(msg, SID, pressure_instance, p_source, pressure)) {
        if (p_source == N2kps_Atmospheric) {
            DummyTimestamp t(msg.MsgTime);
            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 1 + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)p_source;
            *rtn += pressure;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> HandleExtTemperature(tN2kMsg& msg)
{
    unsigned char   SID;
    unsigned char   temp_instance;
    tN2kTempSource  t_source;
    double          temp, set_temp;
    std::shared_ptr<Serialisable> rtn;
    
    if (ParseN2kTemperatureExt(msg, SID, temp_instance, t_source, temp, set_temp)) {
        if (t_source == N2kts_SeaTemperature || t_source == N2kts_OutsideTemperature) {
            DummyTimestamp t(msg.MsgTime);
            rtn = std::shared_ptr<Serialisable>(new Serialisable(t.SerialisationSize() + 1 + sizeof(double)));
            t.Serialise(rtn);
            *rtn += (uint8_t)t_source;
            *rtn += temp;
        }
    }
    return rtn;
}

std::shared_ptr<Serialisable> SerialisableFactory::Convert(tN2kMsg& msg, PayloadID& payload_id)
{
    std::shared_ptr<Serialisable> rtn;
    payload_id = Pkt_Version;   // Invalid for normal users (can only be added by serialisation code)
    
    switch (msg.PGN) {
        case 126992UL:  rtn = HandleSystemTime(msg);        payload_id = Pkt_SystemTime;    break;
        case 127257UL:  rtn = HandleAttitude(msg);          payload_id = Pkt_Attitude;      break;
        case 128267UL:  rtn = HandleDepth(msg);             payload_id = Pkt_Depth;         break;
        case 129026UL:  rtn = HandleCOG(msg);               payload_id = Pkt_COG;           break;
        case 129029UL:  rtn = HandleGNSS(msg);              payload_id = Pkt_GNSS;          break;
        case 130311UL:  rtn = HandleEnvironment(msg);       payload_id = Pkt_Environment;   break;
        case 130312UL:  rtn = HandleTemperature(msg);       payload_id = Pkt_Temperature;   break;
        case 130313UL:  rtn = HandleHumidity(msg);          payload_id = Pkt_Humidity;      break;
        case 130314UL:  rtn = HandlePressure(msg);          payload_id = Pkt_Pressure;      break;
        case 130316UL:  rtn = HandleExtTemperature(msg);    payload_id = Pkt_Temperature;   break;
        default:
            break;
    }
    return rtn;
}

std::shared_ptr<Serialisable> SerialisableFactory::Convert(uint32_t elapsed_time, std::string& nmea_string, PayloadID& payload_id)
{
    std::shared_ptr<Serialisable> rtn(new Serialisable(nmea_string.length() + 4));
    *rtn += elapsed_time;
    *rtn += nmea_string.c_str();
    
    payload_id = Pkt_NMEAString;
    return rtn;
}
