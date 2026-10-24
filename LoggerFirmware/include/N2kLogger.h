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
#include "timing.h"
#include "LogManager.h"

namespace nmea {
namespace N2000 {

/// \class N2KTimeSource
/// \brief Time information from NMEA2000 messages for timestamping
class N2KTimeSource : public timing::BaseTimeSource {
public:
    N2KTimeSource(void) : m_fromSystemTime(false) {};

    bool assigntime(uint64_t const elapsed, timing::TimePoint& now);

    void setReferenceUnconditional(uint64_t const elapsed, uint16_t const days, double const seconds);
    void setReferenceGNSS(uint64_t const elapsed, uint16_t const days, double const seconds);

    String printable(void) const { return m_reference.printable(); }
    bool isValid(void) const { return m_reference.isValid(); }

private:
    timing::TimePoint   m_reference;
    bool                m_fromSystemTime;
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
    Logger(tNMEA2000 *source, logger::Manager *output, N2KTimeSource *timeref);
    
    /// \brief Default destructor
    ~Logger(void);
    
    /// \brief Message handler for the tNMEA2000::tMsgHandler interface
    void HandleMsg(const tN2kMsg &N2kMsg);
    
    /// \brief Generate a software version string, as required by NMEA2000 library
    static String SoftwareVersion(void);
    /// \brief Report software version information for the NMEA2000 logger
    static void SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch);

    /// \brief Set verbose logging state
    void SetVerbose(bool verb) { m_verbose = verb; }
    
private:
    bool            m_verbose;          ///< Flag for verbose debug output
    N2KTimeSource   *m_timeReference;   ///< Time reference information for timestamping records
    logger::Manager *m_logManager;      ///< Handler for output log files
    std::set<int>   m_pgnList;          ///< List of PGNs to write to output (binary)
    bool            m_writeAll;         ///< Flag: write all unknown PGNs to binary output if set
    
    /// \brief Translate and serialise the real-time information from GNSS (or atomic clock)
    void HandleSystemTime(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise the platform attitude information
    void HandleAttitude(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise the observed depth information
    void HandleDepth(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise the course and speed over ground information
    void HandleCOG(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise the GNSS observation information
    void HandleGNSS(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise the temperature, humidity, and pressure information
    void HandleEnvironment(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise a temperature observation
    void HandleTemperature(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise an external temperature observation
    void HandleExtTemperature(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise a humidity observation
    void HandleHumidity(uint64_t const t, tN2kMsg const& msg);
    /// \brief Translate and serialise a pressure observation
    void HandlePressure(uint64_t const t, tN2kMsg const& msg);
    /// \brief Write the binary representation of an auxiliary packet
    void HandleBinary(uint64_t const t, tN2kMsg const& msg);

    /// \brief Get the list of PGNs that we need to write in binary to output
    void retrievePGNlist(void);
    /// \brief Checked whether a given PGN is on the list to write
    bool writing_pgn_bin(unsigned long pgn);
};

}
}

#endif
