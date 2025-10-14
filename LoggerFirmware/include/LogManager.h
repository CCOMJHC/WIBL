/*!\file LogManager.h
 * \brief Objects to manage the log files, and writing data to them
 *
 * In order to ensure that multiple different loggers can write into the same output file, this
 * code centralises all of the access for log files, making new files, writing to them, removing
 * them as required, etc.
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

#ifndef __LOG_MANAGER_H__
#define __LOG_MANAGER_H__

#include <vector>
#include <stdint.h>
#include <Arduino.h>
#include "FS.h"
#include "serialisation.h"
#include "StatusLED.h"
#include "MemController.h"

namespace logger {

// The maximum number of log files here is relatively arbitrary, although depending on the file
// system being used on the SD card, it might be problematic for the number to be above 1,000
// (since the number is the file extension).  If this becomes a problem, it would be necessary to
// change the way that the file names are constructed (in MakeLogName() in this case, but possibly
// also elsewhere).  A likely scenario for this would be if there was a very large SD card being
// used, where the total file space (MaxLogFiles * MAX_LOG_FILE_SIZE) was significantly smaller
// than the size of the card.  With the default size of 10MB files and 1,000 files, this is about
// 9.8GB.

const int MaxLogFiles = 1000; ///< Maximum number of log files that we will create

/// \class Manager
/// \brief Handle log file access, creation, and deletion
///
/// This encapsulates the requirements for log file creation, access, and deletion.  This includes
/// log file naming and serialisation object numbering.

class Manager {
public:
    /// \brief Default constructor
    Manager(StatusLED *led, mem::MemController *storage);
    /// \brief Default destructor
    ~Manager(void);
    
    /// \brief Start a new log file, with the next available number
    void StartNewLog(void);

    /// \brief Close the current logfile (use judiciously!)
    void CloseLogfile(void);
    
    /// \brief Remove a given log file from the SD card
    boolean RemoveLogFile(const uint32_t file_num);

    /// \brief Remove all log files currently available (use judiciously!)
    void RemoveAllLogfiles(void);

    /// \brief Count the number of log files on the system
    uint32_t CountLogFiles(uint32_t filenumbers[MaxLogFiles]);
    /// \brief Count the number of log files on the system
    uint32_t CountLogFiles(void);
    
    class MD5Hash {
    public:
        MD5Hash(void);
        String Value(void) const;
        uint8_t const * const Hash(void) const;
        bool Empty(void) const;
        void Set(uint8_t hash[16]);
        static uint32_t ObjectSize(void) { return sizeof(uint8_t)*16; }
    
    private:
        uint8_t m_hash[16];
    };

    /// \brief Extract information on a single log file
    void EnumerateLogFile(uint32_t lognumber, String& filename, uint32_t& filesize, MD5Hash& filehash,
        uint16_t& uploadcount);
    
    /// \enum PacketIDs
    /// \brief Symbolic definition for the packet IDs used to serialise the messages from NMEA2000
    enum PacketIDs {
        Pkt_SystemTime = 1,     ///< Real-time information from GNSS (or atomic clock)
        Pkt_Attitude = 2,       ///< Platform roll, pitch, yaw
        Pkt_Depth = 3,          ///< Observed depth, offset, and depth range
        Pkt_COG = 4,            ///< Course and speed over ground
        Pkt_GNSS = 5,           ///< Position information and metrics
        Pkt_Environment = 6,    ///< Temperature, Humidity, and Pressure
        Pkt_Temperature = 7,    ///< Temperature and source
        Pkt_Humidity = 8,       ///< Humidity and source
        Pkt_Pressure = 9,       ///< Pressure and source
        Pkt_NMEAString = 10,    ///< A generic NMEA0183 string, in raw format
        Pkt_LocalIMU = 11,      ///< Logger's on-board IMU
        Pkt_Metadata = 12,      ///< Logger identification information
        Pkt_Algorithms = 13,    ///< Algorithms and parameters to apply to the data, by preference
        Pkt_JSON = 14,          ///< JSON metadata element to pass on to cloud processing
        Pkt_NMEA0183ID = 15,    ///< Acceptable NMEA0183 sentence ID for filtering
        Pkt_SensorScales = 16,  ///< Scale factors for any sensors that will be recorded raw
        Pkt_RawIMU = 17,        ///< Raw store for logger's on-board IMU
        Pkt_Setup = 18          ///< Setup JSON string for entire configuration
    };
    
    /// \brief Write a packet into the current log file
    void Record(PacketIDs pktID, Serialisable const& data);
    /// \brief Provide a pointer to the current serialiser
    Serialiser *OutputChannel(void) { return m_serialiser; }
    /// @brief Provide a reference for the file system being used to store files
    fs::FS& FileSystem(void) { return m_storage->Controller(); }
    
    /// \brief Call to log on the console log
    void Syslog(String const& message);
    /// \brief Close the console file prior to shutdown
    void CloseConsole(void);
    /// \brief Dump console log to serial
    void DumpConsoleLog(Stream& output);
    /// \brief Send a log file to a particular output stream
    void TransferLogFile(uint32_t file_num, MD5Hash const& filehash, Stream& output);

    void HashFile(uint32_t file_num, MD5Hash& hash);
    uint16_t IncrementUploadCount(uint32_t file_num);
    void AddInventory(bool verbose = false);
    void EmitNoDataReject(void);

    bool WriteSnapshot(const char *name, String const& contents, String& url);

private:
    /// \class Inventory
    /// \brief Manage an inventory of the files currently on the SD card
    ///
    /// Although it is possible to keep track of log files by trawling the file system, this can be
    /// relatively expensive if there are lots of files on the logger.  In order to speed things up,
    /// this object can be used to maintain a cache of the files on the logger, listing their size and
    /// MD5 checksum.

    class Inventory {
    public:
        Inventory(Manager *manager, bool verbose = false);
        ~Inventory(void);

        bool Reinitialise(void);
        bool Lookup(uint32_t filenum, uint32_t& filesize, MD5Hash& hash, uint16_t& uploads);
        bool Update(uint32_t filenum, MD5Hash *hash = nullptr);
        void RemoveLogFile(uint32_t filenum);
        uint32_t CountLogFiles(uint32_t filenumbers[MaxLogFiles]);
        uint32_t CountLogFiles(void);
        uint32_t GetNextLogNumber(void);
        uint32_t Filesize(uint32_t filenum);
        uint16_t UploadCount(uint32_t filenum);
        uint16_t IncrementUploadCount(uint32_t filenum);

        void SerialiseCache(Stream& stream);

    private:
        Manager                 *m_logManager;
        bool                    m_verbose;
        std::vector<uint32_t>   m_filesize;
        std::vector<MD5Hash>    m_hashes;
        std::vector<uint16_t>   m_uploadCount;
    };
    mem::MemController  *m_storage; ///< Controller for the storage to use
    File        m_consoleLog;       ///< File on which to write console information
    File        m_outputLog;        ///< Current output log file on the SD card
    uint32_t    m_currentFile;      ///< Filenumber of the currently open file
    Serialiser  *m_serialiser;      ///< Object to handle serialisation of data
    StatusLED   *m_led;             ///< Pointer for status (data event) handling
    Inventory   *m_inventory;       ///< Cache for file information, if available

    bool m_noDataAlgEmitted;    ///< Flag for whether the "NoDataReject" algorithm packet has been emitted
    
    /// \brief Find the next log number in sequence that doesn't already exist
    uint32_t GetNextLogNumber(void);
    /// \brief Make a filename for the given log file number
    String  MakeLogName(uint32_t lognum);
    /// \brief Extract a log number from a filename (if valid)
    int32_t ExtractLogNumber(String const& filename);
    /// \brief Count the number of log files on the system
    uint32_t count(uint32_t *filenumbers);
    /// \brief Extract information on a single log file
    void enumerate(uint32_t lognumber, String& filename, uint32_t& filesize);
    /// \brief Generate a hash for a given file 
    void hash(String const& filename, MD5Hash& hash);
    /// \brief Rotate the console log files, if necessary
    void RotateConsoleLogs(void);
    /// \brief Reset the indicators for dynamic algorithm requests
    void ResetDynamicAlgorithms(void);
};

}

#endif
