/*!\file MemController.h
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

#ifndef __MEM_CONTROLLER_H__
#define __MEM_CONTROLLER_H__

#include "FS.h"

namespace mem {

/// \class MemController
/// \brief Abstract interface to start an appropriate controller for the primary storage being used
///
/// Depending on the implemenation of the WIBL logger, it's possible that more than one type of
/// memory might be used for large-scale storage.  This class provides an abstract interface to start
/// and stop the memory system so that specialisations can be made without changing the rest of the
/// code base.

class MemController {
public:
    /// \brief Default (null) constructor
    MemController(void) {}
    /// \brief Default (virtual) constructor
    virtual ~MemController(void) {}

    /// \brief Start the memory interface
    bool Start(void) { return start_interface(); }
    /// \brief Shut down the memory interface
    void Stop(void) { stop_interface(); }
    /// \brief Call-through for the file system abstract used by the memory controller
    fs::FS& Controller(void) { return get_interface(); }
    fs::FS *ControllerPtr(void) { return get_ptr_interface(); }

private:
    /// \brief Implement the code to start the memory interface
    virtual bool start_interface(void) = 0;
    /// \brief Implement the code to stop the memory interface
    virtual void stop_interface(void) = 0;
    /// \brief Return a reference for the file system abstraction implemented by the memory sub-system
    virtual fs::FS& get_interface(void) = 0;
    /// \brief Return a pointer for the file system abstraction implemented by the memory sub-system
    virtual fs::FS *get_ptr_interface(void) = 0;
};

/// \class MemControllerFactory
/// \brief Factory class to construct the appropriate \a MemController interface for the hardware
///
/// This provides a static member that can be used to generate a new instance of the \a MemController
/// interface that's appropriate for the memory sub-system in the current hardware implementation.
/// The pointer passed back is owned by the caller.

class MemControllerFactory {
public:
    /// \brief Construct a new instance of the memory controller object appropriate for the hardware
    static MemController *Create(void);
};

}

#endif
