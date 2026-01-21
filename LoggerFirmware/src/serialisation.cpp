/*!\file serialisation.cpp
 * \brief Implement simple serialisation for SD file storage
 *
 * This implements the interface for serialisation of storage into
 * an SDLib::File of binary packet data.  This is not intended to be
 * very automatic (on the order of Boost::Serialization), but just
 * enough to get packets into the file
 *
 * Copyright (c) 2019, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include <stdint.h>
#include "serialisation.h"
#include "N2kLogger.h"
#include "N0183Logger.h"
#include "IMULogger.h"
#include "Configuration.h"

/// Constructor for a serialisable buffer of data.  The buffer is allocated to the \a size_hint but
/// can grow as new data is added if required.  Expanding a buffer is expensive, so it's wise to
/// set the size of the buffer appropriately at construction, if the nominal size is know.
///
/// \param size_hint    Starting buffer size

Serialisable::Serialisable(uint32_t size_hint)
{
    m_buffer = (uint8_t*)malloc(sizeof(uint8_t)*size_hint);
    m_bufferLength = size_hint;
    m_nData = 0;
}

/// Destructor for the serialisation buffer.  This simply frees the buffer allocated to avoid leaks.

Serialisable::~Serialisable(void)
{
    free(m_buffer); // Must exist if we get to here
}

/// Make sure that there is sufficient space in the buffer to include the data that's about to
/// be added to the buffer, and re-allocate if not.  Re-allocation is expensive, so you want to
/// avoid this if possible by setting the size hint on the constructor.
///
/// \param s    Size in bytes of the data that's about to be added.

void Serialisable::EnsureSpace(size_t s)
{
    if ((m_bufferLength - m_nData) < s) {
        uint32_t target_buffer_size = std::max(2*m_bufferLength, m_nData + s);
        uint8_t *new_buffer = (uint8_t *)malloc(sizeof(uint8_t)*target_buffer_size);
        memcpy(new_buffer, m_buffer, sizeof(uint8_t)*m_nData);
        free(m_buffer);
        m_buffer = new_buffer;
        m_bufferLength = target_buffer_size;
    }
}

/// Serialise a byte into the buffer.
///
/// \param b    Unsigned byte to be added to the buffer.

void Serialisable::operator+=(uint8_t b)
{
    EnsureSpace(sizeof(uint8_t));
    m_buffer[m_nData++] = b;
}

/// Serialise a half-word to the buffer.
///
/// \param h    Half-word (16-bit unsigned) to be added to the buffer.

void Serialisable::operator+=(uint16_t h)
{
    EnsureSpace(sizeof(uint16_t));
    uint8_t *data = (uint8_t*)&h;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
}

/// Serialise a signed half-word to the buffer.
///
/// \param h    Half-word (16-bit signed) to be added to the buffer.

void Serialisable::operator+=(int16_t h)
{
    EnsureSpace(sizeof(int16_t));
    uint8_t *data = (uint8_t*)&h;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
}

/// Serialise a word (32-bit) to the buffer.
///
/// \param w    Word (32-bit unsigned) to be added to the buffer

void Serialisable::operator+=(uint32_t w)
{
    EnsureSpace(sizeof(uint32_t));
    uint8_t *data = (uint8_t*)&w;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
    m_buffer[m_nData++] = data[2];
    m_buffer[m_nData++] = data[3];
}

/// Serialise a double-word (64-bit) to the buffer
///
/// \param ul   Double-word (64-bit unsigned) to be added to the buffer

void Serialisable::operator+=(uint64_t ul)
{
    EnsureSpace(sizeof(uint64_t));
    uint8_t *data = (uint8_t*)&ul;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
    m_buffer[m_nData++] = data[2];
    m_buffer[m_nData++] = data[3];
    m_buffer[m_nData++] = data[4];
    m_buffer[m_nData++] = data[5];
    m_buffer[m_nData++] = data[6];
    m_buffer[m_nData++] = data[7];
}

/// Serialise a single-precision floating point (32-bit) to the buffer
///
/// \param f    Single-precision float (32-bit) to be added to the buffer.

void Serialisable::operator+=(float f)
{
    EnsureSpace(sizeof(float));
    uint8_t *data = (uint8_t*)&f;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
    m_buffer[m_nData++] = data[2];
    m_buffer[m_nData++] = data[3];
}

/// Serialise a double-precision floating point (64-bit) to the buffer
///
/// \param d    Double-precision float (64-bit) to be added to the buffer

void Serialisable::operator+=(double d)
{
    EnsureSpace(sizeof(double));
    uint8_t *data = (uint8_t*)&d;
    m_buffer[m_nData++] = data[0];
    m_buffer[m_nData++] = data[1];
    m_buffer[m_nData++] = data[2];
    m_buffer[m_nData++] = data[3];
    m_buffer[m_nData++] = data[4];
    m_buffer[m_nData++] = data[5];
    m_buffer[m_nData++] = data[6];
    m_buffer[m_nData++] = data[7];
}

/// Serialise an array of characters to the output buffer (i.e., a C-style, zero
/// terminated, string).
///
/// \param p    Pointer to the array to add

void Serialisable::operator+=(const char *p)
{
    EnsureSpace(strlen(p));
    const char *src = p;
    while (*src != '\0') {
        m_buffer[m_nData++] = *src++;
    }
}

/// Serialise a buffer of bytes to the output buffer, with given length.
///
/// \param buffer   Pointer to the buffer to copy
/// \param n        Length of the buffer in bytes

void Serialisable::deposit(uint8_t *buffer, uint32_t n)
{
    EnsureSpace(n);
    memcpy(m_buffer + m_nData, buffer, n);
    m_nData += n;
}

/// Constructor for the serialiser, which writes \a Serialisable objects to file.  The file has
/// to be opened in binary mode in order for this to work effectively.
///
/// \param file Reference for the file on which the data should be serialised.

Serialiser::Serialiser(File& file)
: m_file(file)
{
    uint16_t major, minor, patch;
    
    Serialisable version(22);
    
    version += (uint16_t)SerialiserVersionMajor;
    version += (uint16_t)SerialiserVersionMinor;
    
    nmea::N2000::Logger::SoftwareVersion(major, minor, patch);
    version += major;
    version += minor;
    version += patch;
    
    nmea::N0183::Logger::SoftwareVersion(major, minor, patch);
    version += major;
    version += minor;
    version += patch;

    imu::Logger::SoftwareVersion(major, minor, patch);
    version += major;
    version += minor;
    version += patch;

    rawProcess(0, version);

    Serialisable meta(255);
    String name, identifier;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_SHIPNAME_S, name);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_MODULEID_S, identifier);
    meta += name.length();
    meta += name.c_str();
    meta += identifier.length();
    meta += identifier.c_str();

    rawProcess(logger::Manager::PacketIDs::Pkt_Metadata, meta);

    DynamicJsonDocument json_setup(logger::ConfigJSON::ExtractConfig(true));
    String json_str;
    serializeJson(json_setup, json_str);
    Serialisable setup(json_str.length() + sizeof(size_t));
    setup += json_str.length();
    setup += json_str.c_str();

    rawProcess(logger::Manager::PacketIDs::Pkt_Setup, setup);
}

/// Private method to actually write the buffer to file.  This avoids cross-checks on the payload ID
/// specified so that we can write the ID 0 packet for the serialiser version.
///
/// \param payload_id   ID number to write to file in order to identify what's coming next
/// \param payload          Buffer handler to be written to file
///
/// \return True if the packet was successfully written to file, otherwise False

bool Serialiser::rawProcess(uint32_t payload_id, Serialisable const& payload)
{
    m_file.write((const uint8_t*)&payload_id, sizeof(uint32_t));
    m_file.write((const uint8_t*)&payload.m_nData, sizeof(uint32_t));
    m_file.write((const uint8_t*)payload.m_buffer, sizeof(uint8_t)*payload.m_nData);
    m_file.flush();
    return true;
}

/// User-level method to write the buffer to file.  The payload ID number specified has to be
/// greater than zero (which is reserved for internal use).
///
/// \param payload_id   ID number to write to file in order to identify what's coming next
/// \param payload          Buffer hanlder to be written to file
///
/// \return True if the packet was written to to file, otherwise False

bool Serialiser::Process(uint32_t payload_id, Serialisable const& payload)
{
    if (0 == payload_id) {
        // Reserved for version packet at the start of the file
        return false;
    }
    
    return rawProcess(payload_id, payload);
}

String Serialiser::SoftwareVersion(void)
{
    return String(SerialiserVersionMajor) + "." + String(SerialiserVersionMinor);
}
