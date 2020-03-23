/// \file StatusLED.h
/// \brief Interface for status LED management
///
/// The logger has status LEDs to indicate what it's doing, and things like a full
/// SD card, or bad card, etc.  This code manages the colours and specifics of
/// the system.
///
/// Copyright (c) 2019, University of New Hampshire, Center for Coastal and Ocean Mapping.
/// All Rights Reserved.

#ifndef __STATUS_LED_H__
#define __STATUS_LED_H__

#include <Arduino.h>

#if defined(ARDUINO_ARCH_ESP32) || defined(ESP32)
/// ESP32 GPIO pin to use for the RED indicator LED
#define DEFAULT_RED_LED_PIN 25
/// ESP32 GPIO pin to use for the GREEN indicator LED
#define DEFAULT_GREEN_LED_PIN 26
/// ESP32 GPIO pin to use for the BLUE indicator LED
#define DEFAULT_BLUE_LED_PIN 27
#endif

#if defined(__SAM3X8E__)
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
    StatusLED(int red_ping = DEFAULT_RED_LED_PIN,
              int green_pin = DEFAULT_GREEN_LED_PIN,
              int blue_pin = DEFAULT_BLUE_LED_PIN);
    
    /// \enum Status
    /// \brief Known states that the logger can be in
    enum Status {
        sINITIALISING,  ///< The logger is initialising (probably very brief)
        sNORMAL,        ///< Normal operations
        sCARD_FULL,     ///< The SD card for data is full and needs service
        sFATAL_ERROR    ///< A fatal error has occurred, and the logger needs service
    };
    
    /// \brief Set the status for the LED
    void SetStatus(Status status);
    
    /// \brief Switch state of LED if time period has expired
    void ProcessFlash(void);
    
private:
    int             led_pins[3];        ///< GPIO pin numbers to use for the three LED channels
    boolean         led_state[3];       ///< Flags indicating whether each LED should be on or off
    boolean         led_flasher;        ///< Flag indicating whether the LEDs should be flashing or not
    unsigned long   last_change_time;   ///< Last millis() when the flash status changed
    unsigned long   on_period;          ///< Number of millis() for each flash
    
    /// \enum Colour
    /// \brief Translated version of the states
    enum Colour {
        cINITIALISING,  ///< Colours for initialisation
        cNORMAL,        ///< Colours for normal behaviour
        cCARD_FULL,     ///< Colours for full SD card
        cALARM          ///< Colours for an alarm condition
    };
    
    /// \brief Set the specific colours used for each state, and the flash status
    void SetColour(Colour colour, boolean flash = false);
};

#endif