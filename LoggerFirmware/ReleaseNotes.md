# Release Notes: Logger Firmware

## Firmware 1.5.5

Firmware 1.5.5 includes the following changes:

* __Multicast DNS Support__.  The firmware instantiates a multicast DNS responder when the WiFi interface starts, so that the logger can be found using the `name.local` protocol on any supporting browser (that's most of them now).  This works in AP or Station mode, and means that you don't need to know the IP address of the logger to find it.  The mDNS name is a parameter (set with `mdns` command to the logger, or the firmware website configuration page, or corresponding JSON).
* __Default Unique ID__.  The logger now declares the unique ID for the logger to be a fixed (but invalid) string (`TNODEID` by default), since the previous version (`wibl-logger`) caused apparent failure of the generation mechanism in the firmware website (detail: having a hyphen in the name tells the JavaScript that it's a valid UUID and therefore shouldn't be changed!).
* __Website Icon__.  The firmware website now includes a mechanism to store a small icon (favicon.ico) that most browsers will attempt to show in the tab used for the logger pages.

## Firmware 1.5.4

Firmware 1.5.4 includes the following changes:

* __Management Website Error Reporting__.  This adds reporting of errors (as modal dialog boxes) to the management website so that, e.g., bad JSON files don't cause silent failure in the JavaScript (the JSON is parsed so that it can be stringified) that causes confusion for the user (i.e., the upload appears to fail, but there's no clue as to why).
* __Management Website Consistency__.  With previous versions of the management website, the configuration JSON was parsed in order from top to bottom of the HTML page.  If the JSON was not in the correct format, this could cause some of the elements in the display to be replaced with default values (often "undefined"), invalidating the configuration, before the parsing failed.  This version of the firmware parses the enable elements first, making it much more likely that a bad configuration file will be detected early.
* __Consistent Logger Addressing__.  Previous version of the management website JavaScript used a fixed address for the logger when attempting to connect to the REST endpoint for commands.  On the logger's own WAP, this was sufficient, but it fails when the logger joins another WAP as a station.  The code now uses the `location.host` property in JavaScript to parse out the host's name or IP address, and assembles the endpoint URL from there, ensuring that the code adapts to the logger's environment.

## Firmware 1.5.3

Firmware 1.5.3 includes the following changes:

* __WiFi Password Length Checks__.  Fixes an oversight (i.e., an exploitable bug that we don't want to see in practice) in the length of the password set for AP or station mode: if the user provided a password shorter than eight characters or longer than 64 when using the debug version of the firmware, the underlying WiFi library fails the password, but then fails a debug `assert()` which caused the firmware to enter into a reboot loop of death, bricking the logger until the entire flash memory was erased and rebuilt!
* __File Patching__.  Ah, Windows ...  It turns out that on Windows systems there isn't a `patch` command, and so the auto-patching of the WebServer.cpp code (to revert the "fix" for Chrome that forces you to attempt to complete the entire HTTP call within a single callback) doesn't work---but claims that it did.  This release of firmware uses an entirely Python patch utility so that it's platform agnostic.  Much thanks to Ashok Anjappa at CHS Pacific to help us work out what was really going on here.
* __HTTP Response MIME Code__.  Since the firmware now responds to all commands with JSON data, the MIME response header in the HTTP should always be "application/json".  It now is.

## Firmware 1.5.2

Firmware 1.5.2 includes the following changes:

* Fixes bug in logger website status script where status would not be updated once the logger was running for more than 1 day
* Updates NMEA2000-library from version 4.17.2 to 4.21.5
* Updates Arduino_LSM6DS3 from version 1.0.0 to 1.0.3
* Updates ArduinoJson from version 6.20.1 to 6.21.5
* Build updates:
  * Pins espressif32 platform version to version 6.4.0
  * Pin all library versions
  * Add automated patching of platformio package files

## Firmware 1.5.1

Firmware 1.5.1 is a bug-fix for "last known good" data reporting in the firmware website.

## Firmware 1.5.0

Firmware 1.5.0 includes the following additions:

* __Internal website__.  The logger can now host its own configuration and manipulation software, providing these to any browser as a mixture of HTML/CSS/JavaScript.  Data download is through normal browser download mechanisms by exposing the log files as a static website and providing download links as part of the website status page.  This makes the logger self-hosting.
* __Data Integrity__.  Monitoring for the latest time/position/depth on NMEA0183 and NMEA2000 inputs so that the status page on the internal website can demonstrate whether the logger is receiving data (ideal for installation, but also good for debugging while underway).
* __Auto-upload__.  If the logger is connected to a network that has internet connection, it can now be configured to automatically connect to a server to upload log files, using TLS for the connection and HTTP BasicAuth for authentication.  The upload events happen at a fixed interval, and run for a fixed duration (or until all of the files are transferred) so that the code doesn't dominate the logger's functionality while uploading.  A separate timeout parameter ensures the system doesn't halt if the server isn't available.
* __Data Monitoring__.  Ability to include algorithm requests dynamically based on the data being captured.  This resolves the issue to "no data" values in NMEA2000 inputs causing chaos in post.
* JSON output for all commands when using the WiFi interface.  This includes error messages as a JSON response with just a "messages" tag and an array of strings.
* A consistently reported firmware version in configuration and status information.
* Addition of NVM storage for an upload token (e.g., for an API key).
* "/heartbeat" API endpoint on the logger's WiFi interface now generates a full status message, rather than just the serial number of the logger.
* Console logs are now limited to a fixed (compile-time) size, but will rotate three stages (grandparent-parent-child) to preserve a little more history.
* Scales, metadata, NMEA0183 filters, and algorithm requests are now all stored as JSON data int the NVM, rather than as plain-text files.
* The status command now provides the URL at which to find each log file, as well as size, MD5 hash, ID number, and upload count.
* New command "snapshot" to generate a snapshot of the running configuration, default configuration, or file catalog as files on the SD card so that they can be downloaded to local storage on a mobile device.  The JSON response is the URL at which to find the snapshot.  The internal website implements this functionality through GUI buttons.
* New command "upload" to control auto-upload of log files.
* New command "auth" to control auto-upload authentication artifacts.
* Ability to specify more than one NMEA0183 sentence recognition string in "accept" command in a single command.

Note that this release also updates the command processor version to 1.4.0.
