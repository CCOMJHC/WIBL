 /*! @file AutoUpload.h
 * @brief Provide services to upload files directly from the logger a server in the cloud
 * 
 * For loggers that are connected in Station mode to a network with internet routing, this
 * provides the capability to touch an upload server to check that we're online, and then
 * start sending any available file on the logger to the server's upload endpoint.  The
 * expectation is that the server will provide a RESTful API to catch results coming in,
 * and check MD5s, etc. as required to confirm that the data made it to the cloud in good
 * order.
 *
 * Copyright (c) 2023, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#ifndef __AUTO_UPLOAD_H__
#define __AUTO_UPLOAD_H__

#include "LogManager.h"
#include "Configuration.h"

namespace net {

class UploadManager {
public:
    UploadManager(logger::Manager *logManager);
    ~UploadManager();

    void UploadCycle(void);

private:
    logger::Manager *m_logManager;      ///< Pointer for the LogManager to use for file information
    String          m_serverURL;        ///< Based URL for the server and port

    int32_t         m_timeout;          ///< Timeout for upload requests (ms)
    unsigned long   m_uploadInterval;   ///< Interval between upload events (ms)
    unsigned long   m_uploadDuration;   ///< Maximum duration for a single upload cycle (ms)
    
    unsigned long   m_lastUploadCycle;  ///< Timestamp for the last upload cycle (ms)

    bool            m_modeDropbox;      ///< Use Dropbox API instead of custom HTTPS server
    String          m_dropboxPath;      ///< Folder path on Dropbox (POSIX, leading /)
    String          m_dropboxToken;     ///< Dropbox OAuth2 bearer token

    bool ReportStatus(void);
    bool TransferFile(fs::FS& controller, uint32_t file_id);
    void DropboxUploadCycle(void);
    bool TransferFileDropbox(fs::FS& controller, uint32_t file_id);
    
};

/// In-memory test upload to Dropbox (path + token from config). Does not require auto-upload to be enabled.
bool TestDropboxUpload(String *detail_message = nullptr);

/// Normalize Dropbox access token from NVM/web (trim, UTF-8 BOM, embedded newlines) so it matches a compile-time token string.
void NormaliseDropboxAccessToken(String *token);

}

#endif
