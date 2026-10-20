/*! \file IMULogger.cpp
 *  \brief Provide interface to log data from an MPU-6050 6-dof IMU.
 *
 * On the NEMO-30 module, there is an embedded MPU-6050 6-dof IMU.  This class uses
 * the Adafruit MPU-6050 interface to talk to the sensor, and to transfer data to the
 * logManager application so that it gets written into the output data files.
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

#include "serialisation.h"
#include "LogManager.h"
#include "LSM6DSL.h"
#include "NVMFile.h"
#include "IMULogger.h"

namespace imu {

const int SoftwareVersionMajor = 1; ///< Software major version for the logger
const int SoftwareVersionMinor = 1; ///< Software minor version for the logger
const int SoftwareVersionPatch = 0; ///< Software patch version for the logger

const int IMUInterruptPin = 39; // Interrupt from LSM6DSL for data ready
const int IMUAddressI2C = 0x6A; // Address on I2C with address pin grounded

// LSM6DSL Registers not defined in the support library
const uint8_t LSM6DSL_DRDY_PULSE_CFG    = 0x0B; // Control for latched/pulsed interrupt
const uint8_t LSM6DSL_CTRL3_C           = 0x12; // Control register 3
const uint8_t LSM6DSL_MASTER_CONFIG     = 0x1A; // Master configuration register
const uint8_t LSM6DSL_STATUS_REGISTER   = 0x1E; // Status register for data ready

// INT1 enabling bits for INT1_CTRL
enum LSM6DSL_INT1_CTRL_BITS {
    LSM6DSL_INT1_CTRL_DRDY_XL   = 0x01, // Accelerometer data ready
    LSM6DSL_INT1_CTRL_DRDY_G    = 0x02, // Gyro data ready
    LSM6DSL_INT1_CTRL_BOOT      = 0x04, // Boot status
    LSM6DSL_INT1_CTRL_FTH       = 0x08, // FIFO threshold
    LSM6DSL_INT1_CTRL_FIFO_OVR  = 0x10, // FIFO over-run
    LSM6DSL_INT1_CTRL_FULL_FLAG = 0x20, // FIFO full
    LSM6DSL_INT1_CTRL_SIGN_MOT  = 0x40, // Significant motion
    LSM6DSL_INT1_CTRL_STEP_DET  = 0x80  // Pedometer step detection
};

// DRDY_PULSE_CFG register (latch/pulse)
enum LSM6DSL_DRDY_PULSE_CFG_BITS {
    LSM6DSL_INT2_WRIST_TILT = 0x01, // Enable wrist-tilt interrupt on INT2
    LSM6DSL_DRDY_PULSED     = 0x80  // Enable DataReady pulses (75us) rather than latched
};

// CTRL3 register bits
enum LSM6DSL_CTRL3_BITS {
    LSM6DSL_CTRL3_SWRESET   = 0x01, // Software reset (if enabled)
    LSM6DSL_CTRL3_BLE       = 0x02, // Big/little endian (0 == LSB first)
    LSM6DSL_CTRL3_IFINC     = 0x04, // Register autoincrement (if enabled)
    LSM6DSL_CTRL3_SIM       = 0x08, // SPI module select (4-wire if 0, 3-wire if 1)
    LSM6DSL_CTRL3_PPOD      = 0x10, // Push-pull (0) or Open-drain (1) INT1/INT2
    LSM6DSL_CTRL3_HLACTIVE  = 0x20, // Interrupt active level (0 = high, 1 = low)
    LSM6DSL_CTRL3_BDU       = 0x40, // Block data update (0 = continuous, 1 = blocked)
    LSM6DSL_CTRL3_BOOT      = 0x80  // Reboot memory (0 = normal, 1 = reboot)
};

// Master configuration register controls
enum LSM6DSL_MASTER_CFG_BITS {
    LSM6DSL_MCFG_SENSOR_HUB_ON          = 0x01, // Sensor hub I2C master enable
    LSM6DSL_MCFG_IRON_CORRECTION        = 0x02, // Hard-iron correction enable
    LSM6DSL_MCFG_PASSTHROUGH            = 0x04, // I2C interface pass-through
    LSM6DSL_MCFG_PULLUP_EN              = 0x08, // Auxiliary I2C pull-up enable
    LSM6DSL_MCFG_START_CONFIG           = 0x10, // Senor hub trigger signal selection
    LSM6DSL_MCFG_DATA_VALID_FIFO_SEL    = 0x40, // FIFO data valid signal selection
    LSM6DSL_MCFG_DRDY_ON_INT1           = 0x80  // Enable master data ready signal on INT1
};

// Status register bits
enum LSM6DSL_STATUS_REGISTER_BITS {
    LSM6DSL_STATUSREG_XLDA      = 0x01, // Accelerometer data ready
    LSM6DSL_STATUSREG_GDA       = 0x02, // Gyroscope data ready
    LSM6DSL_STATUSREG_TDA       = 0x04, // Temperature data ready
    LSM6DSL_STATUSREG_ANYSRC    = 0x07 // Any source of data ready
};

volatile bool imu_data_ready = false;

/// Interrupt service routine for the IMU interrupt, indicating that data is ready at the IMU
/// for reading.  This indicates that the data is ready by setting a global variable that the
/// logger can read.

void IRAM_ATTR IMUDataReady()
{
    imu_data_ready = true;
}

/// Standard constructor for the IMU logger, with output to the specified log manager.
///
/// \param output   Pointer to the log manager to use for output
/// \return N/A

Logger::Logger(logger::Manager *output)
: m_output(output), m_verbose(false)
{
    m_sensor = new LSM6DSL(LSM6DSL_MODE_I2C, IMUAddressI2C);
    
    // After construction of the instance, we can change configuration before the begin()
    m_sensor->settings.gyroRange = 245;         // Full scale degrees per second (must be from known list)
    m_sensor->settings.gyroSampleRate = 13;     // Sampling rate, Hz (must be from known list)
    m_sensor->settings.accelRange = 4;          // Full scale in Gs (must be from known list)
    m_sensor->settings.accelSampleRate = 13;    // Sampling rate, Hz (must be from known list)

    // Set up scale factors for conversion from int16_t at full scale to floating-point value
    m_accelScale = 4.0 / 32767.0;
    m_gyroScale = 245.0 / 32767.0;
    m_tempScale = (1.0 / 256.0);
    m_tempOffset = 25.0;
    logger::ScalesStore scales;
    const char *names[4] = {"recipAccelScale", "recipGyroScale", "recipTempScale", "tempOffset" };
    double values[4] = { 1.0/m_accelScale, 1.0/m_gyroScale, 1.0/m_tempScale, m_tempOffset };
    scales.AddScales("imu", names, values, 4);
    
    if (m_sensor->begin() != IMU_SUCCESS) {
        Serial.println("Failed to initialise LSM6DSL; logging disabled.");
        delete m_sensor;
        m_sensor = nullptr;
        m_output = nullptr;
    } else {
        // Attach an interrupt handler before setting up the external system to cause them
        pinMode(IMUInterruptPin, INPUT);
        attachInterrupt(digitalPinToInterrupt(IMUInterruptPin), IMUDataReady, FALLING);

        // Set up for interrupts so that we don't have to poll for data availability
        m_sensor->writeRegister(LSM6DSL_ACC_GYRO_INT1_CTRL,
                                LSM6DSL_INT1_CTRL_DRDY_G);  // Data ready interrupts from gyros to INT1
        m_sensor->writeRegister(LSM6DSL_CTRL3_C,
                                LSM6DSL_CTRL3_HLACTIVE |    // Active Low
                                LSM6DSL_CTRL3_PPOD |        // Open drain
                                LSM6DSL_CTRL3_IFINC);       // Auto-increment addresses on read
        m_sensor->writeRegister(LSM6DSL_DRDY_PULSE_CFG,
                                LSM6DSL_DRDY_PULSED);       // 75us pulses on interrupt
        m_sensor->writeRegister(LSM6DSL_MASTER_CONFIG,
                                LSM6DSL_MCFG_DRDY_ON_INT1); // Enabled data ready interrupts on INT1
    }
}

/// Standard destructor.  This removes the sensor interface object, hopefully also
/// turning the sensor off.
///
/// \return N/A

Logger::~Logger(void)
{
    delete m_sensor;
}

/// Test the data availability register in the IMU for new data.
///
/// \return True if new data is available, otherwise false

bool Logger::data_available(void)
{
    uint8_t status;
    if (m_sensor->readRegister(&status, LSM6DSL_STATUS_REGISTER) != IMU_SUCCESS) return false;
    return (status & LSM6DSL_STATUSREG_ANYSRC) != 0;
}

float Logger::convert_acceleration(int16_t v)
{
    return v * m_accelScale;
}

float Logger::convert_gyrorate(int16_t v)
{
    return v * m_gyroScale;
}

float Logger::convert_temperature(int16_t t)
{
    return t * m_tempScale + m_tempOffset;
}

/// Get the next sensor reading from the IMU, and write into the output stream.
///
/// \return N/A

void Logger::TransferData(void)
{
    if (m_sensor == nullptr) return;

    int16_t reading[7];
    uint64_t now = m_output->GetElapsedTime();

    if (imu_data_ready && data_available()) {
        if (m_sensor->readFullData(reading) != IMU_SUCCESS) {
            Serial.print("ERR: failed to read from IMU system ... needs investigation.\n");
        } else {
            Serialisable buffer(7*sizeof(int16_t) + sizeof(uint64_t));
            buffer += now;
            for (uint32_t i = 0; i < 7; ++i)
                buffer += reading[i];
            m_output->Record(logger::Manager::PacketIDs::Pkt_RawIMU, buffer);
        }

        imu_data_ready = false;
    }
}

/// Assemble a logger version string
///
/// \return Printable version of the version information

String Logger::SoftwareVersion(void)
{
    String rtn;
    rtn = String(SoftwareVersionMajor) + "." + String(SoftwareVersionMinor) +
            "." + String(SoftwareVersionPatch);
    return rtn;
}

/// Report the versioning information for the logger, primarily so that it can be written
/// into the log file to allow the reader to adapt to the contents during read.
///
/// \param major    Major software version
/// \param minor    Minor software version
/// \param patch    Patch level/build level

void Logger::SoftwareVersion(uint16_t& major, uint16_t& minor, uint16_t& patch)
{
    major = SoftwareVersionMajor;
    minor = SoftwareVersionMinor;
    patch = SoftwareVersionPatch;
}

/// Set the reporting information 
void Logger::SetVerbose(bool verbose)
{
    m_verbose = verbose;
}

}