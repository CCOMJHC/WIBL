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
#include "WiFiAdapter.h"

#include <cstdio>
#include <cstring>
#include <time.h>

namespace {

struct ScopePauseWebForTls {
    WiFiAdapter *m_w;
    explicit ScopePauseWebForTls(WiFiAdapter *w) : m_w(w)
    {
        if (m_w != nullptr) {
            m_w->PauseConfigWebServerDuringTls();
        }
    }
    ~ScopePauseWebForTls()
    {
        if (m_w != nullptr) {
            m_w->ResumeConfigWebServerAfterTls();
        }
    }
};

void LogDropboxRequestMeta(char const *ctx, size_t payload_bytes, bool body_in_arduino_string, size_t content_length,
                           int custom_header_count)
{
    Serial.printf("DBG: DropboxTLS req |%s| payload_bytes=%u body_in_String=%d content_length=%u custom_headers=%d\n",
                  ctx,
                  static_cast<unsigned>(payload_bytes),
                  body_in_arduino_string ? 1 : 0,
                  static_cast<unsigned>(content_length),
                  custom_header_count);
}

/// Tiny scheduler nudge before outbound TLS (heap prep delays/nudge removed — they did not help peak RAM).
void PrepareInternalHeapForTls(void)
{
    yield();
    yield();
}

/// When TLS fails, mbedTLS/WiFi errors are in WiFiClientSecure.
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

/// Same shape as Dropbox files/upload API: {"path":"...","mode":"...","autorename":false,...} into a fixed buffer.
bool FormatDropboxApiArgJson(String const& dropboxPath, char const *mode, char *out, size_t cap)
{
    if (cap < 48U || mode == nullptr) {
        return false;
    }
    size_t o = 0;
    auto append_c = [&](char c) -> bool {
        if (o + 1U >= cap) {
            return false;
        }
        out[o++] = c;
        return true;
    };
    auto append_raw = [&](char const *s) -> bool {
        for (; *s != '\0'; ++s) {
            if (!append_c(*s)) {
                return false;
            }
        }
        return true;
    };
    if (!append_raw("{\"path\":\"")) {
        return false;
    }
    for (unsigned i = 0; i < dropboxPath.length(); ++i) {
        char c = dropboxPath.charAt(i);
        if (c == '\\' || c == '"') {
            if (!append_c('\\')) {
                return false;
            }
        }
        if (!append_c(c)) {
            return false;
        }
    }
    if (!append_raw("\",\"mode\":\"")) {
        return false;
    }
    for (char const *m = mode; *m != '\0'; ++m) {
        if (!append_c(*m)) {
            return false;
        }
    }
    if (!append_raw("\",\"autorename\":false,\"mute\":false,\"strict_conflict\":false}")) {
        return false;
    }
    out[o] = '\0';
    return true;
}

static bool WriteAll(WiFiClient &c, uint8_t const *data, size_t len)
{
    size_t w = 0;
    while (w < len) {
        size_t const remain = len - w;
        size_t const n = c.write(data + w, remain);
        if (n == 0U) {
            return false;
        }
        w += n;
        yield();
    }
    return true;
}

static bool ReadLineWiFiClient(WiFiClient &c, char *buf, size_t cap, unsigned long deadline_ms)
{
    size_t n = 0;
    while (n + 1U < cap) {
        if (!c.connected() && c.available() == 0) {
            break;
        }
        while (c.available() == 0) {
            if (millis() > deadline_ms) {
                return false;
            }
            if (!c.connected()) {
                buf[n] = '\0';
                return n > 0;
            }
            yield();
        }
        int ch = c.read();
        if (ch < 0) {
            break;
        }
        if (ch == '\n') {
            buf[n] = '\0';
            if (n > 0 && buf[n - 1U] == '\r') {
                buf[n - 1U] = '\0';
            }
            return true;
        }
        buf[n++] = static_cast<char>(ch);
    }
    buf[n] = '\0';
    return n > 0;
}

static int ParseHttpStatusCode(char const *line)
{
    char const *p = strstr(line, "HTTP/");
    if (p == nullptr) {
        return -1;
    }
    p = strchr(p, ' ');
    if (p == nullptr) {
        return -1;
    }
    return atoi(p + 1);
}

static int DropboxReadHttpStatusAndSnippet(WiFiClient &c, unsigned long deadline_ms, char *snippet, size_t snippet_cap)
{
    char line[144];
    if (!ReadLineWiFiClient(c, line, sizeof(line), deadline_ms)) {
        return -2;
    }
    int const code = ParseHttpStatusCode(line);
    for (;;) {
        if (!ReadLineWiFiClient(c, line, sizeof(line), deadline_ms)) {
            break;
        }
        if (line[0] == '\0') {
            break;
        }
    }
    size_t sn = 0;
    while (sn + 1U < snippet_cap) {
        if (millis() > deadline_ms) {
            break;
        }
        if (c.available() == 0) {
            if (!c.connected()) {
                break;
            }
            yield();
            continue;
        }
        int const ch = c.read();
        if (ch < 0) {
            break;
        }
        snippet[sn++] = static_cast<char>(ch);
    }
    snippet[sn] = '\0';
    return code;
}

static bool DropboxSendContentUploadHeadersAndMemBody(WiFiClientSecure &c, char const *token, char const *api_arg_json,
                                                      uint8_t const *body, size_t body_len)
{
    char head[1856];
    int const hn = snprintf(head, sizeof(head),
                            "POST /2/files/upload HTTP/1.1\r\n"
                            "Host: content.dropboxapi.com\r\n"
                            "User-Agent: WIBL\r\n"
                            "Authorization: Bearer %s\r\n"
                            "Content-Type: application/octet-stream\r\n"
                            "Dropbox-API-Arg: %s\r\n"
                            "Content-Length: %lu\r\n"
                            "Connection: close\r\n"
                            "\r\n",
                            token, api_arg_json, static_cast<unsigned long>(body_len));
    if (hn <= 0 || static_cast<size_t>(hn) >= sizeof(head)) {
        return false;
    }
    if (!WriteAll(c, reinterpret_cast<uint8_t const *>(head), static_cast<size_t>(hn))) {
        return false;
    }
    return WriteAll(c, body, body_len);
}

static bool DropboxSendContentUploadHeadersOnly(WiFiClientSecure &c, char const *token, char const *api_arg_json,
                                                size_t content_length)
{
    char head[1856];
    int const hn = snprintf(head, sizeof(head),
                            "POST /2/files/upload HTTP/1.1\r\n"
                            "Host: content.dropboxapi.com\r\n"
                            "User-Agent: WIBL\r\n"
                            "Authorization: Bearer %s\r\n"
                            "Content-Type: application/octet-stream\r\n"
                            "Dropbox-API-Arg: %s\r\n"
                            "Content-Length: %lu\r\n"
                            "Connection: close\r\n"
                            "\r\n",
                            token, api_arg_json, static_cast<unsigned long>(content_length));
    if (hn <= 0 || static_cast<size_t>(hn) >= sizeof(head)) {
        return false;
    }
    return WriteAll(c, reinterpret_cast<uint8_t const *>(head), static_cast<size_t>(hn));
}

static bool DropboxStreamFileBody(WiFiClientSecure &c, File &f, size_t total_len)
{
    constexpr size_t kChunk = 1024;
    uint8_t buf[kChunk];
    size_t left = total_len;
    while (left > 0U) {
        size_t const chunk = left > kChunk ? kChunk : left;
        size_t const br = f.read(buf, chunk);
        if (br != chunk) {
            return false;
        }
        if (!WriteAll(c, buf, br)) {
            return false;
        }
        left -= br;
    }
    return true;
}

} // namespace

namespace net {

void LogTlsInternalHeapCheckpoint(char const *tag)
{
    constexpr uint32_t caps = MALLOC_CAP_8BIT | MALLOC_CAP_INTERNAL;
    size_t const internal_free = heap_caps_get_free_size(caps);
    size_t const largest = heap_caps_get_largest_free_block(caps);
    uint32_t const min_heap_watermark = ESP.getMinFreeHeap();
    Serial.printf("DBG: DropboxTLS heap |%s| internal_free=%u largest_internal=%u min_heap_watermark=%u\n",
                  tag,
                  static_cast<unsigned>(internal_free),
                  static_cast<unsigned>(largest),
                  static_cast<unsigned>(min_heap_watermark));
}

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


UploadManager::UploadManager(logger::Manager *logManager, WiFiAdapter *wifi)
: m_logManager(logManager), m_timeout(-1), m_lastUploadCycle(0), m_modeDropbox(false), m_wifiAdapter(wifi)
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

    char apiArgBuf[512];
    if (!FormatDropboxApiArgJson(dropbox_file, "overwrite", apiArgBuf, sizeof(apiArgBuf))) {
        Serial.printf("ERR: Dropbox API path too long for buffer (|...%s|).\n", file_name.c_str());
        f.close();
        return false;
    }

    int32_t const effective_to = (m_timeout > 0 ? m_timeout : 15000);
    uint32_t timeout_sec = static_cast<uint32_t>(effective_to / 1000);
    if (timeout_sec == 0U) {
        timeout_sec = 1U;
    }
    if (timeout_sec > 120U) {
        timeout_sec = 120U;
    }
    unsigned long const deadline_ms = millis() + static_cast<unsigned long>(effective_to);

    ScopePauseWebForTls pause(m_wifiAdapter);
    PrepareInternalHeapForTls();
    WiFiClientSecure client;
    client.setInsecure();
    client.setTimeout(timeout_sec);
    client.setHandshakeTimeout(static_cast<unsigned long>(effective_to));

    bool ok = false;
    char snippet[320];
    snippet[0] = '\0';
    int code = -1;

    LogTlsInternalHeapCheckpoint("before TLS connect");
    if (!client.connect("content.dropboxapi.com", 443)) {
        LogTlsInternalHeapCheckpoint("after TLS connect fail");
        LogDropboxRequestMeta("dropbox file upload", sz, false, sz, 0);
        client.stop();
        LogTlsInternalHeapCheckpoint("after client.stop");
        f.close();
        return false;
    }
    LogTlsInternalHeapCheckpoint("after TLS connect ok");
    LogDropboxRequestMeta("dropbox file upload", sz, false, sz, 3);
    LogTlsInternalHeapCheckpoint("before write request");
    if (!DropboxSendContentUploadHeadersOnly(client, m_dropboxToken.c_str(), apiArgBuf, sz) ||
        !DropboxStreamFileBody(client, f, sz)) {
        LogTlsInternalHeapCheckpoint("after write fail");
        code = -1;
    } else {
        LogTlsInternalHeapCheckpoint("after write body");
        code = DropboxReadHttpStatusAndSnippet(client, deadline_ms, snippet, sizeof(snippet));
        LogTlsInternalHeapCheckpoint("after response");
        if (code == 200) {
            ok = true;
        } else {
            Serial.printf("DBG: Dropbox upload HTTP %d: %s\n", code, snippet);
        }
    }
    client.stop();
    LogTlsInternalHeapCheckpoint("after client.stop");
    f.close();
    return ok;
}

bool TestDropboxUpload(String *detail_message, WiFiAdapter *wifi)
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

    char apiArgBuf[512];
    if (!FormatDropboxApiArgJson(remote, "overwrite", apiArgBuf, sizeof(apiArgBuf))) {
        if (detail_message) {
            *detail_message = "Dropbox folder path too long for API buffer.";
        }
        return false;
    }

    String wibl_ap_ssid;
    LoggerConfig.GetConfigString(Config::CONFIG_AP_SSID_S, wibl_ap_ssid);

    String const station_ssid = WiFi.SSID();

    char whenbuf[48];
    struct tm timeinfo;
    if (getLocalTime(&timeinfo, 10)) {
        if (strftime(whenbuf, sizeof(whenbuf), "%Y-%m-%d %H:%M:%S", &timeinfo) == 0U) {
            snprintf(whenbuf, sizeof(whenbuf), "(strftime failed)");
        }
    } else {
        snprintf(whenbuf, sizeof(whenbuf), "(not set; uptime %lu ms)", static_cast<unsigned long>(millis()));
    }

    char bodyBuf[512];
    String fw_ver = FirmwareVersion();
    int const bl = snprintf(bodyBuf, sizeof(bodyBuf),
                            "WIBL Dropbox connectivity test\n"
                            "Firmware: %s\n"
                            "WIBL AP SSID (configured): %s\n"
                            "Station connected to AP SSID: %s\n"
                            "Local date/time: %s\n"
                            "Elapsed ms since boot: %lu\n",
                            fw_ver.c_str(),
                            wibl_ap_ssid.length() > 0 ? wibl_ap_ssid.c_str() : "(none)",
                            station_ssid.length() > 0 ? station_ssid.c_str() : "(unknown)",
                            whenbuf,
                            static_cast<unsigned long>(millis()));
    if (bl <= 0 || static_cast<size_t>(bl) >= sizeof(bodyBuf)) {
        if (detail_message) {
            *detail_message = "Internal error building test body.";
        }
        return false;
    }
    size_t const content_len = static_cast<size_t>(bl);

    uint32_t timeout_sec = static_cast<uint32_t>(timeout_ms / 1000);
    if (timeout_sec == 0U) {
        timeout_sec = 1U;
    }
    if (timeout_sec > 120U) {
        timeout_sec = 120U;
    }
    unsigned long const deadline_ms = millis() + static_cast<unsigned long>(timeout_ms);

    ScopePauseWebForTls pause(wifi);
    PrepareInternalHeapForTls();
    WiFiClientSecure client;
    client.setInsecure();
    client.setTimeout(timeout_sec);
    client.setHandshakeTimeout(static_cast<unsigned long>(timeout_ms));

    int code = -1;
    char snippet[400];
    snippet[0] = '\0';

    LogTlsInternalHeapCheckpoint("before TLS connect");
    if (!client.connect("content.dropboxapi.com", 443)) {
        LogTlsInternalHeapCheckpoint("after TLS connect fail");
        LogDropboxRequestMeta("dropbox test", content_len, false, content_len, 0);
        if (detail_message) {
            *detail_message = "TLS connect to content.dropboxapi.com failed";
            AppendTlsFailureDetail(detail_message, client);
        }
        client.stop();
        LogTlsInternalHeapCheckpoint("after client.stop");
        return false;
    }
    LogTlsInternalHeapCheckpoint("after TLS connect ok");
    LogDropboxRequestMeta("dropbox test", content_len, false, content_len, 3);
    LogTlsInternalHeapCheckpoint("before write request");
    if (!DropboxSendContentUploadHeadersAndMemBody(client, token.c_str(), apiArgBuf,
                                                   reinterpret_cast<uint8_t const *>(bodyBuf), content_len)) {
        LogTlsInternalHeapCheckpoint("after write fail");
        code = -1;
        if (detail_message) {
            *detail_message = "Write request or body failed";
            AppendTlsFailureDetail(detail_message, client);
        }
    } else {
        LogTlsInternalHeapCheckpoint("after write body");
        code = DropboxReadHttpStatusAndSnippet(client, deadline_ms, snippet, sizeof(snippet));
        LogTlsInternalHeapCheckpoint("after response");
        if (detail_message) {
            *detail_message = String("HTTP ") + String(code) + ": " + snippet;
            if (code < 0) {
                AppendTlsFailureDetail(detail_message, client);
            } else if (code == 401) {
                if (strstr(snippet, "invalid_access_token") != nullptr) {
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
    }
    client.stop();
    LogTlsInternalHeapCheckpoint("after client.stop");

    if (code == 200) {
        if (detail_message) {
            *detail_message = String("OK: uploaded ") + remote + " (" + String(static_cast<unsigned>(content_len)) + " bytes)";
        }
        Serial.printf("INF: Dropbox test upload succeeded -> %s\n", remote.c_str());
        return true;
    }
    Serial.printf("ERR: Dropbox test upload failed (HTTP %d)\n", code);
    return false;
}

}
