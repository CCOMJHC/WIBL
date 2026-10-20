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

#include "driver/timer.h"

#include "timing.h"
namespace timing {

String TimePoint::printable(void) const
{
    String rtn;
    double seconds = second + microsecond / 1000000.0;
    rtn = "R: " + String(seconds) + " s since datum, " +
        String(elapsed) + " us since boot";
    return rtn;
}

const int TIMER_DIVIDER = 80;
const int TIMER_NUMBER = 0;
const bool TIMER_COUNTDIR = true; // Count up from zero by default

Timestamper::Timestamper(void)
{
    if ((m_timer = timerBegin(TIMER_NUMBER, TIMER_DIVIDER, TIMER_COUNTDIR)) == nullptr) {
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
    m_sources[static_cast<int>(priority)].push_back(source);
}

uint64_t Timestamper::GetElapsed(void)
{
    if (m_timer != nullptr) {
        return timerRead(m_timer);
    }
    return 0ULL;
}

bool Timestamper::Translate(uint64_t const elapsed, TimePoint& now)
{
    for (int n = 0; n < static_cast<int>(SourcePriority::TIMING_MAXPRI); ++n) {
        for (auto it = m_sources[n].begin(); it != m_sources[n].end(); ++it) {
            if ((*it)->assigntime(elapsed, now)) {
                return true;
            }
        }
    }
    return false;
}

}
