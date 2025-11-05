/*!\file simulator.cpp
 * \brief Encapsulate a simple simulator for data generation that can be reflected on both busses.
 *
 * This defines the core simulator for time, position, and depth so that the same information can
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

 #ifndef __SIMULATOR_H__
 #define __SIMULATOR_H__

 #include "StatusLED.h"

class Simulator {
public:
    Simulator(void);
    void StepSimulator(StatusLED *leds);

private:
    double UnitNormal(void);
    bool StepDepth(unsigned long now);
    bool StepPosition(unsigned long now);
    bool StepTime(unsigned long now);

    bool iset;      ///< Global for Gaussian variate generator (from Numerical Recipies)
    float gset;     ///< Global state for Gaussian variate generator (from Numerical Recipies)

    // Parameters to determine when to issue the NMEA0183 simulator packets
    unsigned long target_depth_time;    ///< Time in milliseconds for the next DBT (depth) packet to be sent
    unsigned long target_position_time; ///< Time in milliseconds for the next GGA (position) packet to be sent
    unsigned long target_zda_time;      ///< Time in milliseconds for the next ZDA (time tick) packet to be sent

    // State parameters for the depth (DBT) message
    double current_depth;            ///< Simulator state: depth in metres
    double measurement_uncertainty;  ///< Simulator state: depth sounder measurement uncertainty, std. dev., metres
    double depth_random_walk;        ///< Simuator state: standard deviation, metres change in one second for depth changes

    // State parameters for the time (ZDA) message
    int current_year;           ///< Simulator state: current year for the simulation
    int current_day_of_year;    ///< Simulator state: current day of the year (a.k.a. Julian Day) for the simulation
    int current_hours;          ///< Simulator state: current time of day, hours past midnight
    int current_minutes;        ///< Simulator state: current time of day, minutes past the hour
    double current_seconds;     ///< Simulator state: vurrent time of day, seconds past the minute

    // State parameters for the position (GGA) message
    double current_longitude;       ///< Simulator state: longitude in degrees
    double current_latitude;        ///< Simulator state: latitude in degress
    double position_step;           ///< Simulator state: change in latitude/longitude per second
    double latitude_scale;          ///< Simulator state: current direction of latitude change
    double last_latitude_reversal;  ///< Simulator state: last time the latitude changed direction
};

extern Simulator simulator;

 #endif
