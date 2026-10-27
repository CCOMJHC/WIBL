/*!\file timing.h
 * \brief Types and definitions for time-stamp generation from various sources
 *
 * Although we do time-stamping mostly in post-processing, we need to capture the raw materials
 * for that (particularly an elapsed time since boot with suitable resolution, and a real time
 * associated with it) derived from either input NMEA messages, or an in-built GNSS receiver, and
 * we need to be able to generate at least an approximate time-stamp so that we can give logged
 * files appropriate creation times to make them easier to tell apart.
 * 
 * When we have multiple sources, we also need to be able to give an order of preference so that
 * we can defend against missing data and always have a backup, which is defined through a core class
 * with plug-in data receivers that can be used by the various loggers to provide the source data
 * that can be used to determine time.
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

#ifndef __TIMING_H__
#define __TIMING_H__

#include <vector>
#include <list>
#include <ctime>
#include <cstdint>
#include "Arduino.h"

namespace timing {

/// \struct TimePoint
/// \brief A simple POD for an elapsed count and associated UTC timestamp
struct TimePoint {
    uint64_t    elapsed;        ///< Elapsed 1MHz count since boot
    time_t      second;         ///< UTC second corresponding to elapsed count
    uint32_t    microsecond;    ///< UTC microsecond corresponding to elapsed count

    TimePoint(void) { reset(); }
    void reset(void);
    bool isValid(void) const { return elapsed != 0ULL; }
    String printable(void) const;
};

class BaseTimeSource {
public:
    virtual ~BaseTimeSource(void) {}
    virtual bool assigntime(uint64_t const elapsed, TimePoint& now) = 0;
    virtual String printable(void) const = 0;
    virtual bool isValid(void) const = 0;
};

/// \enum SourcePriority
/// \brief Describe the level of quality to expect from a \a BaseTimeSource
enum SourcePriority {
    TIMING_REFERENCE = 0,   ///< Atomic reference (e.g., a locked GNSS)
    TIMING_HIGH,            ///< High performance (e.g., NMEA2000 SystemTime or equivalent)
    TIMING_LOW,             ///< Low performance (e.g., NMEA0183 ZDA or equivalent)
    TIMING_MAXPRI
};

/// \class Timestamper
/// \brief Manage time sources to provide a translation of elapsed time to real time
class Timestamper {
public:
    Timestamper();
    ~Timestamper();

    void RegisterSource(BaseTimeSource *source, SourcePriority const priority);

    uint64_t GetElapsed(void);
    bool Translate(uint64_t const elapsed, TimePoint& now, SourcePriority& source);

    inline bool Timestamp(TimePoint& now, SourcePriority& source) {
        return Translate(GetElapsed(), now, source);
    }
    void update_timeofday(void);

private:
    hw_timer_t      *m_timer;
    std::vector<std::list<BaseTimeSource*>> m_sources;
    time_t          m_lastSystemTime;
};

}

#endif
 