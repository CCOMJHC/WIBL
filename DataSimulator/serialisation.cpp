/*!\file serialisation.cpp
 * \brief Implement simple serialisation
 *
 * This implements the interface for serialisation of data packets into
 * the file format used by the hardware logger, so that sample files can
 * be generated without having to have hardware available.
 *
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

#include <stdint.h>
#include <stdlib.h>
#include <cstdio>
#include <string>
#include "serialisation.h"
#include "Writer.h"

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
        uint8_t *new_buffer = (uint8_t *)malloc(sizeof(uint8_t)*(2*m_bufferLength));
        memcpy(new_buffer, m_buffer, sizeof(uint8_t)*m_nData);
        free(m_buffer);
        m_buffer = new_buffer;
        m_bufferLength = 2*m_bufferLength;
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

/// Constructor for the serialiser, which writes \a Serialisable objects to file.  The file has
/// to be opened in binary mode in order for this to work effectively.
///
/// \param file Reference for the file on which the data should be serialised.

Serialiser::Serialiser(FILE *file)
: m_file(file)
{
    uint16_t major, minor, patch;
    
    Serialisable version(16);
    
    version += (uint16_t)SerialiserVersionMajor;
    version += (uint16_t)SerialiserVersionMinor;
    
    major = 1; minor = patch = 0;
    version += major;
    version += minor;
    version += patch;
    
    version += major;
    version += minor;
    version += patch;
    
    version += major;
    version += minor;
    version += patch;

    rawProcess(0, version);
	
	Serialisable meta(255);
	std::string name("Gulf Surveyor");
	std::string identifier("WIBL-Simulator");
	meta += static_cast<uint32_t>(name.size());
	meta += name.c_str();
	meta += static_cast<uint32_t>(identifier.size());
	meta += identifier.c_str();
	
	rawProcess(nmea::logger::Writer::PacketIDs::Pkt_Metadata, meta);
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
    fwrite((const uint8_t*)&payload_id, sizeof(uint32_t), 1, m_file);
    fwrite((const uint8_t*)&payload.m_nData, sizeof(uint32_t), 1, m_file);
    fwrite((const uint8_t*)payload.m_buffer, sizeof(uint8_t), payload.m_nData, m_file);
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
