# Release Notes: Logger Firmware

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
