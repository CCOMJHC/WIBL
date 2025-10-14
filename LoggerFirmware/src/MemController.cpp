/*!\file MemController.cpp
 * \brief Abstract interface to start the memory system used for log files
 *
 * Depending on the configuration of the logger, the code can write to either an SD card
 * using the SPI interface, or to an eMMC chip using the SDIO/MMC interface.  This object
 * starts the right Arduino interface components for the appropriate system so the main
 * code doesn't have to work this out.
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

#define LOG_LOCAL_LEVEL ESP_LOG_VERBOSE
#include "esp_log.h"

#include "MemController.h"
#include "FS.h"
#include "SD.h"
#include "SPI.h"
#include "SD_MMC.h"
#include "Configuration.h"
#include "eMMCController.h"

namespace mem {

const uint8_t default_cs_pin = 5;   ///< Pin used to control selection of the SD card when in SPI mode

/// \class SPIController
/// \brief Specialisation of the MemController interface for SPI bus
///
/// This assumes that the SPI bus used is the VSPI default, which is what's used on NEMO-30.  This means
/// that no specialist configuration is required to bring up the system.

class SPIController : public MemController {
public:
    /// \brief Default constructor
    ///
    /// This stores the pin to use for Chip Select (CS*) when accessing the SD card, but otherwise
    /// does not access the card.
    ///
    /// \param cs_pin   GPIO pin number to use for chip select when accessing the SPI card

    SPIController(uint8_t cs_pin = default_cs_pin)
    : m_csPin(cs_pin)
    {
    }

    /// \brief Default destructor

    ~SPIController(void)
    {
    }

private:
    uint8_t    m_csPin; ///< GPIO pin number to use for chip select

    /// \brief Start up the SPI interface to get to SD card online
    ///
    /// This initialises the SPI interface, using the CS pin specified at construction, allowing for
    /// a few repetitions (which are sometimes required, according to Dr. Google) for the chip to
    /// reset and restart.
    ///
    /// \return True if the interface started, otherwise False

    bool start_interface(void)
    {
        // By default, the interface chosen for SPI is the ESP32's VSPI, which is what NEMO-30 uses,
        // so we don't need to configure the SPI interface to make this work.

        bool rc = false;
        int rep = 0;
        while (rep < 10 && !rc) {
            Serial.printf("DBG: repeat %d for SD start ...\n", rep);
            rc = SD.begin(m_csPin);
            ++rep;
        }
        return rc;
    }

    /// \brief Shut down SPI interface.
    void stop_interface(void)
    {
        SD.end();
    }

    /// \brief Return a reference to the SPI interface being used.
    fs::FS& get_interface(void)
    {
        return SD;
    }

    /// \brief Return a pointer to the SPI interface being used.
    fs::FS *get_ptr_interface(void)
    {
        return &SD;
    }
};

/// \class MMCController
/// \brief Specialisation of the MemController interface for SD/MMC modules
///
/// This provides an interface to configure and start up an SD/MMC module, either an
/// SD card configured on the SD/MMC interface (higher speed, 4-bit), or an eMMC module,
/// if available (only supported on NEMO30).

class MMCController : public MemController {
public:
    /// \brief Default constructor
    MMCController(void)
    {
#ifdef BUILD_NEMO30
        m_eMMCController = new nemo30::eMMCController();
        m_eMMCController->setModuleStatus(true); // Enable CMD line to module
        m_eMMCController->resetModule();
#endif
    }

    /// \brief Default destructor
    ~MMCController(void)
    {
#ifdef BUILD_NEMO30
        delete m_eMMCController;
#endif
    }

private:
#ifdef BUILD_NEMO30
    nemo30::eMMCController  *m_eMMCController;  ///< Pointer to the eMMC module's hardware interface
#endif

    /// \brief Start up the SD/MMC interface
    ///
    /// This starts the interface, bringing the storage online
    ///
    /// \return True if the module initialised, otherwise False

    bool start_interface(void)
    {
        return SD_MMC.begin();
    }

    /// \brief Stop the SD/MMC interface
    ///
    /// This should stop the interface and idle the storage, but since the interface controller is
    /// always allocated, this may not recover memory.

    void stop_interface(void)
    {
        SD_MMC.end();
    }

    /// \brief Return a reference to the interface in use.
    fs::FS& get_interface(void)
    {
        return SD_MMC;
    }

    /// \brief Return a pointer to the interface in use.
    fs::FS *get_ptr_interface(void)
    {
        return &SD_MMC;
    }
};

/// All WIBL-based loggers have to provide some large-scale storage for the logged data, but the particular
/// interface on which that storage is provided can change.  This provides a mechanism to abstact away the
/// details of the interfacing by providing a uniform MemController pointer to use for control.
///
/// \return Pointer to the appropriate MemController sub-class to use for the current hardware.

MemController *MemControllerFactory::Create(void)
{
    bool use_sdio;
    MemController *rc = nullptr;

    if (!logger::LoggerConfig.GetConfigBinary(logger::Config::ConfigParam::CONFIG_SDMMC_B, use_sdio)) {
#ifdef PROTOTYPE_LOGGER
        Serial.println("ERR: prototype logger, setting VSPI SD interface.");
        use_sdio = false;
#else
        Serial.println("ERR: memory module interface not recognised!  Using SDIO.");
        use_sdio = true;
#endif
    }
    use_sdio = true;
    if (use_sdio) {
        Serial.println("Starting SD/MMC interface.");
        rc = new MMCController();
    } else {
        Serial.println("Starting SPI interface.");
        rc = new SPIController();
    }
    return rc;
}

}