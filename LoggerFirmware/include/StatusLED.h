/*!\file StatusLED.h
 * \brief Interface for status LED management
 *
 * The logger has status LEDs to indicate what it's doing, and things like a full
 * SD card, or bad card, etc.  This code manages the colours and specifics of
 * the system.
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

#ifndef __STATUS_LED_H__
#define __STATUS_LED_H__

#include <Arduino.h>

#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
#ifdef PROTOTYPE_LOGGER

// The prototype logger is made up of standard modules, and an ESP32 development
// module to do the work.  There isn't a lot of use for this now that WIBL exists,
// but it's here for historical reasons.

/// ESP32 GPIO pin to use for the RED indicator LED
#define DEFAULT_RED_LED_PIN 25
/// ESP32 GPIO pin to use for the GREEN indicator LED
#define DEFAULT_GREEN_LED_PIN 26
/// ESP32 GPIO pin to use for the BLUE indiator LED
#define DEFAULT_BLUE_LED_PIN 27

#elif defined(BUILD_NEMO30)

// The NEMO-30 implementation of WIBL uses different LED pins from the standard model
// due to certain pins being required for other purposes with its particular hardware.

/// ESP32 GPIO pin to use for the RED indicator LED
#define DEFAULT_RED_LED_PIN 34
/// ESP32 GPIO pin to use for the GREEN indicator LED
#define DEFAULT_GREEN_LED_PIN 35
/// ESP32 GPIO pin to use for the BLUE indicator LED
#define DEFAULT_BLUE_LED_PIN 32

#else

// The standard setup for WIBL

/// ESP32 GPIO pin to use for the RED indicator LED
#define DEFAULT_RED_LED_PIN     25
/// ESP32 GPIO pin to use for the GREEN indicator LED
#define DEFAULT_GREEN_LED_PIN   26
/// ESP32 GPIO pin to use for the BLUE indicator LED
#define DEFAULT_BLUE_LED_PIN    27
#endif
#endif

#if defined(__SAM3X8E__)

// As a legacy, there is an option to use an Arduino Due for the logger prototype
// (at the breadboard level).

/// Arduino Due GPIO pin to use for the RED indicator LED
#define DEFAULT_RED_LED_PIN 8
/// Arduino Due GPIO pin to use for the GREEN indicator LED
#define DEFAULT_GREEN_LED_PIN 9
/// Arduino Due GPIO pin to use for the BLUE indicator LED
#define DEFAULT_BLUE_LED_PIN 22
#endif

/// \class StatusLED
/// \brief Controller for the status LEDs, translating status to colours/flashes
///
/// The logger can have up to three status LEDs, nominally a common-cathode RGB variety
/// to show the status of the logger (e.g., initialising, normal behaviour, error condition, card full,
/// etc.)  If a RGB led isn't available, separate red and green LEDs give most of the behaviours.

class StatusLED {
public:
    /// \brief Default constructor for the LED manager
    StatusLED(int red_pin = DEFAULT_RED_LED_PIN,
              int green_pin = DEFAULT_GREEN_LED_PIN,
              int blue_pin = DEFAULT_BLUE_LED_PIN);
    
    /// \enum Status
    /// \brief Known states that the logger can be in
    enum Status {
        sINITIALISING,  ///< The logger is initialising (probably very brief)
        sNORMAL,        ///< Normal operations
        sCARD_FULL,     ///< The SD card for data is full and needs service
        sFATAL_ERROR,   ///< A fatal error has occurred, and the logger needs service
        sSTOPPED        ///< Logger is stopped for shutdown
    };
    
    /// \brief Set the status for the LED
    void SetStatus(Status status);
    
    /// \brief Indicate that a data event has occurred
    void TriggerDataIndication(void);
    
    /// \brief Switch state of LED if time period has expired
    void ProcessFlash(void);
    
private:
    int             led_pins[3];        ///< GPIO pin numbers to use for the three LED channels
    boolean         led_state[3];       ///< Flags indicating whether each LED should be on or off
    boolean         led_flasher;        ///< Flag indicating whether the LEDs should be flashing or not
    unsigned long   last_change_time;   ///< Last millis() when the flash status changed
    unsigned long   on_period;          ///< Number of millis() for each flash
    unsigned long   data_next_available;///< Time at which next data indication is allowed
    unsigned long   data_end_time;      ///< Time after which to turn off data light
    unsigned long   data_flash_duration;///< Number of millis() for data event to show
    
    /// \brief Turn on the data LED for an event indication
    void DataLEDOn(void);
    
    /// \brief Turn off the data LED
    void DataLEDOff(void);

    /// \enum Colour
    /// \brief Translated version of the states
    enum Colour {
        cINITIALISING,  ///< Colours for initialisation
        cNORMAL,        ///< Colours for normal behaviour
        cCARD_FULL,     ///< Colours for full SD card
        cALARM,         ///< Colours for an alarm condition
        cSTOPPED        ///< Colours for a stopped logger
    };
    
    /// \brief Set the specific colours used for each state, and the flash status
    void SetColour(Colour colour, boolean flash = false);
};

#endif
