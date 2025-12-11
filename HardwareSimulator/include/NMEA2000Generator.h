/*!\file NMEA2000Simulator.h
 * \brief Provide a simple NMEA2000 simulator engine (from NMEA2000 library examples)
 *
 * This code is an example ("MessageTalker") from the NMEA2000 library source code, which
 * generates sample messages on the CAN bus at appropriate times.  The implementation here,
 * which just splits the code up a little, is custom to this project.
 */

#ifndef __NMEA2000_GENERATOR_H__
#define __NMEA2000_GENERATOR_H__

namespace nmea2000 {

void SetupInterface(void);
void ProcessMessages(void);

void GenerateSystemTime(int year, int month, int day, int hour, int minute, double second);
void GenerateGNSS(double latitude, double longitude, int year, int month, int day, int hour, int minute, double second);
void GenerateDepth(double depth);

}

#endif
