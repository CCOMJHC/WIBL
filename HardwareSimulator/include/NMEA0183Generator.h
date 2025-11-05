/*!\file NMEA0183Simulator.h
 * \brief This module generates a very simple set of NMEA0183 sentences on Serial1 and Serial2
 *
 * This code generates a SDDBT and GPGGA sentence sequence on Serial 1 and Serial 2 (respectively)
 * over time, with the position and depth changing from time to time to demonstrate that the CRC is
 * being computed correctly.
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

#ifndef __NMEA0183_SIMULATOR_H__
#define __NMEA0183_SIMULATOR_H__

namespace nmea0183 {

void GenerateZDA(int year, int month, int day, int hour, int minute, double second);
void GenerateDepth(double depth_metres);
void GeneratePosition(double latitude, double longitude, int hour, int minute, double second);

}

#endif
