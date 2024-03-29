/*! \file IncrementalBuffer.h
 * \brief Declare a buffer to accumulate strings until a full sentence is available.
 *
 * This is a base class for use in accumulating strings of characters from the NMEA0183
 * interface, and from the serial interface so that you can handle them as a single entity,
 * rather than character by character.
 *
 * Copyright (c) 2020, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

#include <stdint.h>

#ifndef __INCREMENT_BUFFER_H__
#define __INCREMENT_BUFFER_H__

namespace logger {

/// \class IncBuffer
/// \brief Assemble a sentence from character input
///
/// This object allows the code to accumulate a sentence into a buffer one character at a time,
/// so that it can then be pulled out for processing.

class IncBuffer {
public:
    static const int DEFAULT_MAX_SENTENCE_LENGTH = 128; ///< Maximum is probably order 100 characters; this is safe
    
    /// \brief Default constructor, just resetting the buffer insertion point
    IncBuffer(uint32_t max_stencence_length = DEFAULT_MAX_SENTENCE_LENGTH)
    : m_bufferLength(max_stencence_length)
    {
        m_sentence = new char[m_bufferLength];
        Reset();
    }

    /// \brief Default destructor
    ~IncBuffer(void)
    {
        delete m_sentence;
    }
    
    /// \brief Add a new character into the buffer, with length management
    ///
    /// This adds the specified character into the buffer, making sure that there is space
    /// for it beforehand.
    ///
    /// \param a    Character to add
    /// \return True if the character was added, otherwise False
    
    bool AddCharacter(char const a)
    {
        if (m_insertPoint < m_bufferLength-1) {
            m_sentence[m_insertPoint++] = a;
            return true;
        }
        return false;
    }

    /// \brief Remove the last character in the buffer, if there is one
    ///
    /// This removes the last character added, so that you can backspace and keep a valid
    /// buffer to send to the command processor later.

    void RemoveLastCharacter(void)
    {
        if (m_insertPoint > 0) {
            m_sentence[--m_insertPoint] = '\0';
        }
    }
    
    /// \brief Reset the current sentence, going back to zero length
    ///
    /// This resets the buffer to zero contents, invalidates the timestamp, and sets the insertion
    /// point back to zero, effectively removing the old data without having to reconstruct.

    virtual void Reset(void)
    {
        bzero(m_sentence, m_bufferLength);
        m_insertPoint = 0;
    }

    /// \brief Reset the size of the buffer to the length given
    ///
    /// If, at compile time, you don't know what length you need in the buffer, this code
    /// can be used to reset the length to the runtime size required.  Note that this will also
    /// remove anything that's currently in the buffer, and reset the insertion point.
    ///
    /// \param  max_len Maximum length of the buffer to set

    void ResetLength(uint32_t max_len)
    {
        delete m_sentence;
        m_sentence = new char[max_len];
        m_bufferLength = max_len;
        Reset();
    }
    
    /// \brief Provide a pointer to the current sentence in the buffer
    char const *Contents(void) const { return m_sentence; }
    /// \brief Provide a legnth-count for the current contents of the buffer
    int Length(void) const { return m_insertPoint; }
    /// \brief Provide a count for the maximum possible sentence length
    int MaxLength(void) const { return m_bufferLength; }
    
protected:
    /// \brief Getter for the current insertion point in the buffer
    int InsertPoint(void) const { return m_insertPoint; }
    /// \brief Value in the buffer at the specified point
    char BufferChar(uint32_t pt) const { return m_sentence[pt]; }
    
private:
    uint32_t    m_bufferLength; ///< Length of the buffer to assemble sentences
    char        *m_sentence;    ///< Sentence assembly space
    uint32_t    m_insertPoint;  ///< Location for next character to be placed in the buffer
};

}

#endif
