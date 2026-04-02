/*! \file WiFiAdapter.cpp
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

#include <functional>
#include <queue>
#include <vector>
#include <algorithm>

#include <WiFi.h>
#include <WiFiAP.h>
#include <ESPmDNS.h>
#include <WebServer.h>
#include <WifiClient.h>
#include <LittleFS.h>
#include <ESP32-targz.h>

#include "LogManager.h"
#include "WiFiAdapter.h"
#include "Configuration.h"
#include "MemController.h"
#include "serial_number.h"

#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)

class ChunkedStream : public Stream {
public:
    ChunkedStream(WebServer *output) {
        m_output = output;
    }
    ~ChunkedStream() {}

    int available() override {
        return m_output->client().available();
    }

    int read() override {
        return m_output->client().read();
    }
    int peek() override {
        return m_output->client().peek();
    }
    size_t write(uint8_t b) override {
        return m_output->client().write(b);
    }
    size_t write(const uint8_t *buf, size_t size) override {
        m_output->sendContent((const char *)buf, size);
        return size;
    }

private:
    WebServer *m_output;
};

class ExtendedWebServer : public WebServer {
public:
    ExtendedWebServer(int port = 80)
    : WebServer(port)
    {}
    ~ExtendedWebServer() {}

    size_t StreamArchive(fs::FS *source, const char *path)
    {
        // First parse the path to get the list of files that need to be packaged and sent, so
        // that we know if there is actually anything to send.
        TAR::dir_entities_t dirEntries;
        TAR::collectDirEntities(&dirEntries, source, path);
        if (dirEntries.size() == 0) {
            return 0;
        }
        // Due to an oddness in the WebServer library, it ignores the content length set in the
        // _prepareHeader() method unless the length has never been set (_contentLength ==
        // CONTENT_LENGTH_NOT_SET), so we have to set the length to CONTENT_LENGTH_UNKNOWN
        // here to make sure it does into chunked mode...
        setContentLength(CONTENT_LENGTH_UNKNOWN);

        // OK, so there's something to send, so we can build the headers then stream
        String headers, module_id;
        if (logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_MODULEID_S, module_id)) {
            if (module_id.startsWith("TNODEID")) {
                // This is the default configuration, if the user hasn't configured the module yet, but
                // we don't want to pass it back as the filename, so ...
                module_id = String("wibl-logs.tgz");
            } else {
                module_id += ".tgz";
            }
        } else {
            module_id = String("wibl-logs.tgz");
        }
        sendHeader("Content-Disposition", String("attachment; filename=\"") + module_id + "\"");
        _prepareHeader(headers, 200, "application/tar+gzip", CONTENT_LENGTH_UNKNOWN);
        _currentClient.write(headers.c_str(), headers.length());

        // We can now stream the tar/gzipped data to the client, but we can't just direct the
        // information to the client connection, since we need to use the chunking mechanism
        // to make sure that the formatting is correct.  The ChunkedStream here provides an
        // over-ride for the write() method in the Stream class that calls the server's
        // sendContent() method to do this.
        ChunkedStream op(this);
        size_t compressed_size = TarGzPacker::compress(source, dirEntries, &op);
        return compressed_size;
    }
};

class ConnectionStateMachine {
public:
    ConnectionStateMachine(bool verbose = false)
    : m_verbose(verbose)
    {
        String boot_status;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, boot_status);
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_BOOTSTATUS_S, boot_status);
        if (m_verbose) {
            Serial.printf("DBG: starting ConnectionStateMachine; boot status is %s\n", boot_status.c_str());
        }
        m_lastConnectAttempt = m_lastStatusCheck = millis();
        m_retryDelay = retryDelay();
        m_connectDelay = connectionDelay();
        m_statusDelay = 500;    // Delay between status checks in milliseconds
        logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_WIFI_OPENCONNECT_B, m_openConnectEnabled);
        m_openConnectTried = false;
        m_currentCandidateIndex = 0;

        m_currentState = STOPPED;
        String status;
        WiFiAdapter::WirelessMode mode = WiFiAdapter::GetWirelessMode();
        if (mode == WiFiAdapter::WirelessMode::ADAPTER_SOFTAP) {
            status = "AP-Stopped";
        } else if (mode == WiFiAdapter::WirelessMode::ADAPTER_AP_STA) {
            status = "AP+Station-Stopped";
        } else {
            status = "Station-Stopped";
        }
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, status);
    }

    bool Verbose(void) { return m_verbose; }
    void Verbose(bool verbose) { m_verbose = verbose; }

    void Start(void)
    {
        WiFiAdapter::WirelessMode mode = WiFiAdapter::GetWirelessMode();
        if (mode == WiFiAdapter::WirelessMode::ADAPTER_SOFTAP) {
            // AP-only: bring up AP and never attempt a station join.
            m_currentState = AP_MODE;
            logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, "AP-Enabled");
            apSetup();
        } else if (mode == WiFiAdapter::WirelessMode::ADAPTER_AP_STA) {
            // AP+Station: bring up AP and immediately try a single station join sequence.
            WiFi.mode(WIFI_AP_STA);
            WiFi.setAutoReconnect(false);   // one-shot join; do not auto-retry in background
            m_currentState = AP_MODE;
            apSetup();
            logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, "AP+Station-Enabled,Connecting");
            m_currentState = STATION_CONNECTING;
            m_currentCandidateIndex = 0;
            m_lastConnectAttempt = millis();
            if (attemptStationJoin())
                m_currentState = STATION_CONNECTED;
        } else {
            // Station-only: immediately try a single station join sequence.
            WiFi.mode(WIFI_STA);
            WiFi.setAutoReconnect(false);   // one-shot join; do not auto-retry in background
            logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, "Station-Enabled,Connecting");
            m_currentState = STATION_CONNECTING;
            m_currentCandidateIndex = 0;
            m_lastConnectAttempt = millis();
            if (attemptStationJoin())
                m_currentState = STATION_CONNECTED;
        }
    }

    void StepState(void)
    {
        using namespace logger;

        int now = millis();
        switch (m_currentState) {
            case STOPPED:
                break;
            case AP_MODE:
                // AP-only mode or AP side of AP+Station; nothing to do here.
                break;
            case STATION_CONNECTING:
                if ((now - m_lastStatusCheck) > m_statusDelay) {
                    if (m_verbose) {
                        Serial.printf("DBG: checking for connection at %d\n", now);
                    }
                    if (isConnected()) {
                        m_currentState = STATION_CONNECTED;
                        if (m_verbose)
                            Serial.print("DBG: station now connected.\n");
                    } else if ((now - m_lastConnectAttempt) > m_connectDelay) {
                        if (m_currentCandidateIndex <= 5) {
                            if (attemptStationJoin()) {
                                m_currentState = STATION_CONNECTED;
                                if (m_verbose)
                                    Serial.print("DBG: station now connected on new candidate.\n");
                            }
                        } else {
                            if (!m_openConnectTried && m_openConnectEnabled && attemptOpenConnectScan()) {
                                m_currentState = STATION_CONNECTED;
                                if (m_verbose)
                                    Serial.print("DBG: station connected via Open WiFi Connect.\n");
                            } else {
                                wl_status_t status = WiFi.status();
                                Serial.printf("INF: station join failed for SSID \"%s\" after %d ms (WiFi.status=%d).\n",
                                              m_lastCandidateSsid.c_str(), now - m_lastConnectAttempt, (int)status);
                                WiFiAdapter::WirelessMode mode = WiFiAdapter::GetWirelessMode();
                                WiFi.setAutoReconnect(false);
                                WiFi.disconnect(true, true);  // fully drop station so core doesn't auto-retry
                                if (mode == WiFiAdapter::WirelessMode::ADAPTER_AP_STA) {
                                    logger::LoggerConfig.SetConfigString(
                                        logger::Config::ConfigParam::CONFIG_WS_STATUS_S,
                                        "AP+Station-Enabled,Station-Join-Failed");
                                    m_currentState = AP_MODE;
                                    if (m_verbose)
                                        Serial.print("DBG: station join failed; staying in AP+Station with AP only (no further attempts).\n");
                                } else {
                                    logger::LoggerConfig.SetConfigString(
                                        logger::Config::ConfigParam::CONFIG_WS_STATUS_S,
                                        "Station-Enabled,Station-Join-Failed");
                                    m_currentState = STOPPED;
                                    if (m_verbose)
                                        Serial.print("DBG: station join failed; stopping further station attempts until reboot.\n");
                                }
                            }
                        }
                    } else {
                        if (m_verbose)
                            Serial.print("DBG: station still not connected.\n");
                    }
                }
                break;
            case STATION_CONNECTED: {
                const char *connected_status = (WiFiAdapter::GetWirelessMode() == WiFiAdapter::WirelessMode::ADAPTER_AP_STA)
                    ? "AP+Station-Enabled,Connected" : "Station-Enabled,Connected";
                logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WS_STATUS_S, connected_status);
                m_currentState = CONNECTION_CHECK;
                if (m_verbose) {
                    Serial.print("DBG: station connected to network, setting state to Connected.\n");
                }
                completeStationJoin();
                break;
            }
            case CONNECTION_CHECK:
                if ((now - m_lastStatusCheck) > m_retryDelay) {
                    if (m_verbose) {
                        Serial.printf("DBG: checking connection status since last check was %d ago.\n", now - m_lastStatusCheck);
                    }
                    if (!isConnected()) {
                        WiFiAdapter::WirelessMode mode = WiFiAdapter::GetWirelessMode();
                        const char *disco_status = (mode == WiFiAdapter::WirelessMode::ADAPTER_AP_STA)
                            ? "AP+Station-Enabled,Disconnected" : "Station-Enabled,Disconnected";
                        logger::LoggerConfig.SetConfigString(
                            logger::Config::ConfigParam::CONFIG_WS_STATUS_S, disco_status);
                        if (m_verbose) {
                            Serial.print("DBG: station disconnected; not retrying until reboot.\n");
                        }
                        m_currentState = (mode == WiFiAdapter::WirelessMode::ADAPTER_AP_STA) ? AP_MODE : STOPPED;
                    }
                }
                break;
        }
    }

    bool IsConnectionPending(void) const
    {
        return m_currentState == STATION_CONNECTING;
    }

private:
    enum State {
        STOPPED = 0,
        AP_MODE,
        STATION_CONNECTING,
        STATION_CONNECTED,
        CONNECTION_CHECK
    };
    State   m_currentState;
    bool    m_verbose;
    int     m_lastConnectAttempt;
    int     m_lastStatusCheck;
    int     m_retryDelay;
    int     m_statusDelay;
    int     m_connectDelay;
    int     m_currentCandidateIndex;
    String  m_lastCandidateSsid;
    bool    m_openConnectEnabled;
    bool    m_openConnectTried;

    void apSetup(void)
    {
        String ssid, password;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_SSID_S, ssid);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_AP_PASSWD_S, password);
        // On first bring-up, the SSID and password are not going to be set; this ensures that when the
        // logger first boots, the WIFi comes up with known SSID and password.
        if (ssid.length() == 0) ssid = "wibl-config";
        if (password.length() == 0) password = "wibl-config-password";
        WiFi.softAP(ssid.c_str(), password.c_str());
        WiFi.setSleep(false);
        IPAddress server_address = WiFi.softAPIP();
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WIFIIP_S, server_address.toString());
        if (m_verbose) {
            Serial.printf("DBG: started AP mode on %s:%s with IP %s and hostname |%s|.\n", ssid.c_str(), password.c_str(), server_address.toString().c_str(), WiFi.softAPgetHostname());
        }
        startMDNSResponder();
    }

    void startMDNSResponder(void)
    {
        String logger_name;
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_MDNS_NAME_S, logger_name);
        if (!MDNS.begin(logger_name)) {
            Serial.print("ERR: failed to start mDNS responder ... you'll have to find the IP on your own!");
        }
    }

    bool attemptStationJoin(void)
    {
        String ignored_ssids[5];
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID1_S, ignored_ssids[0]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID2_S, ignored_ssids[1]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID3_S, ignored_ssids[2]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID4_S, ignored_ssids[3]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID5_S, ignored_ssids[4]);

        auto isIgnored = [&ignored_ssids](String const& candidate) -> bool {
            for (int i = 0; i < 5; ++i) {
                if (ignored_ssids[i].length() > 0 && candidate == ignored_ssids[i])
                    return true;
            }
            return false;
        };

        static const logger::Config::ConfigParam preset_ssid[] = {
            logger::Config::CONFIG_UPLOAD_WIFI_SSID1_S, logger::Config::CONFIG_UPLOAD_WIFI_SSID2_S,
            logger::Config::CONFIG_UPLOAD_WIFI_SSID3_S, logger::Config::CONFIG_UPLOAD_WIFI_SSID4_S,
            logger::Config::CONFIG_UPLOAD_WIFI_SSID5_S
        };
        static const logger::Config::ConfigParam preset_pass[] = {
            logger::Config::CONFIG_UPLOAD_WIFI_PASS1_S, logger::Config::CONFIG_UPLOAD_WIFI_PASS2_S,
            logger::Config::CONFIG_UPLOAD_WIFI_PASS3_S, logger::Config::CONFIG_UPLOAD_WIFI_PASS4_S,
            logger::Config::CONFIG_UPLOAD_WIFI_PASS5_S
        };

        for (int slot = m_currentCandidateIndex; slot <= 5; ++slot) {
            String ssid, password;
            if (slot == 0) {
                logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, ssid);
                logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_PASSWD_S, password);
            } else {
                logger::LoggerConfig.GetConfigString(preset_ssid[slot - 1], ssid);
                logger::LoggerConfig.GetConfigString(preset_pass[slot - 1], password);
            }
            if (ssid.length() == 0)
                continue;
            if (isIgnored(ssid))
                continue;

            m_currentCandidateIndex = slot + 1;
            m_lastConnectAttempt = millis();
            m_lastCandidateSsid = ssid;
            Serial.printf("INF: attempting station join candidate #%d SSID=\"%s\" PASSWORD=\"%s\".\n",
                          slot, ssid.c_str(), password.c_str());

            wl_status_t status = WiFi.begin(ssid.c_str(), password.c_str());
            WiFi.setSleep(false);
            if (m_verbose) {
                Serial.printf("DBG: started network join candidate #%d %s at %d with immediate status %d\n",
                              slot, ssid.c_str(), m_lastConnectAttempt, (int)status);
            }
            return status == WL_CONNECTED;
        }

        m_currentCandidateIndex = 6;
        if (WiFi.status() == WL_CONNECTED)
            return true;
        Serial.print("ERR: no valid station candidate (tried slots 0..5); check Station SSID and presets.\n");
        return false;
    }

    bool attemptOpenConnectScan(void)
    {
        m_openConnectTried = true;

        int n = WiFi.scanNetworks();
        if (n <= 0) {
            Serial.print("INF: Open WiFi Connect: no networks found during scan.\n");
            return false;
        }

        String ignored_ssids[5];
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID1_S, ignored_ssids[0]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID2_S, ignored_ssids[1]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID3_S, ignored_ssids[2]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID4_S, ignored_ssids[3]);
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_UPLOAD_IGNORED_SSID5_S, ignored_ssids[4]);

        String explicit_ssids[6];
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, explicit_ssids[0]);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_WIFI_SSID1_S, explicit_ssids[1]);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_WIFI_SSID2_S, explicit_ssids[2]);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_WIFI_SSID3_S, explicit_ssids[3]);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_WIFI_SSID4_S, explicit_ssids[4]);
        logger::LoggerConfig.GetConfigString(logger::Config::CONFIG_UPLOAD_WIFI_SSID5_S, explicit_ssids[5]);

        auto isIgnored = [&ignored_ssids](String const& candidate) -> bool {
            for (int i = 0; i < 5; ++i) {
                if (ignored_ssids[i].length() > 0 && candidate == ignored_ssids[i])
                    return true;
            }
            return false;
        };

        auto isExplicit = [&explicit_ssids](String const& candidate) -> bool {
            for (int i = 0; i < 6; ++i) {
                if (explicit_ssids[i].length() > 0 && candidate == explicit_ssids[i])
                    return true;
            }
            return false;
        };

        std::vector<int> indices;
        indices.reserve((size_t)n);
        for (int i = 0; i < n; ++i)
            indices.push_back(i);
        std::sort(indices.begin(), indices.end(), [](int a, int b) {
            return WiFi.RSSI(a) > WiFi.RSSI(b);
        });

        static const char *fallbackPassword = "12345678";

        for (int idx : indices) {
            String ssid = WiFi.SSID(idx);
            if (ssid.length() == 0)
                continue;
            if (isIgnored(ssid))
                continue;
            if (isExplicit(ssid))
                continue;

            wifi_auth_mode_t auth = WiFi.encryptionType(idx);
            Serial.printf("INF: Open WiFi Connect: trying SSID=\"%s\" (RSSI=%d, auth=%d).\n",
                          ssid.c_str(), WiFi.RSSI(idx), (int)auth);
            (void)auth;

            WiFi.begin(ssid.c_str());
            unsigned long start = millis();
            while ((millis() - start) < (unsigned long)m_connectDelay) {
                if (WiFi.status() == WL_CONNECTED) {
                    m_lastCandidateSsid = ssid;
                    return true;
                }
                delay(100);
            }

            Serial.printf("INF: Open WiFi Connect: retry with fallback password for SSID=\"%s\".\n",
                          ssid.c_str());
            WiFi.begin(ssid.c_str(), fallbackPassword);
            start = millis();
            while ((millis() - start) < (unsigned long)m_connectDelay) {
                if (WiFi.status() == WL_CONNECTED) {
                    m_lastCandidateSsid = ssid;
                    return true;
                }
                delay(100);
            }

            Serial.printf("INF: Open WiFi Connect: failed to join SSID=\"%s\".\n", ssid.c_str());
        }

        Serial.print("INF: Open WiFi Connect: no suitable open networks succeeded.\n");
        return false;
    }

    void completeStationJoin(void)
    {
        IPAddress server_address = WiFi.localIP();
        logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WIFIIP_S, server_address.toString());
        String connected_ssid = WiFi.SSID();
        if (connected_ssid.length() > 0) {
            logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_STATION_SSID_S, connected_ssid);
        }
        if (m_verbose) {
            Serial.printf("DBG: completing station join at IP %s, hostname reported as |%s| on SSID |%s|\n",
                          server_address.toString().c_str(), WiFi.getHostname(), connected_ssid.c_str());
        }
        startMDNSResponder();
    }

    bool isConnected(void)
    {
        wl_status_t status = WiFi.status();
        m_lastStatusCheck = millis();
        if (m_verbose) {
            Serial.printf("DBG: checking WiFi status at %d with status %d\n", m_lastStatusCheck, (int)status);
        }
        return status == WL_CONNECTED;
    }

    int retryDelay(void)
    {
        String val;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_DELAY_S, val);
        return val.toInt() * 1000;
    }

    int connectionDelay(void)
    {
        String val;
        logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_STATION_TIMEOUT_S, val);
        return val.toInt() * 1000;
    }
};

/// \class ESP32WiFiAdapter
/// \brief Implementation of the WiFiAdapter base class for the ESP32 module

class ESP32WiFiAdapter : public WiFiAdapter {
public:
    /// Default constructor for the ESP32 adapter.  This brings up the parameter store to use
    /// for WiFi parameters, but takes no other action until the user explicitly starts the AccessPoint.
    ESP32WiFiAdapter(void)
    : m_storage(nullptr), m_server(nullptr), m_messages(nullptr), m_statusCode(HTTPReturnCodes::OK)
    {
        if ((m_storage = mem::MemControllerFactory::Create()) == nullptr) {
            return;
        }
        // Auth and status responses accumulate several strings; keep headroom for longer tokens/certs.
        if ((m_messages = new DynamicJsonDocument(6144)) == nullptr) {
            return;
        }
    }
    /// Default destructor for the ESP32 adapter.  This stops the Access Point, if it isn't already down,
    /// and then deletes the ParamStore manipulation object.
    virtual ~ESP32WiFiAdapter(void)
    {
        stop();
        delete m_storage; // Note that we're not stopping the interface, since it may still be required elsewhere
        delete m_messages;
    }

    void PauseConfigWebServerDuringTls(void) override
    {
        if (m_server != nullptr && !m_configWebTlsPaused) {
            m_server->close();
            maybeShrinkMessagesDocForTls();
            m_configWebTlsPaused = true;
        }
    }

    void ResumeConfigWebServerAfterTls(void) override
    {
        if (m_server != nullptr && m_configWebTlsPaused) {
            m_server->begin();
            m_configWebTlsPaused = false;
        }
    }

private:
    mem::MemController  *m_storage;     ///< Pointer to the storage object to use
    ExtendedWebServer   *m_server;      ///< Pointer to the server object, if started.
    bool                m_configWebTlsPaused = false;
    std::queue<String>  m_commands;     ///< Queue to handle commands sent by the user
    DynamicJsonDocument *m_messages;    ///< Accumulating message content to be send to the client
    HTTPReturnCodes     m_statusCode;   ///< Status code to return to the user with the transaction response
    ConnectionStateMachine m_state;     ///< Manager for connection state

    /// While the config web is closed for TLS, shrink the JSON accumulator if it is still small so
    /// mbedTLS ECDHE can obtain several contiguous internal-heap blocks (BIGNUM / MPI).
    void maybeShrinkMessagesDocForTls(void)
    {
        if (m_messages == nullptr) {
            return;
        }
        constexpr size_t kTlsTargetCap = 3072U;
        size_t const cap = m_messages->capacity();
        if (cap <= kTlsTargetCap) {
            return;
        }

        size_t const measured = measureJson(*m_messages);
        constexpr size_t kMaxSerializedForShrink = 384U;
        if (measured > kMaxSerializedForShrink) {
            return;
        }

        String probe;
        probe.reserve(measured + 1U);
        serializeJson(*m_messages, probe);

        auto *nu = new DynamicJsonDocument(kTlsTargetCap);
        if (nu == nullptr) {
            return;
        }
        DeserializationError const err = deserializeJson(*nu, probe);
        if (err) {
            delete nu;
            return;
        }
        delete m_messages;
        m_messages = nu;
    }

    /// @brief Handle HTTP requests to the /command endpoint
    ///
    /// HTTP POST endpoint handler for commands being sent to the logger through the web-server
    /// interface.  This simple captures any "command" arguments and queues them for the system
    /// to execute later.
    ///
    /// Browsers request /favicon.ico; without a handler the static FS open fails and WebServer logs
    /// "request handler failed to handle request".
    void handleFavicon(void)
    {
        m_server->send(HTTPReturnCodes::OK, "text/plain", "");
    }

    /// @return N/A
    void handleCommand(void)
    {
        bool scheduled_dropbox_test = false;
        for (uint32_t i = 0; i < m_server->args(); ++i) {
            if (m_server->argName(i) == "command") {
                String cmd = m_server->arg(i);
                cmd.trim();
                m_commands.push(cmd);
                if (cmd == "dropbox test") {
                    scheduled_dropbox_test = true;
                }
            }
        }
        // Dropbox TLS needs a large contiguous internal-heap peak. If we defer work but return
        // without send(), WebServer keeps the POST transaction open; lwIP buffers + fragmentation
        // then break mbedTLS writes (largest_internal ~3KB). Finish HTTP here; SerialCommand
        // still runs the test after m_wirelessDropboxDeferCount without TransmitMessages().
        if (scheduled_dropbox_test) {
            m_server->send(HTTPReturnCodes::OK, "application/json",
                           "{\"messages\":[\"Dropbox test accepted. Full result is on USB serial; "
                           "this response is immediate so the browser releases RAM before TLS.\"]}");
        }
    }

    /// Read raw POST body (same pattern for /setup and /labdefaults).
    void readPostedPlainBody(String &body, size_t maxLen)
    {
        body = "";
        if (m_server->hasArg("plain")) {
            body = m_server->arg("plain");
            body.trim();
            return;
        }
        int cl = -1;
        if (m_server->hasHeader("Content-Length"))
            cl = m_server->header("Content-Length").toInt();
        if (cl > 0 && (size_t)cl <= maxLen) {
            body.reserve((unsigned)cl);
            WiFiClient c = m_server->client();
            unsigned long const started = millis();
            while ((int)body.length() < cl && c.connected()) {
                if (c.available()) {
                    body += (char)c.read();
                } else {
                    if (millis() - started > 10000) {
                        Serial.printf("ERR: readPostedPlainBody timeout (%d of %d bytes).\n",
                                      body.length(), cl);
                        break;
                    }
                    delay(1);
                    yield();
                }
            }
        }
        body.trim();
    }

    /// @brief Handle POST /setup with raw JSON body (avoids form field size limits so passwords are not truncated)
    void handleSetup(void)
    {
        String body;
        readPostedPlainBody(body, 8192);
        if (body.length() > 0) {
            if (body.startsWith("{"))
                m_commands.push("setup " + body);
            else
                m_commands.push(body);
        }
    }

    /// @brief Handle POST /labdefaults with raw JSON (same size limits as /setup)
    void handleLabDefaults(void)
    {
        String body;
        readPostedPlainBody(body, 8192);
        if (body.length() > 0)
            m_commands.push("lab defaults " + body);
    }

    /// @brief Provide a simple endpoint for HTTP GET to indicate presence
    ///
    /// It's not always possible to tell whether you have a web-server available on a known IP
    /// address.  This endpoint handle (typically for GET but it should work for anything) returns
    /// a simple text message with the serial number of the logger board and 200OK so that you
    /// know that the server is on and running.
    ///
    /// @return N/A
    void heartbeat(void)
    {
        m_commands.push("status");
    }
    
    void transferLogs(void)
    {
        size_t bytes_sent = m_server->StreamArchive(m_storage->ControllerPtr(), "/logs");
        if (bytes_sent == 0) {
            m_server->send(400, "application/json", "{\"error\":\"no logs found; this shouldn't happen since there should always be one on the go!\"}");
        } else {
            if (m_state.Verbose()) {
                Serial.printf("DBG: transferred %d bytes of log data.\n", bytes_sent);
            }
        }
    }

    /// Bring up the WiFi adapter, which in this case includes bring up the soft access point.  This
    /// uses the ParamStore to get the information required for the soft-AP, and then interrogates the
    /// server to find out which IP address was allocated.  This is very likely to be the same address
    /// each time (it's usually set by the soft-AP by default), but could change.  The current value is
    /// stored in the NVRAM, but should not be relied on until the server is started.
    ///
    /// \return True if the adapter started as expected; otherwise false.
    
    bool start(void)
    {
        if ((m_server = new ExtendedWebServer()) == nullptr) {
            Serial.println("ERR: failed to start web server.");
            return false;
        } else {
            // Configure the endpoints served by the server
            m_server->on("/heartbeat", HTTPMethod::HTTP_GET, std::bind(&ESP32WiFiAdapter::heartbeat, this));
            m_server->on("/favicon.ico", HTTPMethod::HTTP_GET, std::bind(&ESP32WiFiAdapter::handleFavicon, this));
            m_server->on("/command", HTTPMethod::HTTP_POST, std::bind(&ESP32WiFiAdapter::handleCommand, this));
            m_server->on("/setup", HTTPMethod::HTTP_POST, std::bind(&ESP32WiFiAdapter::handleSetup, this));
            m_server->on("/labdefaults", HTTPMethod::HTTP_POST, std::bind(&ESP32WiFiAdapter::handleLabDefaults, this));
            m_server->on("/archive", HTTPMethod::HTTP_GET, std::bind(&ESP32WiFiAdapter::transferLogs, this));
            if (!m_storage->Controller().exists("/logs")) {
                m_storage->Controller().mkdir("/logs");
            }
            // Use "/logs" not "/logs/" for the FS root: StaticRequestHandler ctor opens this path;
            // a trailing slash on SD/FAT can trigger spurious VFS create errors on some ESP-IDF builds.
            m_server->serveStatic("/logs", m_storage->Controller(), "/logs");
            m_server->serveStatic("/", LittleFS, "/website/");
        }
        //m_state.Verbose(true);
        m_state.Start();
        m_server->begin();
        return true;
    }
    
    /// Stop the WiFi adapter cleanly.  This attempts to disconnect any current client cleanly, to avoid broken pipes.
    
    void stop(void)
    {
        m_configWebTlsPaused = false;
        delete m_server;
        m_server = nullptr;
    }
    
    /// Read the first terminated (with [LF]) string from the client, and return.  This will read over multiple
    /// packets, etc., until it gets a [LF] character, and then return everything since the last [LF].  The
    /// [LF] is not added to the string, but depending on client, there may be a [CR].
    ///
    /// \return A String object with the contents of the latest read from the client.
    
    String readBuffer(void)
    {
        if (m_commands.size() == 0) {
            return String("");
        } else {
            String rtn = m_commands.front();
            m_commands.pop();
            return rtn;
        }
    }
    
    /// Transfer a specific log file from the logger to the client in an efficient manner that doesn't include
    /// converting from binary to String, etc.  The filename must exist, and there must be a connected
    /// client ready to catch the output, otherwise the call will fail.  The transfer is pretty simple, relying on
    /// efficient implementation of buffer in the libraries for fast transfer.
    ///
    /// \param filename Name of the file to transfer to the client
    /// \return True if the transfer worked, otherwise false.
    
    bool sendLogFile(String const& filename, uint32_t filesize, logger::Manager::MD5Hash const& filehash)
    {
        File f = m_storage->Controller().open(filename, FILE_READ);
        if (!f) {
            Serial.println("ERR: failed to open file for transfer.");
            return false;
        } else {
            String hash_digest = "md5=" + filehash.Value();
            m_server->sendHeader("Digest", hash_digest);
            m_server->streamFile(f, "application/octet-stream");
            f.close();
        }
        return true;
    }

    /// Accumulate the message given into the list of those to be sent to the client when the
    /// response is finally sent.  Note that the code doesn't add any formatting, so if you want
    /// newlines in the output message set, you need to add them explicitly to the \a message that
    /// you send.
    ///
    /// \param message  \a String to add to the list of messages.
    /// \return N/A

    void accumulateMessage(String const& message)
    {
        if ((m_messages->memoryUsage() + message.length()) > 0.95*m_messages->capacity()) {
            // Expand capacity to ensure that the message will be added successfully
            size_t new_capacity = m_messages->capacity() * 2;
            DynamicJsonDocument *new_doc = new DynamicJsonDocument(new_capacity);
            if (new_doc != nullptr) {
                new_doc->set(*m_messages);
                delete m_messages;
                m_messages = new_doc;
            }
        }
        if (!(*m_messages)["messages"].add(message)) {
            Serial.printf("ERR: failed to add message to accumulation buffer (capacity %d bytes); messages may be truncated.\n",
                m_messages->capacity());
        }
    }

    /// Replace the entire message to be sent to the client with the provided string.
    ///
    /// \param message \a String to use for the return message.
    /// \return N/A

    void setMessage(DynamicJsonDocument const& message)
    {
        *m_messages = message;
    }

    /// Configure the HTTP status code that the response should use.  By default, the status code used
    /// when the response is finally sent to the client is 200 OK.  However, if there is an error
    /// condition, then it might be useful to send something else, alerting the client.  Although you
    /// should technically only use HTTP status codes, there's no checking on this, so you could send
    /// anything that your client will recognise.
    ///
    /// \param status_code  Code to return to the client (typically HTTP status codes)
    /// \return N/A

    void setStatusCode(HTTPReturnCodes status_code)
    {
        m_statusCode = status_code;
    }

    /// Send the accumulated messages for this transaction back to the client.  This takes the accumulated
    /// messages, and the status code, and sends back via the web-server, then resets the message buffer
    /// to empty, and the status code to 200 OK.
    ///
    /// \return True if the message was send succesfully, otherwise false.

    bool transmitMessages(void)
    {
        String message;
        serializeJson(*m_messages, message);
        //Serial.printf("DBG: WiFi transmitting response |%s|\n", message.c_str());
        m_server->send(m_statusCode, "application/json", message);
        m_messages->clear();
        m_statusCode = HTTPReturnCodes::OK; // "OK" by default
        return true;
    }

    /// In order for the WiFi adapter to manage its internal state, it has to get a regular run loop call
    /// from the main logger.  In addition to passing on this time to the web server to handle client
    /// requests, this code also manages the ConnectionStateMachine, which allows the logger to execute the
    /// client network join code, with suitable fall-back conditions.
    ///
    /// \return N/A

    void runLoop(void)
    {
        yield();
        m_state.StepState();
        if (m_server != nullptr) {
            // During station join, run extra handleClient passes so the AP side keeps serving, but avoid
            // delay(1) between each (~11 ms/frame stalled the UI); yield lets WiFi/system tasks run.
            int const n = m_state.IsConnectionPending() ? 12 : 1;
            for (int i = 0; i < n; ++i) {
                m_server->handleClient();
                if (i + 1 < n) {
                    yield();
                }
            }
        }
    }
};

#endif

/// Pass-through implementation to sub-class code to start the WiFi adapter.
///
/// \return True if the adapter started, or false.
bool WiFiAdapter::Startup(void) { return start(); }

/// Pass-through implementation to the sub-class code to stop the WiFI adapter.
void WiFiAdapter::Shutdown(void) { stop(); }

/// Pass-through implementation to the sub-class code to retrieve the first available string from the client.
///
/// \return String with the latest LF-terminated data from the client.
String WiFiAdapter::ReceivedString(void) { return readBuffer(); }

/// Pass-through implementation to the sub-class code to transfer a log file to the client.
///
/// \param filename Name of the log file to be transferred.
/// \return True if the file was transferred, otherwise false.
bool WiFiAdapter::TransferFile(String const& filename, uint32_t filesize, logger::Manager::MD5Hash const& filehash)
    { return sendLogFile(filename, filesize, filehash); }

/// Pass-through implementation to the sub-class code to accumulate messages
///
/// \param message  String for the message to send
/// \return N/A
void WiFiAdapter::AddMessage(String const& message) { accumulateMessage(message); }

/// Pass-through implementation to the sub-class code to reset the message from straight JSON
///
/// @param message JSON document to send back to the client
/// @return N/A
void WiFiAdapter::SetMessage(DynamicJsonDocument const& message) { setMessage(message); }

/// Pass-through implementation to the sub-class code to set status code
///
/// \param status_code  HTTP status code to set
/// \return N/A
void WiFiAdapter::SetStatusCode(HTTPReturnCodes status_code) { setStatusCode(status_code); }

/// Pass-through implementation to the sub-class code to transmit all available messages.
/// This should also complete the transaction from the client's request.
///
/// \return True if the messages were transmitted successfully
bool WiFiAdapter::TransmitMessages(void) { return transmitMessages(); }

/// Pass-through implementation to the sub-class code to set the wireless adapter mode.
///
/// \param mode WirelessMode for the adapter on startup
void WiFiAdapter::SetWirelessMode(WirelessMode mode)
{
    String value;
    if (mode == WirelessMode::ADAPTER_STATION) {
        value = "Station";
    } else if (mode == WirelessMode::ADAPTER_SOFTAP) {
        value = "AP";
    } else if (mode == WirelessMode::ADAPTER_AP_STA) {
        value = "AP+Station";
    } else {
        Serial.println("ERR: unknown wireless adapater mode.");
        return;
    }
    if (!logger::LoggerConfig.SetConfigString(logger::Config::ConfigParam::CONFIG_WIFIMODE_S, value)) {
        Serial.println("ERR: failed to set WiFi adapater mode on module.");
    }
}

/// Pass-through implementation to the sub-class code to get the wireless adapter mode.
///
/// \return WirelessMode enum value, using AP as the default
WiFiAdapter::WirelessMode WiFiAdapter::GetWirelessMode(void)
{
    String          value;
    WirelessMode    rc;
    
    if (!logger::LoggerConfig.GetConfigString(logger::Config::ConfigParam::CONFIG_WIFIMODE_S, value)) {
        Serial.println("ERR: failed to get WiFi adapter mode on module.");
        value = "UNKNOWN";
    }
    if (value == "Station")
        rc = WirelessMode::ADAPTER_STATION;
    else if (value == "AP+Station")
        rc = WirelessMode::ADAPTER_AP_STA;
    else
        rc = WirelessMode::ADAPTER_SOFTAP;
    return rc;
}

/// Pass-through implementation to the sub-class to run the processing loop
///
/// \return N/A
void WiFiAdapter::RunLoop(void) { runLoop(); }

/// Create an implementation of the WiFiAdapter interface that's appropriate for the hardware in use
/// in the current logger module.
///
/// \return Pointer to the adapter, cast to the base WiFiAdapter.
WiFiAdapter *WiFiAdapterFactory::Create(void)
{
    WiFiAdapter *obj;
#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
    obj = new ESP32WiFiAdapter();
#else
#error "No WiFi Adapter supported for hardware."
#endif
    return obj;
}
