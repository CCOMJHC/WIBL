/*! \file NVMFile.h
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

#ifndef __NVMFILE_H__
#define __NVMFILE_H__

#include <set>
#include "Arduino.h"
#include "ArduinoJson.h"
#include "serialisation.h"

namespace logger {

class Invalid {};

/// \class NVMFile
/// \brief Implementatin of code to read/write a non-volatile file
///
/// A number of modules in the firmware need to provide the facility of storing an arbitrary
/// number of strings in the non-volatile memory on the logger.  This class provides a means
/// to centralise that structure.  Note that this class is not generally exposed to the rest
/// of the code, which interacts via the interface classes to either read or write, but not
/// both together.

class NVMFile {
public:
    /// \brief Default constructor, opening the file in the appropriate mode
    ///
    /// This opens the file specified in the appropriate mode.
    ///
    /// \param filename Backing filename to use for string storage
    /// \param mode     File read mode to use

    NVMFile(String const& filename);

    /// \brief Default destructor
    ///
    /// Close the backing file, and then delete the controller for it.

    ~NVMFile(void);

    /// @brief Check whether the contents of the object are valid
    ///
    /// This checks whether the underlying representation of the object is not empty, indicating
    /// the something valid was read from the file representation.
    ///
    /// @return True if the object has a valid configuration, otherwise false
    bool Valid(void) const { return !m_contents.isEmpty(); }

    /// @brief Generate a string representation of the underlying object, optionally indented
    String JSONRepresentation(bool indented = false) const;

    /// @brief Generate a JsonDocument representation of the underlying object
    DynamicJsonDocument GetContents(void) const;

protected:
    /// @brief Start a transaction to update the contents of the object
    DynamicJsonDocument BeginTransaction(void);
    /// @brief End a transaction that updated the contents of the object
    size_t EndTransaction(DynamicJsonDocument& dest);
    /// @brief Indicate that the contents of the object have been changed
    void MarkChanged(void) { m_changed = true; }
    /// @brief Replace the contents of the objects with a JSON document
    void Set(JsonDocument& doc);
    /// @brief Replace the contents of the objects with a minified JSON representation
    void Set(String const& doc);
    /// @brief Check whether the internal representation of the object is empty
    bool Empty(void) { return m_contents.length() <= 2; }
    /// @brief Remove the contents of the object
    void Clear(void) { m_contents = String("{}"); m_changed = true; }
    /// @brief Estimate the target capacity for the JsonDocument
    size_t EstimateCapacity(String const& minified);

private:
    String  m_backingStore; ///< Name of the file in the NVM to use for the object
    String  m_contents;     ///< Minified string representation of the object
    bool    m_changed;      ///< Flag: true if the contents have been changed since reading
};

/// \class MetadataStore
/// \brief Specialisation of NVMFile for metadata storage
///
/// The logger can be used to store a JSON string with the platform-specific metadata
/// for the ship collecting the data.  This is written into the data files, allowing
/// the post-processing software to set up detailled, rather than general metadata
/// for the ship.
///     Note that the class does not attempt to check what's in the metadata, and just
/// stores what's given, and replicates it into the data.  What it should be, however,
/// is valid JSON in the format specified in IHO B-12 (Crowdsourced Bathymetry Working
/// Group guidelines) for the "platform" element, surrounded by a standard "{ ... }"
/// braces to make it a valid JSON document on its own (otherwise it can't be converted
/// into a Python dictionary using the standard JSON library).
///     Since the metadata string is stored as a single line in a file in non-volatile
/// memory, it's important that the JSON is all in one line, rather than being formatted
/// with spaces/tabs/carriage returns, etc.

class MetadataStore : public NVMFile {
public:
    /// \brief Default constructor
    MetadataStore(void);

    /// \brief Store the specified string as the platform metadata element
    void SetMetadata(String const& meta);

    /// \brief Write the metadata element string into the output file associated with the \a Serialiser
    void SerialiseMetadata(Serialiser *ser);
};

/// \class ScalesStore
/// \brief Specialisation of NVMFile for sensor scale factors
///
/// The logger can have multiple sensors that store their data in binary (or binary-coded) form,
/// needing scale factors applied before they become either usable floating-point data, or converted
/// into the right units.  This store allows the code to provide one or more JSON fragments of
/// scale factors to be stored for transmission into the output data files whenever a file is
/// started.

class ScalesStore : public NVMFile {
public:
    /// \brief Default constructor.
    ScalesStore(void);

    /// \brief Add (or update) a scale parameter in a given instrument group
    void AddScale(String const& group, String const& name, double value);

    void AddScales(String const& group, const char *names[], double *values, int count);

    /// \brief Clear all scales groups from memory
    void ClearScales(void);

    /// \brief Serialise the scales JSON into the output file associated with the \a Serialiser provided
    void SerialiseScales(Serialiser *ser);
};

/// \class AlgoRequestStore
/// \brief Specialisation of NVMFile for algorithm request storage
///
/// The logger can store a list of algorithms that should be applied to the data in post-processing
/// in order to correct any problems that might be generated by the specific circumstances of the
/// ship collecting the data.  There's no guarantee that the post-processing implementation will
/// have the algorithms, or that it will run them, but at least the request is made.
///     The algorithms are specified by a name and a parameter string.  There is no interpretation on
/// how the parameter string should be formatted, since only the algorithm needs to read it.

class AlgoRequestStore : public NVMFile {
public:
    /// \brief Default constructor.
    AlgoRequestStore(void);

    /// \brief Add an algorithm to the list, optionally resetting the list
    void AddAlgorithm(String const& alg_name, String const& alg_params);

    /// \brief Reset the list of known algorithms
    void ClearAlgorithmList(void);

    /// \brief Write the list of all requested algorithms to the log file associated with \a Serialiser
    void SerialiseAlgorithms(Serialiser *s);

    /// \brief Generate and emit a single algorithm by name
    void SerialiseSingleAlgorithm(String const& algorithm, String const& parameters, Serialiser *s);
};

/// \class N0183IDStore
/// \brief Specialisation of NVMFile for NMEA0183 allowed ID storage
///
/// In order to optimise the storage on the logger, the user can specify a list of the NMEA0183 message IDs
/// (the three-letter names that occur after the talked identifier in the messages) that should be written to
/// the data log files; all messages not in the list are ignored (except if there's an empty list, which
/// implicitly means that all messages should be accepted for logging).
///     The algorithm here does not check the message IDs provided for validity, case sensitivity, etc., and
/// filters against what the user provides.  The user is responsible for making sure that the names provided
/// actually make sense.

class N0183IDStore : public NVMFile {
public:
    /// \brief Default constructor
    N0183IDStore(void);

    /// \brief Add another message ID to the accepted list
    bool AddIDs(String const& msgid);

    /// \brief Reset the accepted list to empty
    void ClearIDList(void);

    /// \brief Write the list of accepted message IDs into the data log file associated with \a Serialiser
    void SerialiseIDs(Serialiser *s);

    /// \brief Read all of the message IDs and build the structure required for checking incoming messages
    void BuildSet(std::set<String>& s);
};

/// \class N2000PGNStore
/// \brief Specialisation of NVMFile for NMEA2000 extra-effort PGN storage
///
/// The NMEA2000 logger automatically converts a sub-set of all messages to internal formats and writes
/// them to the output stream, but there are potentially many messages other than the core information
/// that we store that could be useful in other applications.  This object allows the user to specify a
/// list of PGNs in the NMEA2000 stream that should be packaged (in their received binary form) for later
/// interpretation, in addition to the core set that are automatically processed.
///     The algorithm here does not check the PGNs provided for validity, and accepts only decimal versions
/// of the PGNs.  The user is responsible to making sure that they really do want the PGNs specified, since
/// inappropriate specification could result in very large file output sizes.

class N2000PGNStore : public NVMFile {
public:
    /// \brief Default constructor
    N2000PGNStore(void);

    /// \brief Add a set of PGNs (space separated) to the storage list
    bool AddPGNs(String const& pgns);

    /// \brief Indicate whether all PGNs should be written to binary
    void WriteAll(bool write_all);

    /// \brief Reset the list of PGNs to empty
    void ClearPGNList(void);

    /// \brief Write the list of PGNs that are being stored into the associated \a Serialiser
    void SerialisePGNs(Serialiser *s);

    /// \brief Read all of the PGNs and build the structure required for checking incoming messages
    void BuildSet(std::set<int>& s, bool& write_all);

private:
    int convert_pgn(String const& s, int start_point, int end_point);
};

}

#endif
