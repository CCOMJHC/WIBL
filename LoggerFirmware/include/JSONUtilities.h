

#ifndef JSONUTILITIES_H
#define JSONUTILITIES_H

#include <ArduinoJson.h>

inline bool GrowJsonDocumentBy(DynamicJsonDocument & json, size_t capacityIncrease)
{
    auto newCapacity = json.capacity() + capacityIncrease;
    DynamicJsonDocument temp(newCapacity);

    // Allocation failed. Nothing we can do.
    if (temp.capacity() == 0) return false;

    temp.set(json);
    json = std::move(temp);
    return true;
}

inline bool GrowJsonDocument(DynamicJsonDocument & json)
{
    // Double the current capacity.
    return GrowJsonDocumentBy(json, json.capacity());
}

#endif // JSONUTILITIES_H
