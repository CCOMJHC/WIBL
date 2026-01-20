/*!\file GNSSLogger.h
 * \brief WIBL interface to the U-blox ZED-F9P GNSS module
 *
 * This provides an abstraction over the details of the ZED-F9P GNSS module so that it's simpler
 * to use within the logger firmware.  This sets up the module to run with as many constellations as
 * possible, but to use GPS (NavStar) as primary.  The real-time position and time is used as for
 * position records (in case the post-processing fails for any reason), and time synchronisation
 * through a 1PPS signal routed to an ESP32 pin for the interrupt routine.  The real-time position and
 * time go into the output data stream in the same way as NMEA2000 messages, with tags to indicate that
 * they should be the preferred solutions for processing reconstruction if the post-processed data cannot
 * be used for any reason.
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

namespace gnss {

class Logger {
    Logger(void);
    ~Logger(void);
};

}
