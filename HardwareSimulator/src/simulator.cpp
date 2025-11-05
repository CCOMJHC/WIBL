/*!\file simulator.cpp
 * \brief Encapsulate a simple simulator for data generation that can be reflected on both busses.
 *
 * This implements the core simulator for time, position, and depth so that the same information can
 * be used for NMEA0183 and NMEA2000 channels.  The code here steps the state of the simulator when
 * required, and flags when things have changed so that the specific output channels can format
 * appropriately.
 * 
 * Copyright (c) 2025, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include <Arduino.h>
#include "simulator.h"
#include "NMEA0183Generator.h"
#include "NMEA2000Generator.h"

Simulator simulator;

Simulator::Simulator(void)
{
    iset = false;
    gset = 0.0f;

    target_depth_time = 0;
    target_position_time = 0;
    target_zda_time = 0;

    current_depth = 10.0;
    measurement_uncertainty = 0.06;
    depth_random_walk = 0.02;

    current_year = 2025;
    current_day_of_year = 0;
    current_hours = 0;
    current_minutes = 0;
    current_seconds = 0.0;

    current_longitude = -75.0;
    current_latitude = 43.0;
    position_step = 3.2708e-06;
    latitude_scale = +1.0;
    last_latitude_reversal = 0.0;
}

/// Simulate a unit Gaussian variate, using the method of Numerical Recipes.  Note
/// that this preserves state in global variables, so it isn't great, but it does do
/// the job, and gets most benefit from the random simulation calls.  The code does,
/// however, rely on the quality of the standard random() call in the supporting
/// environment, and therefore the statistical quality of the variates is only as good
/// as the underlying linear PRNG.
///
/// \return A sample from a zero mean, unit standard deviation, Gaussian distribution.

double Simulator::UnitNormal(void)
{
    float fac, rsq, v1, v2;
    float u, v, r;

    if (!iset) {
        do {
            u = random(1000)/1000.0;
            v = random(1000)/1000.0;
            v1 = 2.0*u - 1.0;
            v2 = 2.0*v - 1.0;
            rsq = v1*v1 + v2*v2;
        } while (rsq >= 1.0 || rsq == 0.0);
        fac = sqrt(-2.0*log(rsq)/rsq);
        gset = v1*fac;
        iset = true;
        r = v2*fac;
    } else {
        iset = false;
        r = gset;
    }
    return r;
}

bool Simulator::StepDepth(unsigned long now)
{
    if (now < target_depth_time) return false;
    current_depth += depth_random_walk*UnitNormal();
    target_depth_time = now + 1000 + (int)(1000*(random(1000)/1000.0));

    double depth = current_depth + measurement_uncertainty*UnitNormal();
    nmea0183::GenerateDepth(depth);
    nmea2000::GenerateDepth(depth);

    return true;
}

bool Simulator::StepPosition(unsigned long now)
{
    if (now < target_position_time) return false;
    
    current_latitude += latitude_scale * position_step;
    current_longitude += 1.0 * position_step;

    if (now - last_latitude_reversal > 3600000.0) {
        latitude_scale = -latitude_scale;
        last_latitude_reversal = now;
    }
    target_position_time = now + 1000;

    nmea0183::GeneratePosition(current_latitude, current_longitude, current_hours, current_minutes, current_seconds);
    nmea2000::GenerateGNSS(current_latitude, current_longitude, current_hours, current_minutes, current_seconds);

    return true;
}

bool Simulator::StepTime(unsigned long now)
{
    if (now < target_zda_time) return false;
    
    current_seconds += 1.0;
    if (current_seconds >= 60.0) {
        current_minutes++;
        current_seconds -= 60.0;
        if (current_minutes >= 60) {
            current_hours++;
            current_minutes = 0;
            if (current_hours >= 24) {
                current_day_of_year++;
                current_hours = 0;
                if (current_day_of_year > 365) {
                    current_year++;
                    current_day_of_year = 0;
                }
            }
        }
    }
    target_zda_time = now + 1000;

    nmea0183::GenerateZDA(current_year, current_day_of_year, current_hours, current_minutes, current_seconds);
    nmea2000::GenerateSystemTime(current_year, current_day_of_year, current_hours, current_minutes, current_seconds);
    
    return true;
}

void Simulator::StepSimulator(StatusLED *leds)
{
    unsigned long now = millis();
    if (StepDepth(now)) leds->TriggerDataIndication();
    if (StepPosition(now)) leds->TriggerDataIndication();
    if (StepTime(now)) leds->TriggerDataIndication();
}
