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

#include <WiFi.h>
#include "WiFiClientSecure.h"
#include "HTTPClient.h"
#include "ArduinoJson.h"
#include "esp_heap_caps.h"

#include "AutoUpload.h"
#include "Configuration.h"
#include "Status.h"

namespace {

/// Claim and release the largest internal free block so it is one contiguous run (helps mbedTLS peak).
void ConsolidateLargestInternalBlock(void)
{
    size_t const n = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
    if (n > 4096u) {
        void *const p = heap_caps_malloc(n, MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
        if (p != nullptr) {
            heap_caps_free(p);
        }
    }
}

/// Idle long enough for lwIP/WebServer to release buffers; consolidate heap before/after.
void PrepareInternalHeapForTls(void)
{
    ConsolidateLargestInternalBlock();
    for (int n = 0; n < 20; ++n) {
        yield();
        delay(25);
    }
    ConsolidateLargestInternalBlock();
    for (int n = 0; n < 15; ++n) {
        yield();
        delay(25);
    }
}

/// When HTTPClient returns a negative code, mbedTLS/WiFi errors are in WiFiClientSecure; read before http.end().
void AppendTlsFailureDetail(String *detail, WiFiClientSecure &client)
{
    if (detail == nullptr) {
        return;
    }
    char errbuf[112];
    errbuf[0] = '\0';
    client.lastError(errbuf, sizeof(errbuf));
    size_t const largest = heap_caps_get_largest_free_block(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL);
    unsigned const heap_now = ESP.getFreeHeap();
    *detail += String("; largest_internal_block=") + String(static_cast<unsigned>(largest)) + " B, free_heap=" + String(heap_now) + " B";
    if (errbuf[0] != '\0') {
        *detail += String("; mbedTLS: ") + errbuf;
    }
    if (strstr(errbuf, "X509") != nullptr) {
        *detail += " Handshake parses the server certificate chain (extra RAM on top of TLS record buffers). Reboot and run the test before other web pages, use USB serial \"dropbox test\" only, or retry later.";
    } else {
        *detail += "; TLS handshake needs a large contiguous RAM block (heap fragmentation often breaks this).";
    }
}

/// Same shape as working Arduino sample: {"path":"...","mode":"...","autorename":false,"mute":false,"strict_conflict":false}
String MakeDropboxFilesUploadApiArg(String const& dropboxPath, char const *mode)
{
    String pathEscaped;
    pathEscaped.reserve(dropboxPath.length() + 4U);
    for (unsigned i = 0; i < dropboxPath.length(); ++i) {
        char c = dropboxPath.charAt(i);
        if (c == '\\' || c == '"') {
            pathEscaped += '\\';
        }
        pathEscaped += c;
    }
    return String("{\"path\":\"") + pathEscaped + "\",\"mode\":\"" + mode +
           "\",\"autorename\":false,\"mute\":false,\"strict_conflict\":false}";
}

} // namespace

namespace net {

void NormaliseDropboxAccessToken(String *token)
{
    if (token == nullptr || token->isEmpty()) {
        return;
    }
    token->trim();
    if (token->length() >= 3U && static_cast<uint8_t>(token->charAt(0)) == 0xEFU &&
        static_cast<uint8_t>(token->charAt(1)) == 0xBBU && static_cast<uint8_t>(token->charAt(2)) == 0xBFU) {
        token->remove(0, 3);
    }
    token->replace("\r", "");
    token->replace("\n", "");
    token->trim();
    if (token->startsWith("Bearer ") || token->startsWith("bearer ")) {
        *token = token->substring(7);
        token->trim();
    }
    if (token->length() >= 2U) {
        char const a = token->charAt(0);
        char const b = token->charAt(token->length() - 1U);
        if ((a == '"' && b == '"') || (a == '\'' && b == '\'')) {
            *token = token->substring(1, token->length() - 1);
            token->trim();
        }
    }
}


UploadManager::UploadManager(logger::Manager *logManager)
: m_logManager(logManager), m_timeout(-1), m_lastUploadCycle(0), m_modeDropbox(false)
{
    String server, port, upload_interval, upload_duration, timeout;
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_SERVER_S, server);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_PORT_S, port);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_INTERVAL_S, upload_interval);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_DURATION_S, upload_duration);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_TIMEOUT_S, timeout);

    bool want_dropbox = false;
    logger::LoggerConfig.GetConfigBinary(logger::Config::CONFIG_UPLOAD_DROPBOX_B, want_dropbox);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DROPBOX_PATH_S, m_dropboxPath);
    logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_DROPBOX_TOKEN_S, m_dropboxToken);
    m_dropboxPath.trim();
    m_dropboxToken.trim();
    NormaliseDropboxAccessToken(&m_dropboxToken);
    m_modeDropbox = want_dropbox && m_dropboxToken.length() > 0 && m_dropboxPath.length() > 0;
    if (m_modeDropbox && !m_dropboxPath.startsWith("/"))
        m_dropboxPath = "/" + m_dropboxPath;

    bool have_server = !server.isEmpty();
    if (!m_modeDropbox && !have_server) {
        m_logManager = nullptr;
        return;
    }
    if (have_server) {
        if (port.isEmpty()) port = String("80");
        m_serverURL = String("https://") + server + ":" + port + "/";
    }
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

    if (m_modeDropbox) {
        DropboxUploadCycle();
        return;
    }

    if (!ReportStatus()) {
        // Failed to report status ... means the server's not there, or we're not connected
        Serial.printf("DBG: UploadManager::UploadCycle failed to report status at %d ms elapsed.\n",
            m_lastUploadCycle);
        return;
    }
    DynamicJsonDocument files(logger::status::GenerateFilelist(m_logManager));
    int filecount = files["files"]["count"].as<int>();
    for (int n = 0; n < filecount; ++n) {
        uint32_t file_id = files["files"]["detail"][n]["id"].as<uint32_t>();
        if (TransferFile(m_logManager->FileSystem(), file_id)) {
            // File transferred to the server successfully, so we can delete locally
            m_logManager->RemoveLogFile(file_id);
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

namespace {

String LogBasename(String const& path)
{
    int slash = path.lastIndexOf('/');
    if (slash < 0 || slash >= (int)path.length() - 1)
        return path;
    return path.substring(slash + 1);
}

}

void UploadManager::DropboxUploadCycle(void)
{
    unsigned long start_time = millis();
    DynamicJsonDocument files(logger::status::GenerateFilelist(m_logManager));
    int filecount = files["files"]["count"].as<int>();
    for (int n = 0; n < filecount; ++n) {
        uint32_t file_id = files["files"]["detail"][n]["id"].as<uint32_t>();
        if (TransferFileDropbox(m_logManager->FileSystem(), file_id)) {
            m_logManager->RemoveLogFile(file_id);
        }
        unsigned long current_elapsed = millis();
        if ((current_elapsed - start_time) > m_uploadDuration) {
            break;
        }
    }
}

bool UploadManager::TransferFileDropbox(fs::FS& controller, uint32_t file_id)
{
    String file_name;
    uint32_t file_size;
    logger::Manager::MD5Hash file_hash;
    uint16_t upload_count;

    m_logManager->EnumerateLogFile(file_id, file_name, file_size, file_hash, upload_count);
    File f = controller.open(file_name, FILE_READ);
    if (!f) {
        Serial.printf("ERR: UploadManager::TransferFileDropbox failed to open |%s|.\n",
            file_name.c_str());
        return false;
    }

    const size_t sz = f.size();
    if (sz == 0U) {
        f.close();
        return false;
    }

    String dropbox_file = m_dropboxPath;
    if (!dropbox_file.endsWith("/"))
        dropbox_file += "/";
    dropbox_file += LogBasename(file_name);

    String const argHeader = MakeDropboxFilesUploadApiArg(dropbox_file, "overwrite");

    PrepareInternalHeapForTls();
    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    const char *uploadUrl = "https://content.dropboxapi.com/2/files/upload";
    http.setConnectTimeout(m_timeout);
    http.setTimeout(static_cast<uint16_t>(m_timeout));
    bool ok = false;
    if (http.begin(client, uploadUrl)) {
        http.addHeader("Authorization", String("Bearer ") + m_dropboxToken);
        http.addHeader("Content-Type", "application/octet-stream");
        http.addHeader("Dropbox-API-Arg", argHeader);
        int code = http.sendRequest("POST", &f, sz);
        if (code == 200) {
            ok = true;
        } else {
            Serial.printf("DBG: Dropbox upload HTTP %d: %s\n", code, http.getString().c_str());
        }
    }
    http.end();
    f.close();
    return ok;
}

bool TestDropboxUpload(String *detail_message)
{
    using namespace logger;

    String token;
    String path;
    LoggerConfig.GetConfigString(Config::CONFIG_DROPBOX_TOKEN_S, token);
    LoggerConfig.GetConfigString(Config::CONFIG_DROPBOX_PATH_S, path);
    token.trim();
    path.trim();
    NormaliseDropboxAccessToken(&token);
    if (token.isEmpty() || path.isEmpty()) {
        if (detail_message) {
            *detail_message = "Set Dropbox token (this page) and dropboxPath (configure page).";
        }
        return false;
    }
    if (!path.startsWith("/")) {
        path = "/" + path;
    }

    String timeout_s;
    LoggerConfig.GetConfigString(Config::CONFIG_UPLOAD_TIMEOUT_S, timeout_s);
    int32_t timeout_ms = static_cast<int32_t>(timeout_s.toDouble() * 1000.0);
    if (timeout_ms < 1000) {
        timeout_ms = 15000;
    }

    if (WiFi.status() != WL_CONNECTED) {
        if (detail_message) {
            *detail_message = "WiFi not connected (use Station with internet).";
        }
        return false;
    }

    String remote = path;
    if (!remote.endsWith("/")) {
        remote += "/";
    }
    remote += "wibl-dropbox-test.txt";

    String payload = String("WIBL Dropbox connectivity test\nFirmware: ") + FirmwareVersion()
        + "\nElapsed ms: " + String(millis()) + "\n";

    String const argHeader = MakeDropboxFilesUploadApiArg(remote, "overwrite");

    PrepareInternalHeapForTls();
    WiFiClientSecure client;
    client.setInsecure();

    HTTPClient http;
    const char *uploadUrl = "https://content.dropboxapi.com/2/files/upload";
    http.setConnectTimeout(timeout_ms);
    http.setTimeout(static_cast<uint16_t>(timeout_ms));
    if (!http.begin(client, uploadUrl)) {
        if (detail_message) {
            *detail_message = "HTTP client init failed";
        }
        return false;
    }
    http.addHeader("Authorization", String("Bearer ") + token);
    http.addHeader("Content-Type", "application/octet-stream");
    http.addHeader("Dropbox-API-Arg", argHeader);

    int code =
        http.sendRequest("POST", reinterpret_cast<uint8_t *>(const_cast<char *>(payload.c_str())), payload.length());
    String resp = http.getString();
    if (code < 0) {
        Serial.printf("DBG: Dropbox test: free_heap=%u largest_internal_block=%u B (before end)\n",
            static_cast<unsigned>(ESP.getFreeHeap()),
            static_cast<unsigned>(heap_caps_get_largest_free_block(MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL)));
    }
    if (detail_message) {
        *detail_message = String("HTTP ") + String(code) + ": " + resp;
        if (code < 0) {
            AppendTlsFailureDetail(detail_message, client);
        } else if (code == 401) {
            if (resp.indexOf("invalid_access_token") >= 0) {
                *detail_message +=
                    " Dropbox says invalid_access_token: the value on the logger is not a valid access token (wrong string, truncated, or expired). "
                    "In Dropbox App Console: Permissions → enable files.content.write; Settings → Generated access token → Generate. "
                    "Paste the token only (no Bearer prefix, no quotes). Set it again with auth dropbox or the web form.";
            } else {
                *detail_message += " Token rejected (401). Use an OAuth2 access token from the app (not app secret). "
                                   "Enable scope files.content.write. https://www.dropbox.com/developers/apps";
            }
        }
    }
    http.end();

    if (code == HTTP_CODE_OK) {
        if (detail_message) {
            *detail_message =
                String("OK: uploaded ") + remote + " (" + String(payload.length()) + " bytes)";
        }
        Serial.printf("INF: Dropbox test upload succeeded -> %s\n", remote.c_str());
        return true;
    }
    Serial.printf("ERR: Dropbox test upload failed (HTTP %d)\n", code);
    return false;
}

};
