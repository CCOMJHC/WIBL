/*!\file serialisation.h
 * \brief Simple serialisation of basic types for file storage
 *
 * As part of the logging process, we have to put together binary packets
 * of the input data for storage.  In order to provide some central capability
 * for this, the Serialisable type is used to encapsulate a packet of data to
 * be written, and the Serialiser class can be used to provide the overall
 * encapsulation of data type, length byte, checksum, etc. as required.
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

#ifndef __SERIALISATION_H__
#define __SERIALISATION_H__

#include <stdint.h>
#include <string>
#include <memory>

// GNU G++ defines these as macros, but we can undef them: https://bugzilla.redhat.com/show_bug.cgi?id=130601
#undef major
#undef minor

const int SerialiserVersionMajor = 1; ///< Major version number for the serialiser
const int SerialiserVersionMinor = 4; ///< Minor version number for the serialiser

/// \class Serialisable
/// \brief Provide encapsulation for data to be written to store
///
/// This object provides an expandable buffer that can be used to hold data in preparation
/// for writing to SD card.  The buffer can be pre-allocated to a nominal size before starting
/// in order to avoid having to re-allocate the buffer during preparation (which is slow).

class Serialisable {
public:
    /// \brief Default constructor for the buffer object
    Serialisable(uint32_t size_hint = 255);
    /// \brief Default destructor
    ~Serialisable(void);
    
    /// \brief Add a single byte to the output buffer
    void operator+=(uint8_t b);
    /// \brief Add a 2-byte half-word to the output buffer
    void operator+=(uint16_t w);
    /// \brief Add a 4-byte word to the output buffer
    void operator+=(uint32_t dw);
    /// \brief Add an 8-byte double word to the output buffer
    void operator+=(uint64_t ul);
    /// \brief Add a single-precision floating point number to the ouptut buffer
    void operator+=(float f);
    /// \brief Add a double-precision floating point number of the output buffer
    void operator+=(double d);
    /// \brief Add an array of characters (C-style string) to the output buffer
    void operator+=(const char *p);
    
    /// \brief Inspector for the number of bytes of data in the buffer (not the total buffer length)
    uint32_t BufferLength(void) const { return m_nData; }
    /// \brief Inspector for the buffer contents
    uint8_t const *Buffer(void) const { return m_buffer; }
    
private:
    friend class Serialiser;
    uint8_t     *m_buffer;      ///< Pointer to the buffer being assembled
    uint32_t    m_bufferLength; ///< Total size of the buffer currently allocated
    uint32_t    m_nData;        ///< Number of bytes currently used in the buffer
    
    /// \brief Ensure that there is sufficient space in the buffer to add an object of the given size
    void EnsureSpace(size_t s);
};

/// \class Version
/// \brief POD to hold information on a major.minor.patch version number

class Version {
public:
    uint16_t major; ///< Major version of the entity
    uint16_t minor; ///< Minor version of the entity
    uint16_t patch; ///< Patch level of the entity

    /// \brief Simple constructor for the POD to allow for uniform construction
    ///
    /// This simply sets up the data points from the user's input
    ///
    /// \param maj  Major version of the entity
    /// \param min  Minor version of the entity
    /// \param pat  Patch level of the entity

    Version(uint16_t maj, uint16_t min, uint16_t pat)
    : major(maj), minor(min), patch(pat) {}
};

/// \enum PayloadID
/// \brief Identification numbers for the packets known to the serialiser
///
/// Each packet written into the output file must have an identification number written
/// into the data stream (and the packet size) in order to be interpretable without looking
/// backwards into the file.  This enum provides those identification numbers.  Note that
/// these must match those in the Wiki documentation in the repository, and there is no
/// mechanism to enforce this.  Very Bad Things (TM) will happen if this is not the case.

enum PayloadID {
    Pkt_Version = 0,            ///< Versioning information for the serialiser and NMEA handlers
    Pkt_SystemTime = 1,         ///< NMEA2000 SystemTime packets
    Pkt_Attitude = 2,           ///< NMEA2000 Attitude (roll, pitch, yaw) packets
    Pkt_Depth = 3,              ///< NMEA2000 Depth packets
    Pkt_COG = 4,                ///< NMEA2000 Course over Ground packets
    Pkt_GNSS = 5,               ///< NMEA2000 Primary navigation (GNSS) packets
    Pkt_Environment = 6,        ///< NMEA2000 Environmental (temperature, humidity, pressure) packets
    Pkt_Temperature = 7,        ///< NMEA2000 Temperature packets
    Pkt_Humidity = 8,           ///< NMEA2000 Humidity packets
    Pkt_Pressure = 9,           ///< NMEA2000 Pressure packets
    Pkt_NMEAString = 10,        ///< NMEA1083 sentences (of any kind)
    Pkt_LocalIMU = 11,          ///< Motion data from the local IMU on the logger
    Pkt_Metadata = 12,          ///< Identification (name, ID) metadata for the logger
    Pkt_AlgorithmRequest = 13,  ///< List of algorithms that the logger would like the processing to run
    Pkt_JSONMetadata = 14,      ///< Arbitrary JSON-structured metadata to B.12 standard to add to the output
    Pkt_NMEA0183Filter = 15,    ///< List of packets to record from NMEA0183 inputs (by default all)
    Pkt_SensorScales = 16,      ///< Scale factors to apply to RawIMU values (and other sensors)
    Pkt_RawIMU = 17,            ///< Raw measurements from local IMU (needs scaling factors applied)
    Pkt_Setup = 18,             ///< JSON-format string with the active configuration when the file was started
    Pkt_NMEA2000PGNS = 19,      ///< JSON string for list of integer PGNs to record (as binary) from NMEA2000
    Pkt_N2kBinary = 20          ///< The binary representation of a NMEA2000 packet
};

/// \class Serialiser
/// \brief Carry out the serialisation of an object
///
/// This object provides a simple abstract interface for writing a \a Serialisable object
/// into an output stream, the specifics of which are provided by the specialised sub-class.
/// The \a payload_id and a size word are automatically added to the output packets.  A
/// packet with the serialiser version information is written to each file when it is opened
/// so that readers can check on the expected format of the remainder of the file.

class Serialiser {
public:
    /// \brief Default constructor
    Serialiser(Version& n2k, Version& n1k, Version& imu, std::string const& logger_name, std::string const& logger_id);
    
    /// \brief Default destructor
    virtual ~Serialiser(void);
    
    /// \brief Write the payload to file, with header block
    bool Process(PayloadID payload_id, std::shared_ptr<Serialisable> payload);

private:
    std::shared_ptr<Serialisable>   m_version;     ///< Version information to be written
    std::shared_ptr<Serialisable>   m_metadata;    ///< Metadata information to be written
    
    /// \brief Payload serialiser without user-level validity checks
    virtual bool rawProcess(PayloadID payload_id, std::shared_ptr<Serialisable> payload) = 0;
};

/// \class StdSerialiser
/// \brief Serialisation to a standard C FILE pointer

class StdSerialiser : public Serialiser {
public:
    /// \brief Default contructor, simply holding the information for the future
    StdSerialiser(FILE *f, Version& n2k, Version& n1k, Version& imu, std::string const& logger_name, std::string const& logger_id)
    : Serialiser(n2k, n1k, imu, logger_name, logger_id), m_file(f) {}
    
private:
    FILE *m_file;   ///< File pointer through which to serialise

    /// \brief Concrete implementation of the code to write packets to the file.
    bool rawProcess(PayloadID payload_id, std::shared_ptr<Serialisable> payload);
};

#endif
