/*!\file N0183Logger.h
 * \brief Main code for a NMEA0183 message handler with time, position, depth logging and timestamping
 *
 * This code is designed to form a simple data logger for NMEA0183, which keeps track of time and stores
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

#ifndef __N0183_LOGGER_H__
#define __N0183_LOGGER_H__

#include <set>
#include "LogManager.h"
#include "IncrementalBuffer.h"
#include "Configuration.h"

namespace nmea {
namespace N0183 {

/// \class Sentence
/// \brief Assemble a NMEA0183 sentence from character input on serial line
///
/// A standard NMEA0183 sentence begins with "$" and ends with [CR][LF], including a checksum
/// at the end.  This structure allows this information to be accumulated as the characters arrive on the
/// input serial stream (by definition RS-422), and buffers the sentences until the user can read them.  A
/// timestamp is generated for the first "$" in each string, and stored with the string.

class Sentence : public logger::IncBuffer {
public:
    static const int MAX_SENTENCE_LENGTH = 128; ///< Maximum is probably order 100 characters; this is safe
    
    /// \brief Default constructor, just resetting the buffer insertion point
    Sentence(void)
    {
        Reset();
    }
        
    /// \brief Reset the current sentence, going back to zero length
    ///
    /// This resets the buffer to zero contents, invalidates the timestamp, and sets the insertion
    /// point back to zero, effectively removing the old data without having to reconstruct.
    void Reset(void)
    {
        logger::IncBuffer::Reset();
        m_timestamp = 0UL;
    }
        
    /// \brief Get the stored timestamp for the sentence
    unsigned long Timestamp(void) const { return m_timestamp; }
    /// \brief Set the stored timestamp from a seconds count
    void Timestamp(unsigned long const t) { m_timestamp = t; }
    
    /// \brief Deteremine whether the sentence is a valid NMEA sentence or not
    bool Valid(void) const;
    
    /// \brief Provide the recognition token from the start of the sentence
    String Token(void) const;

    /// \brief Provide the NMEA0183 message ID from the start of the sentence
    String MessageID(void) const;
    
private:
    unsigned long   m_timestamp;    ///< Timestamp associated with the "$" that started the sentence
};

/// \class MessageAssembler
/// \brief Implement a state-machine model of accumulating NMEA0183 messages
///
/// This class runs the active part of the NMEA0183 message recognition protocol, keeping track of the
/// state of the channel (searching, in-sentence, etc.) so that it can apply timestamps where required,
/// detect partial messages, early message termination, etc.

class MessageAssembler {
public:
    /// \brief Default constructor
    MessageAssembler(void);
    /// \brief Default destructor
    ~MessageAssembler(void);
    /// \brief Set the channel indicator for reporting
    inline void SetChannel(const int channel) { m_channel = channel; }
    /// \brief Set the log manager to use for console logging
    inline void SetLogManager(logger::Manager *manager) { m_logManager = manager; }
    /// \brief Add a new character to the current sentence (potentially completing it)
    void AddCharacter(const char c);
    /// \brief Set debugging state for message assembly
    inline void SetDebugging(const bool state) { m_debugAssembly = state; }
    /// \brief Copy out the next available sentence from the ring buffer
    Sentence const *NextSentence(void);
    
private:
    /// \enum State
    /// \brief States in the FSM used to assemble sentences from raw characters
    enum State {
        STATE_SEARCHING,    ///< Looking for a new sentence start character
        STATE_CAPTURING     ///< In the middle of a sentence, looking for the end character(s)
    };

    class ErrorCount {
    public:
        ErrorCount(void);
        enum ErrorType {
            NON_START = 0,
            RX_INVERSION,
            RESTART,
            OVERLONG,
            MAX_ERRORS
        };
        void Note(ErrorType event);
        void ReportCounts(logger::Manager *manager, int channel);
    
    private:
        unsigned int m_counts[ErrorCount::MAX_ERRORS];
        unsigned long m_nextReport;
        const unsigned long report_interval = 5000;
        bool reportable(void);
        bool timeout(void);
        void reset(void);
    };

    static const int RingBufferLength = 10; ///< Maximum number of sentences we'll attempt to buffer
    logger::Manager *m_logManager;          ///< Log manager to use for console logging, if required
    ErrorCount m_errors;                    ///< Object to count errors during assembly (for later report)
    State     m_state;                      ///< Current state of the message being assembled
    Sentence  m_current;                    ///< Sentence currently being assembled
    int       m_readPoint;                  ///< Ring buffer read position
    int       m_writePoint;                 ///< Ring buffer write position
    Sentence  m_buffer[RingBufferLength];   ///< Buffer for sentences being held for use
    int       m_channel;                    ///< Channel indicator for messages
    bool      m_debugAssembly;              ///< Flag for debug message construction
    int       m_badStartCount;              ///< Count of the number of bad start characters since last inversion reset
    int       m_lastInvertResetTime;        ///< Elapsed time when we last tried inverting the input to get good data
    bool      m_inverted;                   ///< Indicator that RX inversion has been attempted
};

/// \class Logger
/// \brief Handle NMEA0183 data on inputs, and transpose full sentences to log file
///
/// This class encapsulates the requirements for a NMEA0183 dual-channel logger, taking any valid NMEA0183 serial
/// strings on hardware serial ports Serial1 and Serial2 and logging them into the output SD card file stream passed
/// on construction.  Timestamps are added appropriately for the first "$" that starts each sentence.
///

class Logger {
public:
    /// \brief Default constructor    
    Logger(logger::Manager *output);
    /// \brief Default destructor
    ~Logger(void);
    
    /// \brief Process any characters that have arrived
    void ProcessMessages(void);

    /// \brief Generate a version string for the logger
    static String SoftwareVersion(void);
    /// \brief Report the version information for the NMEA0183 logger
    static void SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch);

    /// \brief Set debugging status
    void SetVerbose(bool verbose);
    
    /// \brief Configure the input inversion bit on the serial ports
    void SetRxInvert(uint32_t port, bool invert);
    
private:
    static const int ChannelCount = 2;            ///< Number of channels that we manage
    bool                m_verbose;                ///< Verbose status for the logger
    logger::Manager    *m_logManager;             ///< Handler for log files on SD card
    MessageAssembler    m_channel[ChannelCount];  ///< Message handler for two channels
    std::set<String>    m_filter;                 ///< Set of NMEA0183 IDs to accept

    /// \brief Find the configured baud rate for the given channel
    uint32_t retrieveBaudRate(logger::Config::ConfigParam channel);
    /// \brief Pull the configured specification of which NMEA messages are allowed to be logged back into memory
    void retrieveIDFilter(void);
    /// \brief Determine whether the given sentence should be logged
    bool filterMessage(Sentence const *s);
};

}
}

#endif
