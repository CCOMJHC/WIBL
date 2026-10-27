/*!\file Status.h
 * \brief General commands to support status report generation
 *
 * The logger needs to generate status information to report to the user, and for
 * uploads when enabled.  The free functions here manage this process, and the
 * construction of JsonDocuments (without the memory hassles).
 *
 * Copyright (c) 2024, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include "ArduinoJson.h"
#include "LogManager.h"

namespace logger {
namespace status {

/// @brief Generate a JSON list of the set of files (and their metrics) currently on the logger
JsonDocument GenerateFilelist(logger::Manager *m);

/// @brief Generate a JSON document representing the current status of the logger
JsonDocument CurrentStatus(logger::Manager *m);

/// @brief Generate a correctly-sized JSON document from a minified string
JsonDocument GenerateJSON(String const& s);

}
}
