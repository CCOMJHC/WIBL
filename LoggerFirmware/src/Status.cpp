/*!\file Status.cpp
 * \brief General commands to support status report generation
 *
 * The logger needs to generate status information to report to the user, and for
 * uploads when enabled.  The free functions here manage this process, and the
 * construction of DynamicJsonDocuments (without the memory hassles).
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
#include "Configuration.h"
#include "N0183Logger.h"
#include "N2kLogger.h"
#include "IMULogger.h"
#include "SerialCommand.h"
#include "DataMetrics.h"

namespace logger {
namespace status {

/// Generate a list of all known files on the logger (and their attributes) into
/// an existing JSON document.  This includes the number of files, their reference
/// IDs, sizes, MD5 hashes, and filenames in the store.
///
/// @param filelist JsonDocument with the file list, ready to insert

DynamicJsonDocument GenerateFilelist(logger::Manager *m)
{
    uint32_t *filenumbers = new uint32_t[logger::MaxLogFiles];
    uint32_t n_files = m->CountLogFiles(filenumbers);
    DynamicJsonDocument doc(100*n_files + 256); // Approximate guess, but can expand

    doc["files"]["count"] = n_files;
    for (int n = 0; n < n_files; ++n) {
        String filename;
        uint32_t filesize;
        logger::Manager::MD5Hash filehash;
        uint16_t uploadCount;
        m->EnumerateLogFile(filenumbers[n], filename, filesize, filehash, uploadCount);
        StaticJsonDocument<256> entry;
        entry["id"] = filenumbers[n];
        entry["len"] = filesize;
        if (!filehash.Empty())
            entry["md5"] = filehash.Value();
        entry["url"] = filename;
        entry["uploads"] = uploadCount;

        int entry_size = entry.memoryUsage();
        if (doc.memoryUsage() + entry_size > 0.95*doc.capacity()) {
            // It's likely that adding the entry will cause the document to run out of
            // space.  We therefore double the capacity (since it's expensive, and we
            // don't want to have to do it more than once) before we attempt the addition.
            int capacity = doc.capacity() * 2;
            DynamicJsonDocument new_doc(capacity);
            new_doc.set(doc);
            doc = new_doc;
        }
        if (!doc["files"]["detail"].add(entry.as<JsonObject>())) {
            // Out of memory, even after adding more above (most likely),
            // so make a new allocation.  Note that the addition can partially
            // work, so you can end up with a malformed entry in the array (and
            // one more entry than you expect).  We therefore remove this last
            // element before continuing -- luckily, it should be at the index in
            // the array of the file number.
            doc["files"]["detail"].remove(n);
            int capacity = doc.capacity() * 2;
            DynamicJsonDocument new_doc(capacity);
            new_doc.set(doc);
            doc = new_doc;
            doc["files"]["detail"].add(entry.as<JsonObject>());
        }
    }
    delete[] filenumbers;
    return doc;
}

DynamicJsonDocument CurrentStatus(logger::Manager *m)
{
    DynamicJsonDocument filelist(GenerateFilelist(m));
    DynamicJsonDocument lkg(logger::Metrics.LastKnownGood());

    // The total capacity should be, approximately, the sum of the biggest components
    // (above), plus some limited information on versions, elapsed time, and boot
    // status.  We're assuming here that 1024B is enough for the extras ... that
    // might not always be the case.
    int capacity = filelist.capacity() + lkg.capacity() + 1024;

    DynamicJsonDocument status(capacity);

    status["version"]["firmware"] = logger::FirmwareVersion();
    status["version"]["commandproc"] = SerialCommand::SoftwareVersion();
    status["version"]["nmea0183"] = nmea::N0183::Logger::SoftwareVersion();
    status["version"]["nmea2000"] = nmea::N2000::Logger::SoftwareVersion();
    status["version"]["imu"] = imu::Logger::SoftwareVersion();
    status["version"]["serialiser"] = Serialiser::SoftwareVersion();

    int now = millis();
    status["elapsed"] = now;
    
    status["supply"] = logger::Metrics.SupplyVoltage();

    String server_status, boot_status;
    logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, server_status);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_WS_BOOTSTATUS_S, boot_status);
    status["webserver"]["current"] = server_status;
    status["webserver"]["boot"] = boot_status;

    status["data"] = lkg;
    status["files"] = filelist["files"];

    return status;
}

DynamicJsonDocument GenerateJSON(String const& source)
{
    size_t capacity = std::max<size_t>(source.length()*2, 1024);
    bool done = false;
    DeserializationError err;
    while (true) {
        DynamicJsonDocument doc(capacity);
        if ((err = deserializeJson(doc, source)) == DeserializationError::NoMemory) {
            capacity *= 2;
        } else if (err == DeserializationError::Ok) {
            return doc;
        } else {
            done = true;
        }
    }
    // If we get to here, then something went wrong on the deserialisation that wasn't
    // not having enough memory, so we need to report that to the end user.  This really
    // shouldn't happen, because the internal JSON should always be well formed, but ...
    DynamicJsonDocument doc(256 + strlen(err.c_str()));
    doc["error"]["message"] = String("failed to render internal string to JSON for transaction");
    doc["error"]["detail"] = err.c_str();
    return doc;
}

}
}
