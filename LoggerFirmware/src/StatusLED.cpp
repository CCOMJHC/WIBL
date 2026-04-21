/*!\file StatusLED.cpp
 * \brief Implementation of status LED management
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

#include "StatusLED.h"

#ifdef PROTOTYPE_LOGGER
const boolean ON = HIGH;
const boolean OFF = LOW;
#else
const boolean ON = LOW;     ///< Synonym for common anode LED state being on (i.e., pin driven low)
const boolean OFF = HIGH;   ///< Synonym for common anode LED state being off (i.e., pin driven high)
#endif

/// Constructor for the LED manager.  This configures the manager to have all of the
/// specified pins as output, and turns them off to start with.  The flasher is also disabled,
/// and the on-period is set to 500ms by default.
///
/// \param red_pin      GPIO pin on which to find a red LED
/// \param green_pin    GPIO pin on which to find a green LED
/// \param blue_pin     GPIO pin on which to find a blue LED

StatusLED::StatusLED(int red_pin, int green_pin, int blue_pin)
{
    led_pins[0] = red_pin;
    led_pins[1] = green_pin;
    led_pins[2] = blue_pin;
    
    for (int i = 0; i < 3; ++i) {
        pinMode(led_pins[i], OUTPUT);
        led_state[i] = OFF;
        digitalWrite(led_pins[i], led_state[i]);
    }
    led_flasher = false;
    
    last_change_time = 0;
    on_period = 500; // milliseconds
    
    data_end_time = 0;
    data_flash_duration = 100;  // milliseconds
}

/// Set the specific colours and flash pattern for any given state.  This translates the state
/// descriptors into specific colours, and sets up the flasher logic if required.  Note that there
/// is no way to have one LED stable and the others flashing if multiple LEDs are used (the
/// target model is a single common-cathode RGB LED).
///
/// \param colour   Status indicator to set
/// \param flash    Flag: true implies the LED will be flashing

void StatusLED::SetColour(Colour colour, boolean flash)
{
    switch(colour) {
        case Colour::cINITIALISING:
            led_state[0] = ON; led_state[1] = ON; led_state[2] = ON; /* White */
            break;
        case Colour::cNORMAL:
            led_state[0] = OFF; led_state[1] = ON; led_state[2] = OFF; /* Green */
            break;
        case Colour::cCARD_FULL:
            led_state[0] = OFF; led_state[1] = ON; led_state[2] = ON; /* Green/Blue (i.e., working, but card's full) */
            break;
        case Colour::cALARM:
            led_state[0] = ON; led_state[1] = OFF; led_state[2] = OFF; /* Red (Or Yellow, depending on build) */
            break;
        case Colour::cSTOPPED:
            led_state[0] = OFF; led_state[1] = OFF; led_state[2] = ON; /* Blue, typically */
    }
    led_flasher = ON;
    if (flash) {
        last_change_time = millis();
    } else {
        last_change_time = 0;
    }
}

/// User-level code to set up the status indicator LED.  This turns on the appropriate
/// flashing state for the LEDs, and translates the status to colour options.
///
/// \param status   Status to set

void StatusLED::SetStatus(Status status)
{
    switch (status) {
        case Status::sINITIALISING:
            SetColour(Colour::cINITIALISING);
            break;
        case Status::sNORMAL:
            SetColour(Colour::cNORMAL);
            break;
        case Status::sCARD_FULL:
            SetColour(Colour::cCARD_FULL, true);
            break;
        case Status::sFATAL_ERROR:
            SetColour(Colour::cALARM, true);
            break;
        case Status::sSTOPPED:
            SetColour(Colour::cSTOPPED);
            break;
    }
    ProcessFlash();
}

/// Turn on some indication that a data event has occurred; depending on the system, this could
/// be a flash of one or more LEDs.

void StatusLED::TriggerDataIndication(void)
{
    DataLEDOn();
    data_end_time = millis() + data_flash_duration;
}

/// Turn on the data LED (whatever that means for the current board)

void StatusLED::DataLEDOn(void)
{
    led_state[2] = ON;
    digitalWrite(led_pins[2], led_state[2]);
}

/// Turn off the data LED (whatever that means for the current board)

void StatusLED::DataLEDOff(void)
{
    led_state[2] = OFF;
    digitalWrite(led_pins[2], led_state[2]);
}

/// User-level code to operate the flashing functionality of the LED(s), if configured for
/// the current state.  Since the Arduino environment is single-threaded, we can't spin off
/// another thread to manage the flashing on a regular basis, so it's important that this code
/// is called regularly, and at least as often as the on-period (by default 500ms).  If this
/// code is not called appropriately often, the LED(s) will not flash, or will flash irregularly,
/// which is not ideal.  Calling this in loop() is appropriate.

void StatusLED::ProcessFlash(void)
{
    if (last_change_time > 0) {
        // This implies that we are flashing the LED
        if ((last_change_time + on_period) < millis()) {
            // Only do anything if we've hit the time marker
            last_change_time = millis();
            if (led_flasher == ON) {
                led_flasher = OFF;
            } else {
                led_flasher = ON;
            }
            for (int i = 0; i < 3; ++i) {
                if (led_flasher == ON && led_state[i] == ON)
                    digitalWrite(led_pins[i], ON);
                else
                    digitalWrite(led_pins[i], OFF);
            }
        }
    } else {
        // If we're not flashing, we just set the LED state
        for (int i = 0; i < 3; ++i) {
            digitalWrite(led_pins[i], led_state[i]);
        }
    }
    if (data_end_time > 0) {
        // This implies that we've indicated a data event, so we need to check whether
        // it's time to turn the LED off again.
        if (data_end_time < millis()) {
            DataLEDOff();
            data_end_time = 0;
        }
    }
}
