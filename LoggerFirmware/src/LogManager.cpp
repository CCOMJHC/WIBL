/*!\file LogManager.cpp
 * \brief Implement log file management primitives
 *
 * This code implements the functionality to manage log files on the SD card in the logger.  This
 * includes writing to the files (including the console), making new files, removing old files, etc.
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

#include <string>
#include <list>
#include <stdint.h>
#include <utility>
#include "MD5Builder.h"
#include "LittleFS.h"
#include "LogManager.h"
#include "StatusLED.h"
#include "MemController.h"
#include "NVMFile.h"

namespace logger {

// We roll over files at approximately the following size, although we might go over
// a little depending on the size of the last block of data being sent to the file.
// This should be sufficiently large that we don't change files often, but not so large
// that losing a file would be a big problem (and take too long to transfer from the
// logger).  We also have a limited number of file numbers that are used before restarting,
// so we might not use all of the available SD card storage if the log size and maximum
// number of files are set too low.
//    The default configuration is 10MB for files, and 1,000 files, which results in about
// 9.8GB total; if the SD card is bigger than this, it might be appropriate to raise the
// limits (although you'd have to collect data for quite a file to get to this level).

const int MAX_LOG_FILE_SIZE = 10*1024*1024; ///< Maximum size of a single log file before swapping
const int MAX_CONSOLE_FILE_SIZE = 100*1024; ///< Maximum size of the console log before rotation
const int MAX_CONSOLE_LOGS = 3; ///< Maximum number of console logs to support before over-writing

Manager::MD5Hash::MD5Hash(void)
{
    memset(m_hash, 0, sizeof(uint8_t)*16);
}

String Manager::MD5Hash::Value(void) const
{
    char buffer[33];
    for (uint32_t i = 0; i < 16; ++i) {
        sprintf(buffer + i*2, "%02X", m_hash[i]);
    }
    buffer[32] = '\0';
    return String(buffer);
}

uint8_t const * const Manager::MD5Hash::Hash(void) const
{
    return m_hash;
}

bool Manager::MD5Hash::Empty(void) const
{
    for (uint32_t b = 0; b < 16; ++b)
        if (m_hash[b] != 0) return false;
    return true;
}

void Manager::MD5Hash::Set(uint8_t hash[16])
{
    memcpy(m_hash, hash, sizeof(uint8_t)*16);
}

Manager::Inventory::Inventory(Manager *manager, bool verbose)
: m_logManager(manager), m_verbose(verbose)
{
    m_filesize.resize(MaxLogFiles);
    m_hashes.resize(MaxLogFiles);
    m_uploadCount.resize(MaxLogFiles);
    Reinitialise();
}

Manager::Inventory::~Inventory(void)
{
}

bool Manager::Inventory::Reinitialise(void)
{
    uint32_t    *filenumbers = new uint32_t[MaxLogFiles];
    uint32_t    filecount = m_logManager->count(filenumbers);
    String      filename;
    Manager::MD5Hash emptyhash;

    if (m_verbose)
        Serial.printf("DBG: Reinitialising Inventory for %u objects.\n", filecount);
    for (uint32_t entry = 0; entry < MaxLogFiles; ++entry) {
        m_filesize[entry] = 0;
        m_hashes[entry] = emptyhash;
        m_uploadCount[entry] = 0;
    }

    for (uint32_t f = 0; f < filecount; ++f) {
        Update(filenumbers[f]);
    }

    delete[] filenumbers;
    
    return true;
}

bool Manager::Inventory::Lookup(uint32_t filenum, uint32_t& filesize, Manager::MD5Hash& hash, uint16_t& uploads)
{
    if (filenum >= MaxLogFiles) return false;
    if (m_filesize[filenum] == 0) return false;
    filesize = m_filesize[filenum];
    hash = m_hashes[filenum];
    uploads = m_uploadCount[filenum];
    return true;
}

bool Manager::Inventory::Update(uint32_t filenum, MD5Hash *filehash)
{
    Manager::MD5Hash hash;
    String filename;

    if (m_verbose)
        Serial.printf("DBG: Inventory update for file %u.\n", filenum);
    if (filenum >= MaxLogFiles) return false;
    m_logManager->enumerate(filenum, filename, m_filesize[filenum]);
    m_logManager->hash(filename, m_hashes[filenum]);
    if (m_verbose)
        Serial.printf("DBG: File |%s|, %u B, hash |%s|.\n", filename.c_str(), m_filesize[filenum], m_hashes[filenum].Value().c_str());
    if (filehash != nullptr) *filehash = m_hashes[filenum];
    return true;
}

void Manager::Inventory::RemoveLogFile(uint32_t filenum)
{
    if (filenum >= MaxLogFiles) return;
    m_filesize[filenum] = 0;
    m_hashes[filenum] = Manager::MD5Hash();
    m_uploadCount[filenum] = 0;
}

uint32_t Manager::Inventory::CountLogFiles(uint32_t filenumbers[MaxLogFiles])
{
    uint32_t filecount = 0;
    for (uint32_t entry = 0; entry < MaxLogFiles; ++entry) {
        if (m_filesize[entry] != 0) {
            filenumbers[filecount] = entry;
            ++filecount;
        }
    }
    return filecount;
}

uint32_t Manager::Inventory::CountLogFiles(void)
{
    uint32_t filecount = 0;
    for (uint32_t entry = 0; entry < MaxLogFiles; ++entry) {
        if (m_filesize[entry] != 0) ++filecount;
    }
    return filecount;
}

uint32_t Manager::Inventory::GetNextLogNumber(void)
{
    if (m_verbose)
        SerialiseCache(Serial);
    for (uint32_t entry = 0; entry < MaxLogFiles; ++entry) {
        if (m_filesize[entry] == 0) {
            return entry;
        }
    }
    return 0;
}

void Manager::Inventory::SerialiseCache(Stream& stream)
{
    stream.println("DBG: File Inventory Cache contents:");
    for (uint32_t entry = 0; entry < MaxLogFiles; ++entry) {
        if (m_filesize[entry] == 0) continue;
        stream.printf("[%4u] %8u %5u %s\n", entry,
            m_filesize[entry], m_uploadCount[entry], m_hashes[entry].Value().c_str());
    }
}

uint32_t Manager::Inventory::Filesize(uint32_t filenum)
{
    if (filenum >= MaxLogFiles || m_filesize[filenum] == 0)
        return 0;
    return m_filesize[filenum];
}

uint16_t Manager::Inventory::UploadCount(uint32_t filenum)
{
    if (filenum >= MaxLogFiles || m_filesize[filenum] == 0)
        return 0;
    return m_uploadCount[filenum];
}

uint16_t Manager::Inventory::IncrementUploadCount(uint32_t filenum)
{
    if (filenum >= MaxLogFiles || m_filesize[filenum] == 0)
        return 0;
    uint16_t rc = m_uploadCount[filenum]++;
    return rc;
}

#ifdef DEBUG_LOG_MANAGER

// When bringing up new hardware designs, it can be problematic if the hardware doesn't
// work, since the logger basically won't run without a log sink.  In order to allow for
// debugging, this implementation of the logger::Manager interface can be used, which
// will provide the same facilities as the full interface, but just throw away all of
// the data, and ignore all commands.

/// \brief Default constuctor
///
/// Construct the log manager.  Normally, the \a StatusLED object would be used to flash
/// one of the LEDs when data is being written to the SD card; in this dummy version,
/// it's simply ignored.
///
/// \param led  Pointer to the LED manager object for the board

Manager::Manager(StatusLED *led)
: m_led(led)
{
    Serial.println("INF: Starting dummy log manager - NO LOGGING WILL BE DONE.");
}

/// \brief Default destructor

Manager::~Manager(void)
{
    // Nothing to be done here
}

/// \brief Close the current log, and start a new one with the next number
///
/// Normally, this would close the current log (if there is one), and start the
/// next one in numeric sequence.  In this dummy version, it simply writes a debug message.

void Manager::StartNewLog(void)
{
    Serial.println("DBG: Call to start new log file");
}

/// \brief Close the current log file
///
/// Normally, this would close the current log file; in this dummy version, it simply writes
/// a debug message.

void Manager::CloseLogfile(void)
{
    Serial.println("DBG: Call to close log file.");
}

/// \brief Remove a log file from the SD card
///
/// Normally, this would remove a specific file from the SD card; in this dummy version,
/// it simply writes a debug message, and always returns True.
///
/// \param file_num The file number to attempt to remove
/// \return True (always)

boolean Manager::RemoveLogFile(const uint32_t file_num)
{
    Serial.printf("DBG: Call to remote log file %d.\n", file_num);
    return true;
}

/// \brief Remove all log files from the SD card
///
/// Normally, this would remove all available log files from the SD card; in this dummy version,
/// it simply writes a debug message.

void Manager::RemoveAllLogfiles(void)
{
    Serial.println("DBG: Call to remove all log files.");
}

/// \brief Count the number of log files on SD card, and provide their file reference numbers
///
/// Normally, this finds all of the log files on the SD card, counts the total number, and returns
/// the internal reference numbers that are being used so that the user can request more details
/// about a specific file later.  In this dummy version, it simply prints a debug message, and returns
/// zero.
///
/// \param filenumbers  Fixed size array (of \a MaxLogFiles) written with the internal reference numbers for the files
/// \return Total number of files available on the SD card

int Manager::CountLogFiles(int filenumbers[MaxLogFiles])
{
    Serial.println("DBG: Call to count log files; returning zero.");
    return 0;
}

/// \brief Determine the size and file name of the specified file
///
/// Normally, this would look up the specified file, and report the filename and size in
/// bytes; in this dummy version, it always reports "UNKNOWN" and a file size of zero.
///
/// \param lognumber    Number of the log to look up
/// \param filename     Reference for where to store the file's name
/// \param filesize     Reference for where to store the file's size

void Manager::EnumerateLogFile(int lognumber, String& filename, int& filesize)
{
    Serial.printf("DBG: Call to enumerate size of logfile %d.\n", lognumber);
    filename = "UNKNOWN";
    filesize = 0;
}

/// \brief Record a packet into the curent log file
///
/// Normally, this would write a \a Serialisable packet of data into the current log file
/// with the ID specified; in this dummy version, it simply prints a debug message.
///
/// \param pktID    Reference ID for the type of data being written
/// \param data     Reference for the data to write to the file

void Manager::Record(PacketIDs pktID, Serialisable const& data)
{
    Serial.printf("DBG: Call to serialise a packet with ID %d.\n", (uint32_t)pktID);
}

/// \brief Getter for the stream on which console information is being written
///
/// Normally, this would return the \a Stream reference for the file being used for console
/// messages (i.e., the permanent log for debug messages); in this dummy version, it simply
/// returns a reference for the hardware \a Serial interface, so messages go on to the
/// standard hardware output.
///
/// \return Reference for the current console output log file

Stream& Manager::Console(void)
{
    return Serial;
}

/// \brief Close the current console log file
///
/// Normally, this would close the console log file being used for permanent debug messages,
/// usually in preparation to stop logging; in this dummy version, it simply writes a 
/// debug message.

void Manager::CloseConsole(void)
{
    Serial.println("DBG: Call to close console log.");
}

/// \brief Output the contents of the console log file
///
/// Normally, this would serialise the console log file on the given stream; in this dummy
/// version, it simply writes a debug message.
///
/// \param output   \a Stream reference on with to write the contents of the console log

void Manager::DumpConsoleLog(Stream& output)
{
    Serial.println("DBG: Call to dump console log to stream.");
}

/// \brief Transfer a log file to a given \a Stream output
///
/// Normally, this is the default log file transfer mechanism (although a specialist version
/// for the WiFi interface also exists), and is used to get data off the logger; in this dummy
/// version, it simply reports a debug mesage with the number of the file requested.
///
/// \param file_num File number to transfer
/// \param output   Reference for a \a Stream on which to write the contents of the file.

void Manager::TransferLogFile(int file_num, Stream& output)
{
    Serial.printf("DBG: Call to transfer log file %d to stream.\n", file_num);
}

#else   // DEBUG_LOG_MANAGER

/// \brief Default constructor.
///
/// Set up for writing to logs, and also for the console log (same idea as a Unix-style
/// syslog).  The system uses the \a StatusLED object to flash one of the LED channels when
/// data is added to the current log file.
///
/// \param led  Pointer to the LED controller for the logger (external owner)

Manager::Manager(StatusLED *led, mem::MemController *storage)
: m_storage(storage), m_led(led), m_inventory(nullptr), m_noDataAlgEmitted(false)
{
#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
    m_consoleLog = m_storage->Controller().open("/console.log", FILE_APPEND);
#else
    m_consoleLog = m_storage->Controller().open("/console.log", FILE_WRITE);
#endif
    Syslog("info: booted logger, appending to console log.");
    Serial.println("info: started console log.");
}

/// \brief Default destructor.
///
/// This closes any current output log file, makes a note in the console log, and then shuts
/// everything down.

Manager::~Manager(void)
{
    if (m_outputLog)
        m_outputLog.close();
    if (m_inventory != nullptr)
        delete m_inventory;
    m_consoleLog.println("INFO: shutting down log manager under control.");
    m_consoleLog.close();
}

/// Start logging data to a new log file, generating the next log number in sequence that
/// hasn't been used within the current data set.  The numbers of the log files are used
/// starting with zero, so it's possible that the "next" log file has lower number than the
/// current one.  Note that this doesn't attempt to stop logging to the current file, if that's
/// happening, and there's only one pointer held for the file.  Therefore, if the system could
/// already be logging, you should call CloseLogfile() first.

void Manager::StartNewLog(void)
{
    Serial.println("Starting new log ...");
    m_currentFile = GetNextLogNumber();
    Serial.println(String("Log Number: ") + m_currentFile);
    String filename = MakeLogName(m_currentFile);
    Serial.println(String("Log Name: ") + filename);

    m_outputLog = m_storage->Controller().open(filename, FILE_WRITE);
    if (m_outputLog) {
        m_serialiser = new Serialiser(m_outputLog);
        logger::AlgoRequestStore algstore;
        algstore.SerialiseAlgorithms(m_serialiser);
        logger::MetadataStore metastore;
        metastore.SerialiseMetadata(m_serialiser);
        logger::N0183IDStore filterstore;
        filterstore.SerialiseIDs(m_serialiser);
        logger::ScalesStore scalesstore;
        scalesstore.SerialiseScales(m_serialiser);
        m_consoleLog.println(String("INFO: started logging to ") + filename);
    } else {
        m_serialiser = nullptr;
        m_consoleLog.println(String("ERR: Failed to open output log file as ") + filename);
    }
    
    m_consoleLog.flush();
    ResetDynamicAlgorithms();
    
    Serial.println("New log file initialisation complete.");
}

/// Close the current log file, and reset the Serialiser.  This ensures that the output log
/// file is safely closed, and no other object has reference to the file structure used
/// for it.

void Manager::CloseLogfile(void)
{
    delete m_serialiser;
    m_serialiser = nullptr;
    m_outputLog.close();
    if (m_inventory != nullptr) m_inventory->Update(m_currentFile);
}

/// Remove a specific log file from the SD card.  The specification of the filename, etc.
/// is abstracted out, so that only the file number is required to remove.  Note that the
/// code here doesn't check that the file exists before attempting to remove it.  Therefore,
/// it is possible that you might receive a failure code either because the file doesn't exist
/// or because the remove failed, and you can't tell the difference.
///
/// \param file_num Logical file number to remove.
/// \return True if the file was successfully removed, otherwise False

bool Manager::RemoveLogFile(uint32_t file_num)
{
    String filename = MakeLogName(file_num);
    bool rc = m_storage->Controller().remove(filename);

    if (rc) {
        m_consoleLog.printf("INFO: erased log file %d by user command.\n", file_num);
        if (m_inventory != nullptr) m_inventory->RemoveLogFile(file_num);
    } else {
        m_consoleLog.printf("ERR: failed to erase log file %d on user command.\n", file_num);
    }
    m_consoleLog.flush();
    
    return rc;
}

/// Remove all log files on the system.  Note that this includes the file that is currently
/// being written, if there is one ("all" means all).  The logger then automatically starts
/// a new log file immediately.

void Manager::RemoveAllLogfiles(void)
{
    uint32_t *filenumbers = new uint32_t[MaxLogFiles];

    CloseLogfile(); // All means all ...
    
    uint32_t filecount = CountLogFiles(filenumbers);
    uint32_t files_closed = 0;
    for (uint32_t f = 0; f < filecount; ++f) {
        String filename = MakeLogName(filenumbers[f]);
        Serial.printf("INFO: erasing log file: \"%s\".\n", filename.c_str());
        bool rc = m_storage->Controller().remove(filename);
        if (rc) {
            m_consoleLog.printf("INFO: erased log file \"%s\" by user command.\n", filename.c_str());
            ++files_closed;
            if (m_inventory != nullptr) m_inventory->RemoveLogFile(filenumbers[f]);
        } else {
            m_consoleLog.printf("ERR: failed to erase log file \"%s\" by user command.\n", filename.c_str());
        }
    }
    delete[] filenumbers;
    m_consoleLog.printf("INFO: erased %u log files of %u.\n", files_closed, filecount);
    m_consoleLog.flush();
    StartNewLog(); // We need to have something running for the logging effort!
}

/// Count the number of log files on the SD card, so that the client can enumerate them
/// and report to the user.
///
/// \param filenumbers  (Out) Array of the log file numbers on card
/// \return Number of files on the SD card

uint32_t Manager::CountLogFiles(uint32_t filenumbers[MaxLogFiles])
{
    uint32_t filecount;
    if (m_inventory != nullptr) {
        filecount = m_inventory->CountLogFiles(filenumbers);
    } else
        filecount = count(filenumbers);
    return filecount;
}

uint32_t Manager::CountLogFiles(void)
{
    uint32_t filecount;
    if (m_inventory != nullptr) {
        filecount = m_inventory->CountLogFiles();
    } else
        filecount = count(nullptr);
    return filecount;
}

/// Make a list of all of the files that exist on the SD card in the log directory, along with their
/// sizes.  This is generally used to work out which files can be transferred to the client application.
///
/// \param lognumber  Number of the file to look up
/// \param filename   Name of the file
/// \param filesize   Size of the specified file in bytes (or 0 if file doesn't exist)
/// \param uploadcount Number of times the file has attempted an upload

void Manager::EnumerateLogFile(uint32_t lognumber, String& filename, uint32_t& filesize, MD5Hash& filehash,
    uint16_t& uploadcount)
{
    filename = MakeLogName(lognumber);

    if (m_inventory != nullptr) {
        m_inventory->Lookup(lognumber, filesize, filehash, uploadcount);
    } else {
        File f = m_storage->Controller().open(filename);
        if (f) {
            filesize = f.size();
        } else {
            filesize = 0;
        }
        filehash = MD5Hash(); // We're not going to rehash the file just for this!
        uploadcount = 0;
    }
}

/// Record a packet into the current output file, and check on size (making a new file if
/// required).
///
/// \param pktID    Reference number to save with the packet
/// \param data Serialisable or derived object with data to write

void Manager::Record(PacketIDs pktID, Serialisable const& data)
{
    m_serialiser->Process((uint32_t)pktID, data);
    m_led->TriggerDataIndication();
    if (m_outputLog.size() > MAX_LOG_FILE_SIZE) {
        m_consoleLog.printf("INFO: Cycling to next log file after %d B to current log file.\n", m_outputLog.size());
        m_consoleLog.flush();
        CloseLogfile();
        StartNewLog();
    }
}

void Manager::Syslog(String const& message)
{
    m_consoleLog.println(message);
    m_consoleLog.flush();
    RotateConsoleLogs(); // This is maybe a little much, but does ensure we don't exceed the max size.
}

void Manager::CloseConsole(void)
{
    m_consoleLog.close();
}

void Manager::HashFile(uint32_t file_num, MD5Hash& filehash)
{
    if (m_inventory != nullptr) {
        m_inventory->Update(file_num, &filehash);
    } else {
        String filename = MakeLogName(file_num);
        hash(filename, filehash);
    }
}

uint16_t Manager::IncrementUploadCount(uint32_t file_num)
{
    uint16_t rc;

    if (m_inventory != nullptr) {
        rc = m_inventory->IncrementUploadCount(file_num);
    } else {
        Serial.println("ERR: upload counts are only managed when an inventory object is running");
        rc = 0;
    }
    return rc;
}

void Manager::AddInventory(bool verbose)
{
    m_inventory = new Inventory(this, verbose);
}

bool Manager::WriteSnapshot(const char *name, String const& contents, String& url)
{
    // Since the /logs directory is served out as the second static website, we need to
    // put the snapshots into the same directory so they can be seen.  This causes some
    // complexity in running through the directory (e.g., when making an Inventory from
    // scratch), but avoids other issues.
    url = String("/logs/") + name;
    File f = m_storage->Controller().open(url, FILE_WRITE);
    if (f) {
        f.print(contents);
        f.close();
        return true;
    }
    return false;
}

/// Reset all indicators used to ensure that any dynamic algorithms are only emitted once
/// into the output data stream.
///

void Manager::ResetDynamicAlgorithms(void)
{
    m_noDataAlgEmitted = false;
}

void Manager::EmitNoDataReject(void)
{
    if (m_noDataAlgEmitted) return;
    logger::AlgoRequestStore store;
    store.SerialiseSingleAlgorithm("nodatareject", "phase=raw", m_serialiser);
    m_noDataAlgEmitted = true;
}

/// Generate a logical file number for the next log file to be written.  This operates
/// by walking the current log directory counting files that exist until the upper
/// limit is reached.  The log directory is created if it does not already exist, and any
/// standard file that appears in the wrong location is removed.  If all log files exist,
/// the code re-uses the first file number, over-writing the log file.  The "next" log
/// file is the first file number that is attempted where a prior log file is not existant
/// on SD card.  This means that the "next" log file might have lower logical number
/// than the current or previous one.
///
/// \return Logical file number for the next log file to write.

uint32_t Manager::GetNextLogNumber(void)
{
    if (!m_storage->Controller().exists("/logs")) {
        m_storage->Controller().mkdir("/logs");
    }
    File dir = m_storage->Controller().open("/logs");
    if (!dir.isDirectory()) {
        dir.close();
        m_storage->Controller().remove("/logs");
        m_storage->Controller().mkdir("/logs");
    }

    if (m_inventory != nullptr) {
        return m_inventory->GetNextLogNumber();
    }
    
    uint32_t lognum = 0;
    while (lognum < MaxLogFiles) {
        if (m_storage->Controller().exists(MakeLogName(lognum))) {
            ++lognum;
        } else {
            break;
        }
    }
    if (MaxLogFiles == lognum)
        lognum = 0; // Re-use the first created
    return lognum;
}

/// Generate a string version for a logical file number.  This converts the logical number
/// into a filename that can be used to open the file.  This assumes that the log file
/// directory already exists.
///
/// \param log_num  Logical file number to generate
/// \return String with full path to the log file to create

String Manager::MakeLogName(uint32_t log_num)
{
    String filename("/logs/wibl-raw.");
    filename += log_num;
    return filename;
}

/// Generate a log number given a filename that is presumably a log file.  This converts
/// the extension of the filename into a number, if possible, but returns -1 if the contents
/// of the extension are non-integer.

int32_t Manager::ExtractLogNumber(String const& filename)
{
    if (filename.indexOf(String("wibl-raw")) < 0) {
        // This is not a log file, so converting the extension would not be useful
        return -1;
    }
    // Since we know that it's a log file (test above) then we know that it must have an
    // extension that can be converted into an integer (since they are only made by
    // MakeLogName() here, and therefore always have the same format)
    return filename.substring(filename.indexOf('.')+1).toInt();
}

/// Output the contents of the system console log to something that implements the Stream
/// interface.
///
/// \param output   Anything Stream-like that supports the write() interface.

void Manager::DumpConsoleLog(Stream& output)
{
    m_consoleLog.close();
    m_consoleLog = m_storage->Controller().open("/console.log", FILE_READ);
    while (m_consoleLog.available()) {
        output.write(m_consoleLog.read());
    }
    m_consoleLog.close();
    m_consoleLog = m_storage->Controller().open("/console.log", FILE_APPEND);
}

/// Rotate the console log file(s) if the currently open log file is larger than the maximum
/// size alowed.  The number of old files retained in the rotation, and the maximum size, are
/// controlled by compile-time constants (at the top of LogManager.cpp).
///
/// \return N/A

void Manager::RotateConsoleLogs(void)
{
    if (m_consoleLog.size() > MAX_CONSOLE_FILE_SIZE) {
        m_consoleLog.close();
        for (int target = MAX_CONSOLE_LOGS-1; target >= 2; --target) {
            String target_file = "/console." + String(target);
            String source_file = "/console." + String(target-1);
            if (m_storage->Controller().exists(source_file))
                m_storage->Controller().rename(source_file.c_str(), source_file.c_str());
        }
        m_storage->Controller().rename("/console.log", "/console.1");
        m_consoleLog = m_storage->Controller().open("/console.log", FILE_APPEND);
    }
}

/// Generic interface to transfer a given log file to any output that supports the Stream
/// interface.  This is not necessarily the fastest way to do this, but it is the most
/// general.  Output protocol is to write the file size as a uint32_t first, then the
/// binary data from the file in order.
///
/// \param file_num Number of the log file to transfer
/// \param output   Anything Stream-like that supports the write() interface.

void Manager::TransferLogFile(uint32_t file_num, MD5Hash const& filehash, Stream& output)
{
    String filename(MakeLogName(file_num));
    Serial.println("Transferring file: " + filename);
    File f = m_storage->Controller().open(filename, FILE_READ);
    uint32_t bytes_transferred = 0;
    uint32_t file_size = f.size();
    
    // We need to send the hash and file size first, so that the other end knows when to stop
    // listening, and go back to ASCII mode.
    uint32_t hash_size = MD5Hash::ObjectSize();
    output.write((const uint8_t*)&hash_size, sizeof(uint32_t));
    output.write(filehash.Hash(), MD5Hash::ObjectSize());
    output.write((const uint8_t*)&file_size, sizeof(uint32_t));
    
    unsigned long start = millis();
    while (f.available()) {
        output.write(f.read());
        ++bytes_transferred;
        if ((bytes_transferred % 1024) == 0) {
            Serial.printf("Transferred %u bytes.\n", bytes_transferred);
        }
    }
    unsigned long end = millis();
    unsigned long duration = (end - start)/1000;
    f.close();
    Serial.printf("Sent %u B in %lu s.\n", bytes_transferred, duration);
}

uint32_t Manager::count(uint32_t *filenumbers)
{
    uint32_t file_count = 0;
    File logdir = m_storage->Controller().open("/logs");
    File entry = logdir.openNextFile();

    while (entry) {
        // Because we can store snapshots of configuration information in the /logs directory
        // (so that they can be seen through the webserver's static website for download), we
        // need to count only the valid log files in the directory.
        int32_t lognumber = ExtractLogNumber(String(entry.name()));
        if (lognumber >= 0) {
            if (filenumbers != nullptr) filenumbers[file_count] = lognumber;
            ++file_count;
        }
        entry.close();
        entry = logdir.openNextFile();
    }
    logdir.close();
    return file_count;
}

void Manager::enumerate(uint32_t lognumber, String& filename, uint32_t& filesize)
{
    filename = MakeLogName(lognumber);
    File f = m_storage->Controller().open(filename);
    if (f) {
        filesize = f.size();
    } else {
        filesize = 0;
    }
}

void Manager::hash(String const& filename, MD5Hash& hash)
{
    MD5Builder md5;
    File f = m_storage->Controller().open(filename, "r");
    md5.begin();
    md5.addStream(f, 2*MAX_LOG_FILE_SIZE);
    f.close();
    md5.calculate();
    uint8_t buffer[16];
    md5.getBytes(buffer);
    hash.Set(buffer);
}

#endif

}
