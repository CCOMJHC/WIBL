/*! \file SerialisableFactory.h
 *  \brief Convert from various data packet types to a Serialisable
 *
 *  This object constructs a Serialisable from a number of different input packets
 *  so that the user doesn't have to fret about the details of the conversion.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping and
 * NOAA/UNH Joint Hydrographic Center.  All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
 * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

#ifndef __SERIALISABLE_FACTORY_H__
#define __SERIALISABLE_FACTORY_H__

#include <memory>
#include <string>
#include "N2kMsg.h"
#include "serialisation.h"

/// \class SerialisableFactory
/// \brief Convert from different input packets to a Serialisable

class SerialisableFactory {
public:
    /// \brief Convert from a NMEA2000 packet into a \a Serialisable packet
    static std::shared_ptr<Serialisable> Convert(tN2kMsg& msg,
        std::set<uint32_t> const& raw_pgn, bool const& all_pgn,
        PayloadID& payload_id, bool& noData_detected);
    /// \brief Convert from a NMEA0183 sentence string into a \a Serialisable packet
    static std::shared_ptr<Serialisable> Convert(uint32_t elapsed_time, std::string& nmea_string, PayloadID& payload_id);
    /// \brief Convert from a JSON metadata filename to a \a Serialisable packet
    static std::shared_ptr<Serialisable> Convert(std::string const& filename, PayloadID& payload_id);
};

#endif
