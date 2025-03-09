/*! \file WiFiAdapter.h
 *  \brief Interface for the WiFi adapter on the module, and a factory to abstract the object
 *
 * In order to get to a decent speed for data transfer, we need to use the WiFi interface rather
 * than the BLE.  This provides the interface to abstract the details of this away.
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

#ifndef __WIFI_ADAPTER_H__
#define __WIFI_ADAPTER_H__

#include <WiFi.h>
#include "ArduinoJson.h"
#include "LogManager.h"

/// \class WiFiAdapter
/// \brief Abstract base class for WiFi access.
///
/// A number of different potential method to provide WiFi access are possible with different implementations
/// of WIBL, so this class is provided to allow this detail to be abstracted for the rest of the code.  This
/// assumes that there's a basic start/stop model, along with facilities to test for data waiting, etc.

class WiFiAdapter {
public:
    /// \brief Default destructor to allow for sub-classes.
    virtual ~WiFiAdapter(void) {}
    
    /// \brief Start the WiFi adapter and access point.
    bool Startup(void);
    /// \brief Shut down the WiFi adapter and access point.
    void Shutdown(void);

    /// \brief Extract the first string from the WiFi client (usually a command string).
    String ReceivedString(void);
    
    /// \brief Manage the transfer of a log file to the client, given the filename.
    bool TransferFile(String const& filename, uint32_t filesize, logger::Manager::MD5Hash const& filehash);

    /// \brief Accumulate messages to be returned to the client for the current transaction
    void AddMessage(String const& message);

    /// \brief Replace the entire message to be returned to the client for the current transaction
    void SetMessage(DynamicJsonDocument const& message);

    enum HTTPReturnCodes {
        OK              = 200,  // The request succeeded
        BADREQUEST      = 400,  // The server cannot or will not process the reqeuest
        NOTFOUND        = 404,  // Resource not found
        IMATEAPOT       = 418,  // Really ... not expected to be used, but good for the yucks.
        SERVERERR       = 500,  // Internal server error
        NOTIMPLEMENTED  = 501,  // Request not supported by the server
        UNAVAILABLE     = 503   // Server not ready to handle request

    };

    /// \brief Set the status code to return to the client
    void SetStatusCode(HTTPReturnCodes status);

    /// \brief Transmit the current set of accumulated messages to the client
    bool TransmitMessages(void);
    
    enum WirelessMode {
        ADAPTER_STATION,    ///< Join the configured network when activated
        ADAPTER_SOFTAP      ///< Create the configured network when activated
    };
    /// \brief Set up wireless mode for the adapter (i.e., AP or STA)
    static void SetWirelessMode(WirelessMode mode);
    /// \brief Determine the wireless mode currently configures
    static WirelessMode GetWirelessMode(void);

    void RunLoop(void);
    
private:
    /// \brief Sub-class implementation of code to start the interface.
    virtual bool start(void) = 0;
    /// \brief Sub-class implementation of code to stop the interface.
    virtual void stop(void) = 0;
    
    /// \brief Sub-class implementation of code to read the first string from the buffer.
    virtual String readBuffer(void) = 0;
    
    /// \brief Sub-class implementation of code to send a log file to the client.
    virtual bool sendLogFile(String const& filename, uint32_t filesize, logger::Manager::MD5Hash const& filehash) = 0;

    /// \brief Sub-class implementation of code to accumulate messages for transmission
    virtual void accumulateMessage(String const& message) = 0;

    /// \brief Sub-class implementation of code to replace message for transmission
    virtual void setMessage(DynamicJsonDocument const& message) = 0;

    /// \brief Sub-class implementation of code to set the status code for the transaction
    virtual void setStatusCode(HTTPReturnCodes status_code) = 0;

    /// \brief Sub-class implementation of code to transmit messages (and complete transaction)
    virtual bool transmitMessages(void) = 0;

    virtual void runLoop(void) = 0;
};

/// \class WiFiAdapterFactory
/// \brief Factory object to generate a WiFiAdapter for the particular hardware module in use
///
/// This provides a single static method to generate an appropriate WiFi interface for the hardware
/// associated with the specific WIBL implementation.

class WiFiAdapterFactory {
public:
    /// \brief Constructor for a WiFiAdapter of the appropriate implementation.
    static WiFiAdapter *Create(void);
};

#endif
