/*!\file serial_number.cpp
 * \brief Generate a serial number from the board hardware.
 *
 * This provides a number, or string, for the board serial number, which should be unique within
 * any given production run.  This code was pulled from the NMEA2000 library example for N2K to 0183
 * conversion.
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

#include "serial_number.h"
#include <Arduino.h>

// Code by Mark T from http://forum.arduino.cc/index.php?topic=289190.0

#if defined(__SAM3X8E__)

/// Read the unique identified for the Arduino Due board, using the flash unique identifier register.
///
/// \param pdwUniqueID  Pointer to an array of uint32 to store the unique ID

__attribute__ ((section (".ramfunc")))
void _EEFC_ReadUniqueID(uint32_t* pdwUniqueID) {
    unsigned int status ;

    /* Send the Start Read unique Identifier command (STUI) by writing the Flash Command Register with the STUI command.*/
    EFC1->EEFC_FCR = (0x5A << 24) | EFC_FCMD_STUI;
    do
    {
        status = EFC1->EEFC_FSR ;
    } while ( (status & EEFC_FSR_FRDY) == EEFC_FSR_FRDY ) ;

    /* The Unique Identifier is located in the first 128 bits of the Flash memory mapping. So, at the address 0x400000-0x400003. */
    pdwUniqueID[0] = *(uint32_t *)IFLASH1_ADDR;
    pdwUniqueID[1] = *(uint32_t *)(IFLASH1_ADDR + 4);
    pdwUniqueID[2] = *(uint32_t *)(IFLASH1_ADDR + 8);
    pdwUniqueID[3] = *(uint32_t *)(IFLASH1_ADDR + 12);

    /* To stop the Unique Identifier mode, the user needs to send the Stop Read unique Identifier
       command (SPUI) by writing the Flash Command Register with the SPUI command. */
    EFC1->EEFC_FCR = (0x5A << 24) | EFC_FCMD_SPUI ;

    /* When the Stop read Unique Unique Identifier command (SPUI) has been performed, the
       FRDY bit in the Flash Programming Status Register (EEFC_FSR) rises. */
    do
    {
        status = EFC1->EEFC_FSR ;
    } while ( (status & EEFC_FSR_FRDY) != EEFC_FSR_FRDY ) ;
}

/// Get a unique serial number from the Arduino Due board (SAM3X8E).  The full unique ID is
/// extracted from the flash store, and the first 32-bit is returned as the unique ID.
///
/// \return A unique identifier for the current microcontroller in use

uint32_t GetSerialNumber(void) {
    uint32_t pdwUniqueID[5] ;
    WDT_Disable( WDT ) ;

    _EEFC_ReadUniqueID( pdwUniqueID );

    return pdwUniqueID[0];
}

#elif defined(ARDUINO_ARCH_ESP32) || defined(ESP32)

#include "esp_mac.h"

/// Get a unique serial number from an ESP32 module using the eFuse MAC address.
///
/// \return 32-bit base MAC address for the current ESP32 module

uint32_t GetSerialNumber(void) {
    uint8_t chipid[6];
    esp_efuse_mac_get_default(chipid);
    return chipid[0] + (chipid[1]<<8) + (chipid[2]<<16) + (chipid[3]<<24);
}

#endif

/// Get the board serial number (by the specific code for the microcontroller in use) and convert into
/// a string representation.
///
/// \return Pointer to the internal buffer containing the string representation of the 32-bit unique ID

const char *GetSerialNumberString(void)
{
    uint32_t serial_number = GetSerialNumber();
    static char serial_string[255];
    snprintf(serial_string, 255, "%lu", (long unsigned int)serial_number);
    return (const char *)serial_string;
}
