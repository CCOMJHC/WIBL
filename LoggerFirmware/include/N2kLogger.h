/*!\file N2kLogger.h
 * \brief Main code for a NMEA2000 message handler with time, position, depth logging and timestamping
 *
 * This code is designed to form a simple data logger for NMEA2000, which keeps track of time and stores
 * position, depth, and some environmental information into the SD card attached to the board.  The goal
 * here is to store sufficient information to make this a useful crowd-sourced bathymetry logging engine,
 * but at the cheapest possible price.
 *
 * Copyright (c) 2019, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#ifndef __N2K_LOGGER_H__
#define __N2K_LOGGER_H__

#include <set>
#include <stdint.h>
#include <Arduino.h>
#include <NMEA2000.h>
#include "serialisation.h"
#include "LogManager.h"

namespace nmea {
namespace N2000 {

/// \class Timestamp
/// \brief Generate a timestamp for an instant based on elapsed time to last known time
///
/// This class attempts to generate plausible timestamps for any given instant based on
/// the elapsed time counter (usually in milliseconds) and a known time instant.  This
/// isn't the most elegant way to do this, but it works good enough for the purpose.

class Timestamp {
public:
    /// \brief Default constructor with invalid setup
    Timestamp(void);
    
    /// \brief Provide a new observation of a known (UTC) time
    void Update(uint16_t date, double timestamp);
    /// \brief Provide a new observation of a known (UTC) time and elapsed time
    void Update(uint16_t date, double timestamp, unsigned long ms_counter);

    /// \brief Indicate whether a good timestamp has been generated yet
    inline bool IsValid(void) const { return m_lastDatumTime >= 0.0; }
    
    /// \struct TimeDatum
    /// \brief POD for a time instant
    ///
    /// This provides a data object that represents a single point in time, with real-time interpolated
    /// from the elapsed time at construction based on the real-time reference and elapsed time
    /// offset in the supporting \a Timestamp object.
    
    struct TimeDatum {
    public:
        /// \brief Constructor, generating an timestamp based on construction time
        TimeDatum(void) : datestamp(0), timestamp(-1.0), m_elapsed(millis()) {}
      
        uint16_t  datestamp; ///< Date in days since 1970-01-01
        double    timestamp; ///< Time in seconds since midnight

        /// \brief Test whether timestamp is valid
        bool IsValid(void) const { return timestamp >= 0.0; }
        
        /// \brief Serialise the datum into a given target
        void Serialise(Serialisable& target) const;
        
        /// \brief Give the size of the object once serialised
        uint32_t SerialisationSize(void) const
        {
            return sizeof(uint16_t)+sizeof(double) + sizeof(uint32_t);
        }
        
        /// \brief Provide something that's a printable version
        String printable(void) const;
        
        /// \brief Provide the raw observation (rarely required)
        uint32_t RawElapsed(void) const { return (uint32_t)m_elapsed; }
        
    private:
        unsigned long m_elapsed; ///< The millisecond counter at observation time
    };

    /// \brief Generate a timestamp for the current time, if possible.
    TimeDatum Now(void);
    
    /// \brief Generate a string-printable representation of the information
    String printable(void) const;

    unsigned long DatumElapsedTime(void) const { return m_elapsedTimeAtDatum; }

private:
    uint16_t      m_lastDatumDate;      ///< Days since 1970-01-01 at last known datum
    double        m_lastDatumTime;      ///< Time in seconds since midnight at last known datum
    unsigned long m_elapsedTimeAtDatum; ///< Internal clock elapsed time at last known datum
};

/// \class Logger
/// \brief Encapsulate N2K message handler
///
/// This provides a tNMEA2000::tMsgHandler sub-class that manages the messages required for the CSB
/// data logger, and writes the translated messages to SD card for later capture.  The code is heavily
/// based on the example N2K->0183 converter that comes as an example with the NMEA2000 library.

class Logger : public tNMEA2000::tMsgHandler {
public:
    /// \brief Default constructor, given the NMEA2000 object that's doing the data capture
    Logger(tNMEA2000 *source, logger::Manager *output);
    
    /// \brief Default destructor
    ~Logger(void);
    
    /// \brief Message handler for the tNMEA2000::tMsgHandler interface
    void HandleMsg(const tN2kMsg &N2kMsg);

    /// \brief Update the time reference being used based on external source
    void UpdateTimeReference(uint16_t days_since_epoch, double seconds_in_day)
    {
        m_timeReference.Update(days_since_epoch, seconds_in_day);
        m_externalTime = true;
    }
    unsigned long TimeReferencedElapsed(void) const { return m_timeReference.DatumElapsedTime(); }
    
    /// \brief Generate a software version string, as required by NMEA2000 library
    static String SoftwareVersion(void);
    /// \brief Report software version information for the NMEA2000 logger
    static void SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch);

    /// \brief Set verbose logging state
    void SetVerbose(bool verb) { m_verbose = verb; }
    
private:
    bool            m_verbose;          ///< Flag for verbose debug output
    bool            m_externalTime;     ///< Flag: set if time is being handled elsewhere
    Timestamp       m_timeReference;    ///< Time reference information for timestamping records
    logger::Manager *m_logManager;      ///< Handler for output log files
    std::set<int>   m_pgnList;          ///< List of PGNs to write to output (binary)
    bool            m_writeAll;         ///< Flag: write all unknown PGNs to binary output if set
    
    /// \brief Translate and serialise the real-time information from GNSS (or atomic clock)
    void HandleSystemTime(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise the platform attitude information
    void HandleAttitude(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise the observed depth information
    void HandleDepth(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise the course and speed over ground information
    void HandleCOG(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise the GNSS observation information
    void HandleGNSS(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise the temperature, humidity, and pressure information
    void HandleEnvironment(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise a temperature observation
    void HandleTemperature(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise an external temperature observation
    void HandleExtTemperature(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise a humidity observation
    void HandleHumidity(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Translate and serialise a pressure observation
    void HandlePressure(Timestamp::TimeDatum const& t, tN2kMsg const& msg);
    /// \brief Write the binary representation of an auxiliary packet
    void HandleBinary(Timestamp::TimeDatum const& t, tN2kMsg const& msg);

    /// \brief Get the list of PGNs that we need to write in binary to output
    void retrievePGNlist(void);
    /// \brief Checked whether a given PGN is on the list to write
    bool writing_pgn_bin(unsigned long pgn);
};

}
}

#endif
