/*! \file NMEA0183Simulator.cpp
 * \brief Generate faked NMEA0183-formated data on the software serial output line
 *
 * This generates example NMEA0183 data for a GNSS with depth sounder on a single line,
 * changing the position and depth as a function of time.  The position information is
 * passed out at 1Hz, and the depth data at 0.5-1.0Hz (randomly).  The position and depth
 * are changed over time, with suitable constraints to maintain consistency.
 */
/// Copyright 2020 Center for Coastal and Ocean Mapping & NOAA-UNH Joint
/// Hydrographic Center, University of New Hampshire.
///
/// Permission is hereby granted, free of charge, to any person obtaining a copy
/// of this software and associated documentation files (the "Software"), to deal
/// in the Software without restriction, including without limitation the rights to use,
/// copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
/// and to permit persons to whom the Software is furnished to do so, subject to
/// the following conditions:
///
/// The above copyright notice and this permission notice shall be included in
/// all copies or substantial portions of the Software.
///
/// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
/// EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
/// OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
/// NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
/// HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
/// WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
/// FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE
/// OR OTHER DEALINGS IN THE SOFTWARE.

#include <Arduino.h>
#include "NMEA0183Generator.h"

namespace nmea0183 {

/// Generate checksums for NMEA0183 messages.  The checksum is a simple XOR of all of the
/// contents of the message between (and including) the leading "$" and trailing "*", and
/// is returned as an 8-bit integer.  This needs to be converted to two hex digits before
/// appending to the end of the message to complete it.  The code here does not modify the
/// message, however.
///
/// \param msg  NMEA0183-formatted message for which to compute the byte-wise XOR checksum
/// \return XOR of the contents of \a msg, taken an 8-bit byte at a time

int compute_checksum(const char *msg)
{
    int chk = 0;
    int len = (int)strlen(msg);
    for (int i = 1; i < len-1; ++i) {
        chk ^= msg[i];
    }
    return chk;
}

/// Simulate the depth being seen by the echosounder, expressed as a SDDBT NMEA0183 message.  The
/// simulation runs in metres, but then converts to feet and fathoms as required by the message
/// format.  The simulation is a random walk with Gaussian variate simulation steps, with variance
/// controlled by compile-time constants.  The code here will only generate a point if the code
/// has reached or exceeded the target time for the next packet, and updates this target time with
/// a random component for the next go-around.  Logging is also done so that the user can see
/// that the simulation is proceeding, if they're monitoring the serial output line.
///     The ESP32-based hardware has two serial output lines that could be used to transmit the
/// simulated messages.  In order to allow testing of simultaneous reception of messages on both
/// reception channels, the code here generates the SDDBT messages on channel 1.
///     Note that the simulation step could, arguably, be something that should increase in variance
/// with the time between the last output and this (i.e., the seafloor has a higher probability of
/// changing more the longer you go between observing it), but that seems to be a little more
/// hassle than it's worth for the current purposes.
///
/// \param led  Pointer to the status LED controller so that we can flash them if data is transmitted

void GenerateDepth(double depth_metres)
{
    double depth_feet = depth_metres * 3.2808;
    double depth_fathoms = depth_metres * 0.5468;

    char msg[255];
    int pos = sprintf(msg, "$SDDBT,%.1lf,f,%.1lf,M,%.1lf,F*", depth_feet, depth_metres, depth_fathoms);
    int chksum = compute_checksum(msg);
    sprintf(msg + pos, "%02X\r\n", chksum);

    String txt = "Sending SDDBT: ";
    Serial.print(txt + msg);
    Serial1.print(msg);
    Serial1.flush();
}

/// Break an angle in degrees into the components required to format for ouptut
/// in a NMEA0183 GGA message (i.e., integer degrees and decimal minutes, with an
/// indicator for which hemisphere to use).  To allow this to be uniform, the code
/// assumes a positive angle is hemisphere 1, and negative angle hemisphere 0.  It's
/// up to the caller to decide what decorations are used for those in the display.
///
/// \param angle    Angle (degrees) to break apart
/// \param d        (Out) pointer to space for the integer part of the angle (degrees)
/// \param m        (Out) pointer to space for the decimal minutes part of the angle
/// \param hemi     (Out) Pointer to space for a hemisphere indicator

void format_angle(double angle, int *d, double *m, int *hemi)
{
    if (angle > 0.0) {
        *hemi = 1;
    } else {
        *hemi = 0;
        angle = -angle;
    }

    *d = (int)angle;
    *m = angle - *d;
}

/// Generate a simulated position (GGA) message.  The simulator only generates a new message once
/// the time advances to the previously specified target time (which is then updated for the next
/// step, specified to be exactly 1.0s).  Each simulated step moves ahead by a fixed amount in
/// latitude and longitude (specified at compile time), with the latitude changing direction every
/// hour so that it stays in bounds.  The remainder of the text of the GGA is constant, and therefore
/// probably not a great simulation (e.g., of the separation), but good enough for testing the hardware.
///     The ESP32-based hardware has two serial output lines that could be used to transmit the
/// simulated messages.  In order to allow testing of simultaneous reception of messages on both
/// reception channels, the code here generates the SDDBT messages on channel 2.
///
/// \param led  Pointer to the status LED controller so that we can flash them if data is transmitted

void GeneratePosition(double latitude, double longitude, int hour, int minute, double second)
{
    char msg[255];
    int pos = sprintf(msg, "$GPGGA,%02d%02d%06.3f,", hour, minute, second);
    int degrees;
    double minutes;
    int hemisphere;
    format_angle(latitude, &degrees, &minutes, &hemisphere);
    pos += sprintf(msg + pos, "%02d%09.6lf,%c,", degrees, minutes, hemisphere == 1 ? 'N' : 'S');
    format_angle(longitude, &degrees, &minutes, &hemisphere);
    pos += sprintf(msg + pos, "%03d%09.6lf,%c,", degrees, minutes, hemisphere == 1 ? 'E' : 'W');
    pos += sprintf(msg + pos, "3,12,1.0,-19.5,M,22.5,M,0.0,0000*");
    int chksum = compute_checksum(msg);
    sprintf(msg + pos, "%02X\r\n", chksum);

    String txt = "Sending GGA: ";
    Serial.print(txt + msg);
    Serial2.print(msg);
    Serial2.flush();
}

/// Convert from a year, and day-of-year (a.k.a., albeit inaccurately, Julian Day) to
/// a month/day pair, as required for ouptut of ZDA information.  Keeping the time
/// as a day of the year makes the simulation simpler ...
///
/// \param year         Current year of the simulation
/// \param year_day     Current day-of-year of the simulation
/// \param month        (Out) Reference for store of the month of the year
/// \param day          (Out) Reference for store of the day of the month

void ToDayMonth(int year, int year_day, int& month, int& day)
{
    unsigned     leap;
    static unsigned months[12] = { 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31 };
    
    /* Determine whether this is a leap year.  Leap years in the Gregorian
     * calendar are years divisible by four, unless they are also a century
     * year, except when the century is also divisible by 400.  Thus 1900 is
     * not a leap year (although it is divisible by 4), but 2000 is, because
     * it is divisible by 4 and 400).
     */
    if ((year%4) == 0) {
            /* Potentially a leap year, check for century year */
            if ((year%100) == 0) {
                    /* Century year, check for 400 years */
                    if ((year%400) == 0)
                            leap = 1;
                    else
                            leap = 0;
            } else
                    leap = 1;
    } else
            leap = 0;
    day = year_day + 1; // External is [0, 364], but we assume here [1, 365]
    
    months[1] += leap;      /* Correct February */
    
    /* Compute month by reducing days until we have less than the next months
     * total number of days.
     */
    month = 0;
    while (day > months[month]) {
            day -= months[month];
            ++month;
    }
    ++month; // External is [1, 12] but here it's [0, 11]
    
    months[1] -= leap;      /* Uncorrect February */
}

/// Simulate a ZDA time stamp message, at 1Hz.  This just reports the real-time of the
/// simulation, based on the delta from the last time the ZDA was generated (in milliseconds)
/// as the advance of time.  Since this is a finite computation, it's possible that we
/// might slip a little each time, making the output not quite 1Hz, but it's unlikely to
/// be a major problem for the simulator, which is designed to test simultaneous reception
/// of the messages on the test hardware.
///     The ESP32-based hardware has two serial output lines that could be used to transmit the
/// simulated messages.  In order to allow testing of simultaneous reception of messages on both
/// reception channels, the code here generates the SDDBT messages on channel 2.
///
/// \param now  Current simulator time (in milliseconds since boot)
/// \param led  Pointer to the status LED controller so that we can flash them if data is transmitted

void GenerateZDA(int year, int yday, int hour, int minute, double second)
{
    int month, day;
    char msg[255];
    
    ToDayMonth(year, yday, month, day);
    int pos = sprintf(msg, "$GPZDA,%02d%02d%06.3lf,%02d,%02d,%04d,00,00*",
                      hour, minute, second, day, month, year);
    int chksum = compute_checksum(msg);
    sprintf(msg + pos, "%02X\r\n", chksum);

    String txt = "Sending ZDA: ";
    Serial.print(txt + msg);
    Serial2.print(msg);
    Serial2.flush();
}

}