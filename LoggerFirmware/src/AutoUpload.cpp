/*! @file AutoUpload.cpp
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

#include "Arduino.h"
#include "base64.h"

#include "WiFiClientSecure.h"
#include "HTTPClient.h"
#include "ArduinoJson.h"

#include "AutoUpload.h"
#include "Configuration.h"
#include "Status.h"

namespace net {

UploadManager::UploadManager(logger::Manager *logManager)
: m_logManager(logManager), m_timeout(-1), m_lastUploadCycle(0)
{
    String server, port, upload_interval, upload_duration, timeout;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_SERVER_S, server);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_PORT_S, port);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_INTERVAL_S, upload_interval);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_DURATION_S, upload_duration);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_TIMEOUT_S, timeout);
    if (server.isEmpty()) {
        m_logManager = nullptr;
        return;
    }
    if (port.isEmpty()) port = String("80");
    m_serverURL = String("https://") + server + ":" + port + "/";
    m_uploadInterval = static_cast<unsigned long>(upload_interval.toDouble() * 1000.0);
    m_uploadDuration = static_cast<unsigned long>(upload_duration.toDouble() * 1000.0);
    m_timeout = static_cast<int32_t>(timeout.toDouble() * 1000.0);
}

UploadManager::~UploadManager(void)
{

}

void UploadManager::UploadCycle(void)
{
    unsigned long start_time = millis();
    if ((start_time - m_lastUploadCycle) < m_uploadInterval) return; // Not time yet ...
    m_lastUploadCycle = start_time;

    if (m_logManager->CountLogFiles() == 0) {
        return; // Nothing to transfer, so no need to get in touch ...
    }

    if (!ReportStatus()) {
        // Failed to report status ... means the server's not there, or we're not connected
        Serial.printf("DBG: UploadManager::UploadCycle failed to report status at %d ms elapsed.\n",
            m_lastUploadCycle);
        return;
    }

    for (auto fileNumber : m_logManager->GetLogFileNumbers()) {
        bool success = TransferFile(m_logManager->FileSystem(), fileNumber);
        if (success) {
            // File transferred to the server successfully, so we can delete locally
            m_logManager->RemoveLogFile(fileNumber);
        } else {
            // File did not transfer, so we update the upload attempt metadata and move on
        }
        unsigned long current_elapsed = millis();
        if ((current_elapsed - start_time) > m_uploadDuration) {
            // We're only allowed to update for a specific length of time (since otherwise we'll
            // halt all logging!)
            break;
        }
    }
}

class SecureClient {
public:
    SecureClient(void)
    {
        m_wifi = new WiFiClientSecure();
        if (!m_wifi) {
            return;
        }
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_CERT_S, m_cert);
        if (m_cert.length() == 0) {
            delete m_wifi;
            m_wifi = nullptr;
        } else {
            m_wifi->setCACert(m_cert.c_str());
        }
    }

    ~SecureClient(void)
    {
        delete m_wifi;
    }

    WiFiClientSecure *Client(void) const
    {
        return m_wifi;
    }

private:
    WiFiClientSecure    *m_wifi;
    String              m_cert;
};

String AuthHeader(void)
{
    String logger_uuid, upload_token, upload_header;

    if (logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_MODULEID_S, logger_uuid) &&
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_TOKEN_S, upload_token) &&
        !upload_token.isEmpty()) {
        String auth_token = logger_uuid + ":" + upload_token;
        upload_header = String("Basic ") + base64::encode(auth_token);
    } else {
        upload_header = "";
    }
    return upload_header;
}

bool UploadManager::ReportStatus(void)
{
    DynamicJsonDocument status(logger::status::CurrentStatus(m_logManager));
    String url = m_serverURL + "checkin";
    String status_json;
    serializeJson(status, status_json);

    SecureClient wifi;
    HTTPClient client;
    bool rc = false; // By default ...
    String auth_header(AuthHeader());

    client.setConnectTimeout(m_timeout);
    if (client.begin(*wifi.Client(), url)) {
        client.setTimeout(static_cast<uint16_t>(m_timeout));
        if (!auth_header.isEmpty()) {
            client.addHeader(String("Authorization"), auth_header);
        }
        int http_rc;
        if ((http_rc = client.POST(status_json)) == HTTP_CODE_OK) {
            // 200 OK is expected; in the future, there might also be some other information
            rc = true;
        } else {
            // Didn't get expected response from server
            Serial.printf("DBG: UploadManager::ReportStatus: error code %d = |%s|\n",
                http_rc, client.errorToString(http_rc).c_str());
            rc = false;
        }
    }
    client.end();

    return rc;
}

bool UploadManager::TransferFile(fs::FS& controller, uint32_t file_id)
{
    String                      file_name;
    uint32_t                    file_size;
    logger::Manager::MD5Hash    file_hash;
    uint16_t                    upload_count;

    m_logManager->EnumerateLogFile(file_id, file_name, file_size, file_hash, upload_count);
    File f = controller.open(file_name, FILE_READ);
    if (!f) {
        Serial.printf("ERR: UploadManager::TransferFile failed to open file |%s| for auto-upload.\n",
            file_name.c_str());
        return false;
    }

    SecureClient wifi;
    HTTPClient client;
    bool rc = false; // By default ...

    String digest_header(String("md5=") + file_hash.Value());
    String auth_header(AuthHeader());
    String url(m_serverURL + "update");

    client.setConnectTimeout(m_timeout);
    if (client.begin(*wifi.Client(), url)) {
        client.setTimeout(static_cast<uint16_t>(m_timeout));
        int http_rc;

        client.addHeader(String("Digest"), digest_header);
        client.addHeader(String("Content-Type"), String("application/octet-stream"), false, true);
        if (!auth_header.isEmpty()) {
            client.addHeader(String("Authorization"), auth_header);
        }

        Serial.printf("DBG: UploadManager::TransferFile POST starting ...\n");
        if ((http_rc = client.sendRequest("POST", &f, file_size)) == HTTP_CODE_OK) {
            Serial.printf("DBG: UploadManager::TransferFile POST completed with 200OK\n");
            // If we get a 200OK then the response body should be a JSON document with information
            // about the upload (successful or unsuccessful).
            String payload = client.getString();
            DynamicJsonDocument response(1024);
            deserializeJson(response, payload);
            if (response.containsKey("status")) {
                if (response["status"] == "success") {
                    // Since the file is now transferred, delete from the logger
                    // (but note that we don't do that here ...)
                    rc = true;
                } else if (response["status"] == "failure") {
                    // Since the transfer failed, mark upload attempt and move on
                    // (but note that we don't do that here ...)
                    rc = false;
                } else {
                    // Invalid response!
                    Serial.printf("DBG: UploadManager::TransferFile invalid status from server |%s|\n",
                        response["status"].as<const char*>());
                    rc = false; // Because we don't know if it worked or not ...
                }
            } else {
                // Invalid response!
                Serial.printf("DBG: UploadManager::TransferFile invalid response from server |%s|\n",
                    payload.c_str());
                rc = false; // Because we don't know if it worked or not ...
            }
        } else {
            // Didn't get expected response from server
            Serial.printf("DBG: UploadManager::TransferFile: error code %d = |%s|\n",
                http_rc, client.errorToString(http_rc).c_str());
            rc = false;
        }
    }
    f.close();
    client.end();

    return rc;
}

};
