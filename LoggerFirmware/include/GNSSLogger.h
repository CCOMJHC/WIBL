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

#include "LogManager.h"
#include "SparkFun_u-blox_GNSS_v3.h"

namespace gnss {

/// \class Logger
/// \brief Provide abstracted interface to a u-blox GNSS receiver
///
/// This provides the WIBL interface abstraction to a u-blox GNSS receiver, typically the F9P or better,
/// that is used to initialise, configure, and extract data (both real-time position and time, and raw
/// observations for post-processing) from the GNSS recevier.  The system will generate output serialiser
/// packets for raw data (storing the binary transferred from the receiver), and separate GNSS and
/// SystemTime packets from the receiver's real-time solutions.

class Logger {
public:
    Logger(logger::Manager *output);
    ~Logger(void);

    /// \brief Generate reporting string for the software module
    static String SoftwareVersion(void);
    /// \brief Extract the software version for the module (for further computation)
    static void SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch);

private:
    SFE_UBLOX_GNSS  *m_sensor;  ///< Pointer to the receiver abstraction
    logger::Manager *m_output;  ///< Pointer to the (shared) output log manager for data reporting
    bool            m_verbose;  ///< Flag: True => lots more output information
};

}
