/*!\file timing.cpp
 * \brief Implementation of types and code for time-stamp generation from multiple sources
 *
 * This code implements a core object for timestamping from the user level, with sub-objects
 * (base and derived) that implement data selection for a source of time information (e.g.,
 * NMEA messages or GNSS receiver) which can be registered with the core object as sources of
 * time information for real-time (and post-processing) use.  The core object provides the
 * methods to get an elapsed time from one of the hardware counters, and correct it to a real
 * time based on the available information from the various sources.
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

 #include <time.h>
#include "driver/gptimer.h"
#include "timing.h"

namespace timing {

void TimePoint::reset(void)
{
    elapsed = 0ULL;
    second = (time_t)0;
    microsecond = 0UL;
}

String TimePoint::printable(void) const
{
    String rtn;
    double seconds = second + microsecond / 1000000.0;
    rtn = "R: " + String(seconds) + " s since datum, " +
        String(elapsed) + " pseudo-us since boot";
    return rtn;
}

const uint32_t TIMER_FREQUENCY = 1000000;

Timestamper::Timestamper(void)
: m_lastSystemTime(0)
{
    if ((m_timer = timerBegin(TIMER_FREQUENCY)) == nullptr) {
        Serial.print("ERR: failed to configure hardware timer for timing sub-system.\n");
        return;
    }
    m_sources.resize(SourcePriority::TIMING_MAXPRI);
}

Timestamper::~Timestamper(void)
{
    if (m_timer != nullptr) {
        timerEnd(m_timer);
    }
}

void Timestamper::RegisterSource(BaseTimeSource *source, SourcePriority const priority)
{
    if (priority < TIMING_REFERENCE || priority > TIMING_LOW) return;
    m_sources[static_cast<int>(priority)].push_back(source);
}

uint64_t Timestamper::GetElapsed(void)
{
    if (m_timer != nullptr) {
        return timerRead(m_timer);
    }
    return 0ULL;
}

bool Timestamper::Translate(uint64_t const elapsed, TimePoint& now, SourcePriority& source)
{
    for (int s = (int)TIMING_REFERENCE; s < (int)TIMING_MAXPRI; ++s) {
        int count = 0;
        for (auto it = m_sources[s].begin(); it != m_sources[s].end(); ++it, ++count) {
            if ((*it)->assigntime(elapsed, now)) {
                source = static_cast<SourcePriority>(s);
                return true;
            }
        }
    }
    return false;
}

void Timestamper::update_timeofday(void)
{
    TimePoint now;
    SourcePriority source;

    if (!Timestamp(now, source)) {
        return;
    }

    // This routine can be called each time new information is added to the system, so it's
    // possible that we might end up with the same time being returned (at least to the second)
    // on multiple calls, which means we can optimise away the system call.
    if (now.second <= m_lastSystemTime) {
        return;
    }

    struct timeval tv = { .tv_sec = now.second, .tv_usec = static_cast<suseconds_t>(now.microsecond) };
    //Serial.printf("DBG: setting time of day to %s\n", now.printable().c_str());
    settimeofday(&tv, nullptr);
    m_lastSystemTime = now.second;
}

}
