/*! \file NVMFile.cpp
 *  \brief Generic Non-voltile Memory file storage for string data
 *
 * The logger has a number of instances where it needs to store one or more strings in
 * persistent, non-volatile, storage (typically flash memory of some kind).  This module
 * provides a primitive for this, and specialisations for particular cases.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include <set>
#include "NVMFile.h"
#include "FS.h"
#include "LittleFS.h"
#include "LogManager.h"
#include "serialisation.h"
#include "ArduinoJson.h"
#include "Status.h"

namespace logger {

/// Open a file from the non-volatile memory space on the logger, and read the contents ready
/// for use.  The internal store is a minified, stringified JSON format, which is converted to
/// a JSON document when required.  The NVM file is simply the stringified version of the JSON.
/// Note that the name of the file used for the NVM must meet the standards of the backing store
/// (potentially SPIFFS, so often 8.3 names, but here LittleFS, which is a little more forgiving).
///
/// @param filename Name of the file in the NVM to open.

NVMFile::NVMFile(String const& filename)
: m_backingStore(filename), m_changed(false)
{
    if (!LittleFS.exists(filename)) {
        File nf = LittleFS.open(filename, FILE_WRITE, true);
        if (nf) {
            nf.close();
        } else {
            Serial.printf("ERR: NVMFile could not create |%s| (LittleFS free ~%u B of %u B)\n",
                          filename.c_str(),
                          (unsigned)(LittleFS.totalBytes() - LittleFS.usedBytes()),
                          (unsigned)LittleFS.totalBytes());
        }
    }
    File f = LittleFS.open(filename, FILE_READ);
    if (!f) {
        Serial.printf("ERR: failed to open \"%s\" for NVM file read.\n", filename.c_str());
        m_backingStore = "";
        return;
    }
    m_contents = f.readString();
    f.close();
    if (m_contents.isEmpty()) {
        // First read, so we need to initialise to at least the minimum JSON document structure
        // so that the string will parse without failing in the ArduinoJson library.
        m_contents = String("{}");
    }
    //Serial.printf("DBG: NVMFile() read |%s| from |%s|\n", m_contents.c_str(), m_backingStore.c_str());
}

/// Write the contents of the object to non-volatile memory space on the logger as a simple
/// string.  Note that the system only writes the contents if something has changed; this is
/// determined by either a call to EndTransaction() or through an explicit call to MarkChanged()
/// (by a derived class that is specific to one file).
///
/// @return N/A

NVMFile::~NVMFile(void)
{
    if (Valid()) {
        if (m_changed) {
            File f = LittleFS.open(m_backingStore, FILE_WRITE, true);
            if (!f) {
                Serial.printf("ERR: failed to open |%s| for NVM file write (LittleFS free ~%u B).\n",
                              m_backingStore.c_str(),
                              (unsigned)(LittleFS.totalBytes() - LittleFS.usedBytes()));
                return;
            }
            //Serial.printf("DBG: ~NVMFile() writing |%s| to |%s|.\n", m_contents.c_str(), m_backingStore.c_str());
            f.print(m_contents);
            f.close();
        }
    }
}

/// Start a modification to the contents of the object.  This translates the contents of the
/// object into a DynamicJsonDocument (i.e., storage on the heap), with enough capacity to allow
/// for the object to be doubled in size.  This should allow most modifications to be made without
/// running out of space, but if that's a concern, the user has to check on this with the usual
/// ArduinoJson methods: the DynamicJsonDocument isn't extensible.  Note that the user owns the
/// returned document; this class keeps no record.
///
/// @return A DynamicJsonDocument with the contents of the object initialised.

DynamicJsonDocument NVMFile::BeginTransaction(void)
{
    return logger::status::GenerateJSON(m_contents);
}

/// Complete a transaction updating the contents of the object, updating the contents to the
/// document provided.  It is a basic assumption that the document provided as \a source is the
/// same as that provided by BeginTransaction() with some modifications, but the class here
/// doesn't attempt to validate this: whatever is passed is what's set.
///
/// @param source Document to parse into the object
/// @return Number of bytes written into the object (i.e., how many bytes were converted)

size_t NVMFile::EndTransaction(DynamicJsonDocument& source)
{
    m_contents.clear();
    m_changed = true;
    return serializeJson(source, m_contents);
}

/// Generate an optionally formatted version of the contents of the object.  If \a indented
/// is true, the code converts the internal string representation of the JSON object to a
/// new JsonDocument, and then re-serialises with indentation; otherwise, the output is a copy
/// of the minified JSON representation.
///
/// @param indented True if the output should be indended and prettified.
/// @return The string representation of the JSON object

String NVMFile::JSONRepresentation(bool indented)
{
    String rtn;
    if (!Valid()) return rtn;

    //Serial.printf("DBG: making JSON representation for NVM contents |%s| from |%s|\n",
    //   m_contents.c_str(), m_backingStore.c_str());
    if (indented) {
        // Since the contents string is minified, we need to deserialise, and then re-serialise ...
        DynamicJsonDocument doc(logger::status::GenerateJSON(m_contents));
        serializeJsonPretty(doc, rtn);
    } else {
        rtn = m_contents;
    }
    return rtn;
}

/// Extract the contents of the object to a JsonDocument (either static or dynamic to taste).  The
/// output is assumed to sufficiently large to handle the object, although there isn't really much
/// way to determine this.
///
/// @param dest Document into which to generate contents

DynamicJsonDocument NVMFile::GetContents(void)
{
    return logger::status::GenerateJSON(m_contents);
}

/// Replace the contents of the object with the specified document.  The previous contents of the
/// object are removed.
///
/// @param doc Source document to use for the object contents

void NVMFile::Set(JsonDocument& doc)
{
    if (!Valid()) throw Invalid();
    m_contents.clear();
    serializeJson(doc, m_contents);
    m_changed = true;
}

/// Replace the contents of the object with the specified string.  This assumes that the contents
/// of the string are a valid minified JSON document, and does not check that this is the case.
/// If you pass something that doesn't meet this requirement, bad things will likely happen.
///
/// @param doc Source document to use for the object contents

void NVMFile::Set(String const& doc)
{
    if (!Valid()) throw Invalid();
    m_contents = doc;
    m_changed = true;
}

/// Estimate the capacity required to represent the minified string in a JsonDocument.  This
/// is somewhat of a guess, since the exact computation would include all of the strings in
/// the representation, and then all of the internal structure for the parse tree of the
/// document (which isn't really known).
///
/// @param s    The minified JSON document as a string
/// @return An estimate of capacity in bytes

size_t NVMFile::EstimateCapacity(String const& minified)
{
    size_t capacity = minified.length() * 2;
    if (capacity < 1024) {
        capacity = 1024;
    }
    return capacity;
}

/// Construct an interface to access the storage for auxiliary metadata associated with the
/// data being generated by the logger.

MetadataStore::MetadataStore(void)
: NVMFile("/Metadata.txt")
{
}

/// Write the specified metadata into the associated backing store file.  Note that no test
/// or interpretation is done on the string: whatever you specify is what gets stored and then
/// dumped out with the data files.  Note that the string should contain no \r\n, otherwise there
/// will likely be problems getting the data back out.
///
/// @param s    Metadata string to store

void MetadataStore::SetMetadata(String const& s)
{
    Set(s);
}

/// Output metadata into an available binary output stream using the provided \a Serialiser object.
/// This allows the metadata to be added to any binary file being created.
///
/// @param s    Pointer to the \a Serialiser object to use to put the data into the output file

void MetadataStore::SerialiseMetadata(Serialiser *s)
{
    if (Empty()) return;

    String meta = JSONRepresentation();
    Serialisable packet(meta.length() + 4);

    packet += meta.length();
    packet += meta.c_str();
    s->Process(logger::Manager::PacketIDs::Pkt_JSON, packet);
}

/// Generate a specialisation of the NVM file for scale parameters used for internal instruments
/// that write unscaled information to the log file (which will need to be denormalised later).
/// The scales are stored as key/value pairs in JSON format, grouped together under a reference name
/// for the instrument (e.g., "imu").  It is up to the caller to ensure that the instrument name
/// is used consistently in the calling code.

ScalesStore::ScalesStore(void)
: NVMFile("/Scales.txt")
{
}

/// Add a scale value to the object.  Note that the @a name is expected to be unique within the
/// @a group, but could be re-used within another @a group.  Semantics of the ArduinoJson library
/// are such that using a new @a name will generate a new key/value pair directly, and therefore
/// a second call with the same @a group and @a name can be used to reset, and inconsistent use
/// of @a name will result in duplicates.
///
/// @param group    Instrument group in which to set the key/value pair
/// @param name     Key for the scale to set
/// @param value    Value for the scale to set
/// @return N/A

void ScalesStore::AddScale(String const& group, String const& name, double value)
{
    DynamicJsonDocument doc(BeginTransaction());
    if (doc.containsKey("error")) {
        // The internal JSON didn't convert
        Serial.printf("ERR: scales update failed (%s/%s)\n",
            doc["error"]["message"].as<const char *>(), doc["error"]["detail"].as<const char*>());
        return;
    }
    doc[group][name] = value;
    EndTransaction(doc);
}

void ScalesStore::AddScales(String const& group, const char *names[], double *values, int count)
{
    DynamicJsonDocument doc(BeginTransaction());
    if (doc.containsKey("error")) {
        // The internal JSON didn't convert
        Serial.printf("ERR: scales update failed (%s/%s)\n",
            doc["error"]["message"].as<const char *>(), doc["error"]["detail"].as<const char*>());
        return;
    }
    for (int n = 0; n < count; ++n) {
        doc[group][names[n]] = values[n];
    }
    EndTransaction(doc);
}

/// Remove all scales from the object.

void ScalesStore::ClearScales(void)
{
    Clear();
}

/// Output the serial scales metadata to the provided binary output stream using the provided
/// \a Serialiser object.  This allows the scales packet to be added to any binary file being
/// created.
///
/// @param s    Pointer to the \a Serialiser object to use to put the data into the output file

void ScalesStore::SerialiseScales(Serialiser *s)
{
    if (Empty()) return;

    String scales = JSONRepresentation();
    Serialisable packet(scales.length() + 4);

    packet += scales.length();
    packet += scales.c_str();
    s->Process(logger::Manager::PacketIDs::Pkt_SensorScales, packet);
}

/// Start a new interface to the list of algorithm requests stored with the logger.  These are algorithms
/// that the logger would recommend be run on the data at the post-processing stage, although there is
/// no guarantee that this will occur.

AlgoRequestStore::AlgoRequestStore(void)
: NVMFile("/Algorithms.txt")
{
    if (Empty()) {
        // First time opening the file from the NVM store
        StaticJsonDocument<256> doc;
        doc["count"] = 0;
        Set(doc);
    }
}

/// Write a new algorithm into the backing store, optionally restarting the file in order to clear
/// out any mistakes or algorithms no longer required.  There is no way to edit the algorithms or
/// parameters in place other than to restart --- the logger isn't meant to be that smart, and all
/// of that complexity has to come from the user configuration.  Note that the code here also doesn't
/// check that the algorithm makes sense, or that the parameters are well formed --- it accepts
/// whatever the user provides.
///
/// @param alg_name     Name of the algorithm being requested
/// @param alg_params   Parameters associate with the algorithm being requested

void AlgoRequestStore::AddAlgorithm(String const& alg_name, String const& alg_params)
{
    DynamicJsonDocument doc(BeginTransaction());
    if (doc.containsKey("error")) {
        // The internal JSON didn't convert
        Serial.printf("ERR: algorithm update failed (%s/%s)\n",
            doc["error"]["message"].as<const char *>(), doc["error"]["detail"].as<const char*>());
        return;
    }
    int count = doc["count"];
    StaticJsonDocument<256> entry;
    entry["name"] = alg_name;
    entry["parameters"] = alg_params;
    if ((doc.memoryUsage() + entry.capacity()) > 0.95*doc.capacity()) {
        // The document needs to be bigger to handle the new entry
        int capacity = doc.memoryUsage() + entry.capacity() + 256;
        DynamicJsonDocument new_doc(capacity);
        new_doc.set(doc);
        doc = new_doc;
    }
    doc["algorithm"].add(entry.as<JsonObject>());
    doc["count"] = count + 1;
    EndTransaction(doc);

    String temp(JSONRepresentation());
    //Serial.printf("DBG: AlgStore now |%s|\n", temp.c_str());
}

/// Empty the list of algorithms being stored by the logger, so that no requests are made of the
/// post-processing code.

void AlgoRequestStore::ClearAlgorithmList(void)
{
    StaticJsonDocument<128> doc;
    doc["count"] = 0;
    Set(doc);
}

/// Write a set of output blocks into the binary WIBL-format file containing the algorithms and their
/// parameters that are being recommended to the post-processing code.
///
/// @param s    Pointer to the @a Serialiser to write data into the required ouptut file

void AlgoRequestStore::SerialiseAlgorithms(Serialiser *s)
{
    DynamicJsonDocument doc(GetContents());

    int alg_count = doc["count"];
    for (int n = 0; n < alg_count; ++n) {
        String algorithm = doc["algorithm"][n]["name"];
        String parameters = doc["algorithm"][n]["parameters"];
        Serialisable ser(algorithm.length() + parameters.length() + sizeof(unsigned int)*2);
        ser += algorithm.length();
        ser += algorithm.c_str();
        ser += parameters.length();
        ser += parameters.c_str();
        s->Process(logger::Manager::PacketIDs::Pkt_Algorithms, ser); 
    }
}

void AlgoRequestStore::SerialiseSingleAlgorithm(String const& algo, String const& params, Serialiser *s)
{
    Serialisable ser(255);
    ser += algo.length();
    ser += algo.c_str();
    ser += params.length();
    ser += params.c_str();
    s->Process(logger::Manager::PacketIDs::Pkt_Algorithms, ser);
}

/// Instantiate a new interface to the list of NMEA0183 sentence message IDs that are expected to
/// be logged to the output data files on reception.

N0183IDStore::N0183IDStore(void)
: NVMFile("/N0183IDs.txt")
{
    if (Empty()) {
        // First load from NVM store
        StaticJsonDocument<128> doc;
        doc["count"] = 0;
        Set(doc);
    }
}

/// Add a new identifier to the list of those allowed for logging at the NMEA0183 interfaces.  The
/// algorithm here just stores the information provided, and doesn't interpret it, but it's unlikely
/// to go well unless the string contains a three-letter ID for a NMEA0183 message (e.g., "GGA", "RMC",
/// "GLL", "ZDA", "DBT", etc.)  No captialisation converion is done --- what you specify is what gets
/// checked.
///
/// @param msgid    String representation of the three-letter message IDs (space separated)

bool N0183IDStore::AddIDs(String const& msg_set)
{
    DynamicJsonDocument doc(BeginTransaction());
    if (doc.containsKey("error")) {
        // The internal JSON didn't convert
        Serial.printf("ERR: NMEA0183 filter update failed (%s/%s)\n",
            doc["error"]["message"].as<const char *>(), doc["error"]["detail"].as<const char*>());
        return false;
    }
    int count = doc["count"];
    int start_point = 0, split_point;

    //Serial.printf("DBG: NMEA0183 ID count currently %d\n", count);

    while ((split_point = msg_set.indexOf(' ', start_point)) >= 0) {
        String msgid = msg_set.substring(start_point, split_point);
        if (msgid.length() != 3) {
            Serial.printf("ERR: cannot add recognition ID of |%s|: must have three characters.\n",
                msgid.c_str());
        } else {
            doc["ids"][count] = msgid;
            ++count;
        }
        start_point = split_point + 1;
    }
    // At the end of the loop, the last sentence to be accepted is at start_point
    if ((msg_set.length() - start_point) != 3) {
        Serial.printf("ERR: cannot add recognition ID of |%s|: must have three characters.\n",
                msg_set.substring(start_point).c_str());
    } else {
        doc["ids"][count] = msg_set.substring(start_point);
        ++count;
    }
    doc["count"] = count;
    EndTransaction(doc);

    String temp(JSONRepresentation());
    //Serial.printf("DBG: Filter store now |%s|\n", temp.c_str());

    return true;
}

/// Reset the list of message IDs on the allowed list for logging; an empty list means "everything is
/// accepted".

void N0183IDStore::ClearIDList(void)
{
    StaticJsonDocument<128> doc;
    doc["count"] = 0;
    Set(doc);
}

/// Write the list of all allowed message IDs to an output WIBL-format binary file using
/// the specified @a Serialiser.
///
/// @param s    Pointer to the @a Serialiser associated with the required output file

void N0183IDStore::SerialiseIDs(Serialiser *s)
{
    DynamicJsonDocument doc(GetContents());

    int count = doc["count"];
    for (int n = 0; n < count; ++n) {
        Serialisable ser;
        String IDname = doc["ids"][n];
        ser += IDname.length();
        ser += IDname.c_str();
        s->Process(logger::Manager::PacketIDs::Pkt_NMEA0183ID, ser);
    }
}

/// Extract a list of all of the message IDs allowed for logging into a set so that the
/// logging code can readily check whether a given sentence is allowed.  Note that the
/// provided output set is cleared before being set up.
///
/// @param s    Reference for the set to store the message IDs.

void N0183IDStore::BuildSet(std::set<String>& s)
{
    DynamicJsonDocument doc(GetContents());

    int count = doc["count"];
    s.clear();
   for (int n = 0; n < count; ++n) {
        String IDname = doc["ids"][n];
        s.insert(IDname);
    }
}

}