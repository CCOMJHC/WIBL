/*!\file N0183Logger.cpp
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

#include "Arduino.h"
#include <string>
#include <cstring>
#include "N0183Logger.h"
#include "Configuration.h"
#include "NVMFile.h"
#include "DataMetrics.h"

namespace nmea {
namespace N0183 {

const int SoftwareVersionMajor = 1; ///< Software major version for the logger
const int SoftwareVersionMinor = 2; ///< Software minor version for the logger
const int SoftwareVersionPatch = 0; ///< Software patch version for the logger

bool N1KTimeSource::assigntime(uint64_t const elapsed, timing::TimePoint& now)
{
    if (!isValid()) {
        return false;
    }
    now.elapsed = elapsed;
    uint64_t advance = elapsed - m_reference.elapsed;
    // If the current time is more than fice seconds from the reference, we prefer to
    // not give an answer than give a potentially bad answer.
    if (advance > 5000000) {
        return false;
    }
    now.second = m_reference.second + (m_reference.microsecond + advance) / 1000000UL;
    now.microsecond = (m_reference.microsecond + advance) % 1000000UL;
    return true;
}

// \brief Set the reference time for time-stamping based on the ZDA or RMC sentence
///
/// This checks a given sentence for ZDA or RMC contents, and if present parses out the date and
/// time and converts them into a reference time that can be used to associate a UTC timestamp with
/// an elapsed time count.  Note that the code here assumes that the NMEA0183 sentence is valid,
/// and makes no further checks (e.g., for checksum validity).  Badly formed sentences, and anything
/// not ZDA or RMC are ignored.
///
/// \param elapsed  Elapsed time counter (64-bit monotonic count since boot) from Timestamper object
/// \param message  Pointer to the NMEA0183 sentence to parse
/// \returns N/A

bool N1KTimeSource::setReference(uint64_t const elapsed, const Sentence *message)
{
    String id(message->MessageID());
    time_t seconds = (time_t)0; // Essentially "no value" since we can't get new data at 1970-01-01!
    uint32_t microseconds = 0UL;
    if (id == "ZDA") {
        parse_zda(message, seconds, microseconds);
    } else if (id == "RMC") {
        parse_rmc(message, seconds, microseconds);
    } else {
        // The message, whatever it is, has no time information that's useful for us.
        return false;
    }
    // The parser code returns early without modifying the seconds/microseconds output
    // if there's a validation failure from the NMEA sentences.  Detecting a non-zero
    // seconds count (even if microseconds is zero) demonstrates that parsing worked.
    if (seconds > 0) {
        m_reference.second = seconds;
        m_reference.microsecond = microseconds;
    }
    return true;
}

bool parse_uint(const char* begin, const char* end, unsigned int& value)
{
    if (begin == end) return false;

    value = 0;
    while (begin < end) {
        if (*begin < '0' || *begin > '9') return false;
        value = value * 10 + static_cast<unsigned int>(*begin - '0');
        ++begin;
    }
    return true;
}

bool is_leap_year(unsigned int year)
{
    return year % 4 == 0 && (year % 100 != 0 || year % 400 == 0);
}

int64_t days_from_civil(int year, unsigned int month, unsigned int day)
{
    year -= month <= 2;
    const int era = (year >= 0 ? year : year - 399) / 400;
    const unsigned int year_of_era = static_cast<unsigned int>(year - era * 400);
    const unsigned int month_prime = month > 2 ? month - 3 : month + 9;
    const unsigned int day_of_year = (153 * month_prime + 2) / 5 + day - 1;
    const unsigned int day_of_era =
        year_of_era * 365 + year_of_era / 4 - year_of_era / 100 + day_of_year;
    return static_cast<int64_t>(era) * 146097 + day_of_era - 719468;
}

bool parse_time(const char* begin, const char* end, unsigned int& hour,
                unsigned int& minute, unsigned int& second, uint32_t& microseconds)
{
    const char* whole_end = begin;
    while (whole_end < end && *whole_end != '.') ++whole_end;
    if (whole_end - begin != 6) return false;

    if (!parse_uint(begin, begin + 2, hour) ||
        !parse_uint(begin + 2, begin + 4, minute) ||
        !parse_uint(begin + 4, whole_end, second) ||
        hour > 23 || minute > 59 || second > 59) {
        return false;
    }

    microseconds = 0;
    if (whole_end < end) {
        const char* fraction = whole_end + 1;
        if (fraction == end) return false;

        unsigned int digits = 0;
        while (fraction < end) {
            if (*fraction < '0' || *fraction > '9') return false;
            if (digits < 6) {
                microseconds = microseconds * 10 +
                    static_cast<uint32_t>(*fraction - '0');
            }
            ++digits;
            ++fraction;
        }
        while (digits < 6) {
            microseconds *= 10;
            ++digits;
        }
    }
    return true;
}

bool date_to_epoch_seconds(unsigned int year, unsigned int month, unsigned int day,
                           unsigned int hour, unsigned int minute, unsigned int second,
                           time_t& epoch_seconds)
{
    static const unsigned int days_per_month[] = {31, 28, 31, 30, 31, 30,
                                                   31, 31, 30, 31, 30, 31};
    if (year == 0 || month < 1 || month > 12) return false;

    unsigned int max_day = days_per_month[month - 1];
    if (month == 2 && is_leap_year(year)) ++max_day;
    if (day < 1 || day > max_day) return false;

    const int64_t epoch_days = days_from_civil(static_cast<int>(year), month, day);
    const int64_t total_seconds = epoch_days * 86400 +
        static_cast<int64_t>(hour) * 3600 + minute * 60 + second;
    epoch_seconds = static_cast<time_t>(total_seconds);
    return true;
}

void N1KTimeSource::parse_zda(const Sentence *message, time_t& seconds, uint32_t& microseconds)
{
    const char* const contents = message->Contents();
    const char* time_start = strchr(contents, ',');
    if (time_start == nullptr) return;
    ++time_start;

    const char* time_end = strchr(time_start, ',');
    if (time_end == nullptr) return;
    const char* day_start = time_end + 1;
    const char* day_end = strchr(day_start, ',');
    if (day_end == nullptr) return;
    const char* month_start = day_end + 1;
    const char* month_end = strchr(month_start, ',');
    if (month_end == nullptr) return;
    const char* year_start = month_end + 1;
    const char* year_end = strchr(year_start, '*');
    if (year_end == nullptr) return;
    if (day_end - day_start != 2 || month_end - month_start != 2 ||
        year_end - year_start != 4) {
        return;
    }

    unsigned int hour, minute, second;
    uint32_t parsed_microseconds = 0;
    if (!parse_time(time_start, time_end, hour, minute, second, parsed_microseconds)) return;

    unsigned int day, month, year;
    if (!parse_uint(day_start, day_end, day) ||
        !parse_uint(month_start, month_end, month) ||
        !parse_uint(year_start, year_end, year)) {
        return;
    }
    if (!date_to_epoch_seconds(year, month, day, hour, minute, second, seconds)) return;
    microseconds = parsed_microseconds;
}

void N1KTimeSource::parse_rmc(const Sentence *message, time_t& seconds, uint32_t& microseconds)
{
    const char* const contents = message->Contents();
    const char* time_start = strchr(contents, ',');
    if (time_start == nullptr) return;
    ++time_start;

    const char* time_end = strchr(time_start, ',');
    if (time_end == nullptr) return;

    const char* date_start = time_end;
    for (int field = 0; field < 7; ++field) {
        date_start = strchr(date_start + 1, ',');
        if (date_start == nullptr) return;
    }
    ++date_start;

    const char* date_end = strchr(date_start, ',');
    const char* checksum = strchr(date_start, '*');
    if (date_end == nullptr || (checksum != nullptr && checksum < date_end)) {
        date_end = checksum;
    }
    if (date_end == nullptr || time_end - time_start < 6 || date_end - date_start != 6) {
        return;
    }

    unsigned int hour, minute, second;
    uint32_t parsed_microseconds = 0;
    if (!parse_time(time_start, time_end, hour, minute, second, parsed_microseconds)) return;

    unsigned int day, month, short_year;
    if (!parse_uint(date_start, date_start + 2, day) ||
        !parse_uint(date_start + 2, date_start + 4, month) ||
        !parse_uint(date_start + 4, date_end, short_year)) {
        return;
    }

    const unsigned int year = short_year >= 80 ? 1900 + short_year : 2000 + short_year;
    if (!date_to_epoch_seconds(year, month, day, hour, minute, second, seconds)) return;
    microseconds = parsed_microseconds;
}

/// Validate the sentence, making sure that it meets the requirements to be a NMEA0183 message.  For
/// this, it has to contain only printable characters, it has to start with a "$", and end with a valid checksum
/// byte (as two hex characters).  If any of these conditions are violated, the sentence is invalid.
///
/// \return True if the sentence if valid, otherwise False.

bool Sentence::Valid(void) const
{
    int checksum = 0;
    
    int i = 1;
    while (i < InsertPoint() && BufferChar(i) != '*') {
        if (!std::isprint(BufferChar(i)))
            // Not printable, so something's wrong
            return false;
        checksum ^= BufferChar(i++);
    }
    if (i == InsertPoint()) {
        // Ran out of string, so there's no checksum to compare against!
        return false;
    }
    char buffer[4];
    sprintf(buffer, "*%02X", checksum);
    buffer[3] = '\0';
    if (strncmp(Contents() + i, buffer, 4) == 0)
        return true;
    else
        return false;
}

/// Extract from the sentence the recognition token from the start of the NMEA sentence, which includes both
/// the talker identifier, and the sentence name string for a total of five characters.
///
/// \return string of the recognition characters.

String Sentence::Token(void) const
{
    String s = String(Contents()).substring(1,6);
    return s;
}

/// Extract from the sentence just the message ID (rather than including the
/// talker identifier as with Token()).
///
/// \return Three-letter message ID

String Sentence::MessageID(void) const
{
    String s = String(Contents()).substring(3,6);
    return s;
}

MessageAssembler::ErrorCount::ErrorCount(void)
{
    for (auto n = 0; n < ErrorCount::MAX_ERRORS; ++n) {
        m_counts[n] = 0;
    }
    m_nextReport = millis() + report_interval;
}

bool MessageAssembler::ErrorCount::reportable(void)
{
    unsigned int total = 0;
    for (auto n = 0; n < ErrorCount::MAX_ERRORS; ++n) {
        total += m_counts[n];
    }
    return total > 0;
}

bool MessageAssembler::ErrorCount::timeout(void)
{
    unsigned long now = millis();
    if (now < m_nextReport) {
        return false;
    }
    m_nextReport = now + report_interval;
    return true;
}

void MessageAssembler::ErrorCount::reset(void)
{
    for (auto n = 0; n < ErrorCount::MAX_ERRORS; ++n) {
        m_counts[n] = 0;
    }
}

void MessageAssembler::ErrorCount::Note(ErrorType event)
{
    ++m_counts[event];
}

void MessageAssembler::ErrorCount::ReportCounts(logger::Manager *manager, int channel)
{
    if (!timeout() || !reportable()) {
        return;
    }

    char *buf = new char[512];

    snprintf(buf, 512, "ERR: NMEA0183 ch %d (%d ms/report):", channel, report_interval);
    manager->Syslog(buf);
    snprintf(buf, 512, "  %d non-start characters while looking for start.", m_counts[0]);
    manager->Syslog(buf);
    snprintf(buf, 512, "  %d RX inversion calls.", m_counts[1]);
    manager->Syslog(buf);
    snprintf(buf, 512, "  %d sentence restarts during capture.", m_counts[2]);
    manager->Syslog(buf);
    snprintf(buf, 512, "  %d overlong sentences.", m_counts[3]);
    manager->Syslog(buf);

    delete [] buf;

    reset();
}

/// Start the message assembler in the "searching" state, with a blank sentence and empty FIFO.

MessageAssembler::MessageAssembler(void)
: m_logManager(nullptr), m_state(STATE_SEARCHING), m_readPoint(0), m_writePoint(0), m_channel(-1),
  m_debugAssembly(false), m_badStartCount(0), m_lastInvertResetTime(millis()), m_inverted(false)
{
}

MessageAssembler::~MessageAssembler(void)
{
}

/// Take the next character from the input stream, and add to the current sentence, keeping track of the
/// message state (e.g., waiting for a "$", looking for an end-character sequence, etc.  If the sentence comes
/// to an end with the current character (meaning that it has to be a newline (\0x0A), then the sentence is
/// moved into the FIFO, and a new sentence is started.
///
/// \param in   Character being added from the input stream

void MessageAssembler::AddCharacter(const char in)
{
    String message;
    bool report = false;
    
    switch(m_state) {
        case STATE_SEARCHING:
            if (in == '$') {
                // This is the start of a string, so get the timestamp, and stash
                m_current.Reset();
                m_current.Timestamp(m_logManager->GetElapsedTime());
                m_current.AddCharacter(in);
                m_state = STATE_CAPTURING;
                if (m_debugAssembly) {
                    Serial.println(String("DEBUG: sentence started with timestamp ") +
                                   m_current.Timestamp() + " on channel " + m_channel +
                                   "; changing to CAPTURING.");
                }
            } else {
                if (m_debugAssembly) {
                    message = "ERR: non-start character ";
                    if (std::isprint(in)) {
                        message += String("'") + in + "'";
                    } else {
                        message += "0x" + String(in, HEX);
                    }
                    message += " while searching for NMEA string (channel " + String(m_channel) + ").";
                    Serial.println(message);
                }
                m_errors.Note(ErrorCount::NON_START);

                if ((in & 0x80) != 0) {
                    // Top bit should never be set in serial ASCII, so that's either a noise
                    // hit, or we might have a polarity problem.  We count these for now,
                    // so that we can try to invert later.
                    m_badStartCount++;
                }
                auto elapsed_time = millis() - m_lastInvertResetTime;
                if (elapsed_time == 0) ++elapsed_time;
                if ((m_badStartCount * 1000 / elapsed_time) > 10) {
                    // If we're seeing more than 10 bad starts/second, it's likely that we've
                    // got an inversion of the inputs, so we attempt to fix that.
                    m_lastInvertResetTime = millis();
                    m_badStartCount = 0;
                    if (!m_inverted) {
                        if (m_channel == 1) {
                            Serial1.setRxInvert(true);
                        } else if (m_channel == 2) {
                            Serial2.setRxInvert(true);
                        }
                        message = "INFO: setting rx input inversion on channel "
                                    + String(m_channel) + " due to bad start characters.";
                        Serial.println(message);
                        m_errors.Note(ErrorCount::RX_INVERSION);
                        m_inverted = true;
                    }
                }
            }
            break;
        case STATE_CAPTURING:
            switch(in) {
                case '\n':
                    // The end of the current sentence, so we convert the current sentence
                    // onto the ring buffer.  Note that we don't store the carriage return.
                    m_buffer[m_writePoint] = m_current;
                    m_writePoint = (m_writePoint + 1) % RingBufferLength;
                    if (m_debugAssembly) {
                        Serial.println(String("DEBUG: LF on channel ") + m_channel +
                                              " to complete sentence; moved to FIFO");
                    }
                    m_state = STATE_SEARCHING;
                    if (m_debugAssembly) {
                        Serial.println(String("DEBUG: changing to SEARCHING on channel ") +
                                       m_channel + ".");
                    }
                    break;
                case '\r':
                    // The NMEA sentence should complete with CR+LF, but we want to ignore the CR so
                    // that sentence termination is recognised by the LF, but we don't have to deal with
                    // the extra CR in the sentence!
                    break;
                case '$':
                    // The start of a new sentence, which is odd ...
                    m_current.Reset();
                    m_current.Timestamp(m_logManager->GetElapsedTime());
                    m_current.AddCharacter(in);
                    message = "WARN: sentence restarted before end of previous one?! (channel " + String(m_channel) + ").";
                    Serial.println(message);
                    if (m_debugAssembly) {
                        Serial.println(String("DEBUG: new sentence started with timestamp ") +
                                       m_current.Timestamp() + " as reset on channel " +
                                       m_channel + ".");
                    }
                    m_errors.Note(ErrorCount::RESTART);
                    break;
                default:
                    // The next character of the current sentence
                    if (!m_current.AddCharacter(in)) {
                        // Ran out of buffer space, so return to searching.  Note that we don't need to
                        // reset the current buffer, because the next sentence starting will do so.
                        m_state = STATE_SEARCHING;
                        message = "WARN: over-long sentence detected, and ignored (channel " + String(m_channel) + ").";
                        Serial.println(message);
                        if (m_debugAssembly) {
                            Serial.println(String("DEBUG: reset state to SEARCHING on channel ") +
                                           m_channel + " after over-long sentence.");
                        }
                        m_errors.Note(ErrorCount::OVERLONG);
                    }
                    break;
            }
            break;
        default:
            const char *msg = "ERR: unknown state in message assembly! Resetting to SEARCHING.";
            Serial.println(msg);
            if (m_logManager != nullptr) {
                m_logManager->Syslog(msg);
            }
            m_state = STATE_SEARCHING;
            break;
    }
    if (m_logManager != nullptr) {
        m_errors.ReportCounts(m_logManager, m_channel);
    }
}

/// Pull the next sentence out of the ring buffer (as a pointer to the location of the message),
/// and update the buffer.  A new sentence only exists if there's data; if there's nothing left,
/// a null pointer is returned.
///
/// \return Pointer to the next sentence, or nullptr

Sentence const *MessageAssembler::NextSentence(void)
{
    if (m_readPoint == m_writePoint) return nullptr;
    
    Sentence const *rtn = m_buffer + m_readPoint;
    m_readPoint = (m_readPoint + 1) % RingBufferLength;

    return rtn;
}
                                       
#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
#if defined(PROTOTYPE_LOGGER)
const int rx1_pin = 13;
const int tx1_pin = 32;
const int rx2_pin = 14;
const int tx2_pin = 33;
#elif defined(BUILD_NEMO30)
const int rx1_pin = 27; ///< UART port 1 receive pin number (default for this system, not standard)
const int tx1_pin = 18; ///< UART port 1 transmit pin number (default for this system, not standard)
const int rx2_pin = 33; ///< UART port 2 receive pin number (default for this system, not standard)
const int tx2_pin = 19; ///< UART port 2 transmit pin number (default for this system, not standard)
#else
const int rx1_pin = 34; ///< UART port 1 receive pin
const int tx1_pin = 18; ///< UART port 1 transmit pin
const int rx2_pin = 35; ///< UART port 2 receive pin
const int tx2_pin = 19; ///< UART port 2 transmit pin
#endif
#elif defined(__SAM3X8E__)
// Note that these are the defaults, since there doesn't appear to be a way to adjust on Arduino Due
const int rx1_pin = 19; ///< UART port 1 receive pin
const int tx1_pin = 18; ///< UART port 1 transmit pin
const int rx2_pin = 17; ///< UART port 2 receive pin
const int tx2_pin = 16; ///< UART port 2 transmit pin
#else
#error "No configuration recognised for serial inputs"
#endif

/// Initialise a logger structure that can be used to handle all logging capabilities for NMEA0183 data on
/// hardware channels Serial1 and Serial2.  This accumulates data from the serial channels into NMEA0183 sentences,
/// and then logs them as they are terminated.  Invalid sentences are removed from consideration before being
/// logged, and filtering is applied to the data if required in order to minimise the data that is logged.
///
/// \param output   Reference for the output SD file logger to use

Logger::Logger(logger::Manager *output, N1KTimeSource *timeref)
: m_verbose(false), m_logManager(output), m_timeref(timeref)
{
    m_channel[0].SetChannel(1);
    m_channel[0].SetLogManager(output);
    m_channel[1].SetChannel(2);
    m_channel[1].SetLogManager(output);
    
#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
    int used_tx1_pin = tx1_pin, used_tx2_pin = tx2_pin;
#if defined(BUILD_NEMO30)
    // We have limits on the number of pins that can be used, so the TX pins (which we don't need)
    // are routed to the SPI pins by default on the assumption that the eMMC module will be used
    // instead for storage, and the SPI pins can be safely reused.  Of course, if that isn't the
    // case, we need to switch ...
    bool sdio_in_use = false;
    if (!logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_SDMMC_B, sdio_in_use)) {
        sdio_in_use = false;
    }
    if (!sdio_in_use) {
        // Reassign to eMMC data lines not otherwise being used.
        used_tx1_pin = 14;
        used_tx2_pin = 15;
    }
#endif
    Serial1.begin(retrieveBaudRate(logger::Config::ConfigParam::CONFIG_BAUDRATE_1_S), SERIAL_8N1, rx1_pin, used_tx1_pin);
    Serial2.begin(retrieveBaudRate(logger::Config::ConfigParam::CONFIG_BAUDRATE_2_S), SERIAL_8N1, rx2_pin, used_tx2_pin);
#elif defined(__SAM3X8E__)
    Serial1.begin(retrieveBaudRate(logger::Config::ConfigParam::CONFIG_BAUDRATE_1_S));
    Serial2.begin(retrieveBaudRate(logger::Config::ConfigParam::CONFIG_BAUDRATE_2_S));
#endif

    retrieveIDFilter();
}

/// Retrieve from NVM the baud rate parameters configured for the logger by the user
/// interface.
///
/// \param channel  Indicator of which channel to retrieve (CONFIG_BAUDRATE_1_S, CONFIG_BAUDRATE_2_S)
/// \return Baud rate for the indicated channel

uint32_t Logger::retrieveBaudRate(logger::Config::ConfigParam channel)
{
    String baud_rate_str;
    uint32_t baud_rate;
    logger::LoggerConfig.GetConfigString(channel, baud_rate_str);
    if (baud_rate_str.isEmpty()) {
        baud_rate = 4800;
    } else {
        baud_rate = static_cast<uint32_t>(baud_rate_str.toInt());
    }
    return baud_rate;
}

/// Pick up the list of known NMEA0183 message IDs that should be accepted by the logger
/// and written to SD card.  This is done using a std::set<String> so that looking should
/// be relatively fast.  No IDs in the set implies that all IDs shoud be accepted.

void Logger::retrieveIDFilter(void)
{
    logger::N0183IDStore filt;
    filt.BuildSet(m_filter);
}

/// Determine whether the message recorded is to be filtered out, or written to the SD card
/// for delivery to the database.  This is based on the set of NMEA0183 message identifiers
/// configured by the user (logger::N0183IDStore).  A blank list implies that all messages
/// are to be accepted and logged.
///
/// \param s    Pointer to the Sentence received.
/// \return True if the Sentence is to be filtered (i.e., dropped), or False if it is to be logged.

bool Logger::filterMessage(Sentence const *s)
{
    if (m_filter.empty()) return false; // No IDs means accept everything
    return m_filter.find(s->MessageID()) == m_filter.end();
}
                                       
Logger::~Logger(void)
{
}

/// Handle as many characters as are waiting on the serial channels, using the assemblers to build them
/// into messages, and then checking and serialising when they indicate that a sentence has been completed.
/// This essentially gives a stateless interface to NMEA0183 message handling, since all of the state is
/// encapsulated here.

void Logger::ProcessMessages(void)
{
    Sentence const *sentence;
    while (Serial1.available()) {
        m_channel[0].AddCharacter(Serial1.read());
    }
    while (Serial2.available()) {
        m_channel[1].AddCharacter(Serial2.read());
    }
    for (int channel = 0; channel < ChannelCount; ++channel) {
        while ((sentence = m_channel[channel].NextSentence()) != nullptr) {
            if (filterMessage(sentence)) {
                if (m_verbose) {
                    Serial.printf("DBG: rejecting sentence \"%s\" due to filtering constraints.\n", sentence->Contents());
                }
                continue;
            }
            if (!sentence->Valid()) {
                if (m_verbose) {
                    Serial.printf("DBG: rejecting |%s| because it is invalid.\n", sentence->Contents());
                }
                continue;
            }
            if (m_verbose) {
                Serial.printf("DBG: logging \"%s\"\n", sentence->Contents());
            }

            logger::DataObs obs(sentence->Timestamp(), sentence->Contents());
            logger::Metrics.RegisterObs(obs);

            // In order to avoid checking the message ID here, and then again to work out how to
            // parse, we offer each valid, non-filtered message to the time-referencing code, but only
            // attempt to reset the timeofday() value if the offer is accepted.
            if (m_timeref->setReference(sentence->Timestamp(), sentence)) {
                m_logManager->UpdateTimeofday();
            }

            Serialisable s;
            s += sentence->Timestamp();
            s += sentence->Contents();
            m_logManager->Record(logger::Manager::PacketIDs::Pkt_NMEAString, s);
        }
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

/// Report the versioning information for the logger, primarily so that it can be written
/// into the log file to allow the reader to adapt to the contents during read.
///
/// \param major    Major software version
/// \param minor    Minor software version
/// \param patch    Patch level/build level

void Logger::SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch)
{
    major = SoftwareVersionMajor;
    minor = SoftwareVersionMinor;
    patch = SoftwareVersionPatch;
}

/// Set the verbose reporting status of the logger (and the message assemblers)
///
/// \param verbose  Set to true for detailed information, or false for quiet

void Logger::SetVerbose(bool verbose)
{
    m_verbose = verbose;
    for (int ch = 0; ch < ChannelCount; ++ch) {
        m_channel[ch].SetDebugging(verbose);
    }
}

/// Configure the hardware inversion for one channel of the logger's NMEA0183 interface
/// so that all bits are flipped before they appear at the UART input.  This can be used
/// to fix reversed polarity on NMEA0183 inputs, a common problem during installation.
///
/// \param port     Port (1/2) to invert
/// \param invert   Flag: True => invert, False => as is.

void Logger::SetRxInvert(uint32_t port, bool invert)
{
    if (port < 1 || port > ChannelCount) {
        Serial.printf("ERR: can't set rx-invert for port %d\n", port);
    } else {
        if (port == 1)
            Serial1.setRxInvert(invert);
        else if (port == 2)
            Serial2.setRxInvert(invert);
    }
}

}
}
