/*!\file SupplyMonitor.h
 * \brief Interface for NEMO-30 power monitoring
 *
 * The NEMO-30 variant of the logger has the ability to monitor the input power feed
 * so that it can detect when the emergency backup power has kicked in, and therefore
 * turn off the logging for a safe shutdown before it gives out.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#ifndef __SUPPLY_MONITOR_H__
#define __SUPPLY_MONITOR_H__

#include <stdint.h>

namespace logger {

const uint8_t default_monitor_pin = GPIO_NUM_36;    ///< GPIO pin to use for monitoring the supply voltage

/// \class SupplyMonitor
/// \brief Object to check on supply voltage and indicate backup power startup
///
/// In order to know when the main power has been pulled, and the system is working on the backup
/// power provided by the super-capacitor, this class can be used to sample an input pin's voltage
/// and check whether it looks like something acceptable for running the system.  A "true" return from
/// EmergencyPower() indicates that the module should start to shut down immediately, since there
/// isn't a lot of time left.

class SupplyMonitor {
public:
    /// \brief Default constructor, specifying the monitoring pin
    SupplyMonitor(uint8_t monitor_pin = default_monitor_pin);

    /// \brief Sample the voltage on the monitoring pin, and determine whether we're on emergency power
    bool EmergencyPower(void);

private:
    bool    m_monitorPower; ///< Flag: True => power monitoring is happening, False => we don't care about power
    uint8_t m_monitorPin;   ///< GPIO pin being used to monitor the power.
};

}

#endif
