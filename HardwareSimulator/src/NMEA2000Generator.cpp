/*!\file NMEA2000Simulator.cpp
 * \brief Implement the NMEA2000 simuation data generation.
 *
 * This code is taken from the MessageTalker example in the NMEA2000 library, and is only different
 * in that it is split out here rather than being all in one file.
 *
 */

#include <Arduino.h>
#include <ctime>
#include <NMEA2000_CAN.h>
#include <N2kMessages.h>

namespace nmea2000 {

void SetupInterface(void)
{
    // Reserve enough buffer for sending all messages. This does not work on small memory devices like Uno or Mega
    NMEA2000.SetN2kCANSendFrameBufSize(250);
    // Set Product information
    NMEA2000.SetProductInformation("00000001", // Manufacturer's Model serial code
                                   100, // Manufacturer's product code
                                   "Message sender example",  // Manufacturer's Model ID
                                   "1.0.2.25 (2019-07-07)",  // Manufacturer's Software version code
                                   "1.0.2.0 (2019-07-07)" // Manufacturer's Model version
                                   );
    // Set device information
    NMEA2000.SetDeviceInformation(1, // Unique number. Use e.g. Serial number.
                                  132, // Device function=Analog to NMEA 2000 Gateway. See codes on http://www.nmea.org/Assets/20120726%20nmea%202000%20class%20&%20function%20codes%20v%202.00.pdf
                                  25, // Device class=Inter/Intranetwork Device. See codes on  http://www.nmea.org/Assets/20120726%20nmea%202000%20class%20&%20function%20codes%20v%202.00.pdf
                                  2046 // Just choosen free from code list on http://www.nmea.org/Assets/20121020%20nmea%202000%20registration%20list.pdf                               
                                 );
    // Uncomment 3 rows below to see, what device will send to bus                           
     NMEA2000.SetForwardStream(&Serial);  // PC output on due programming port
     NMEA2000.SetForwardType(tNMEA2000::fwdt_Text); // Show in clear text. Leave uncommented for default Actisense format.
  
    // If you also want to see all traffic on the bus use N2km_ListenAndNode instead of N2km_NodeOnly below
    NMEA2000.SetMode(tNMEA2000::N2km_NodeOnly,22);
    
    NMEA2000.Open();
}

time_t ConvertTime(int year, int month, int day, int hour, int minute, double second)
{
  // The NMEA2000 output is days since 1970-01-01 and seconds since midnight on the day,
  // and therefore we need to convert from our broken out date into that format.  Conveniently,
  // this is also Unix epoch, so we can do this with a couple of library calls.
  int int_seconds = static_cast<int>(second);
  struct tm t;
  t.tm_year = year - 1900;
  t.tm_mon = month - 1;
  t.tm_mday = day;
  t.tm_hour = hour;
  t.tm_min = minute;
  t.tm_sec = int_seconds;
  t.tm_isdst = 0;
  return mktime(&t);
}

void GenerateGNSS(double latitude, double longitude, int year, int month, int day, int hour, int minute, double second)
{
  tN2kMsg msg;
  time_t utc_time = ConvertTime(year, month, day, hour, minute, second);
  
  int days_since_epoch = static_cast<int>(utc_time / 86400);
  

  SetN2kGNSS(msg,1,days_since_epoch,second,latitude,longitude,-19.5,
    N2kGNSSt_GPS,N2kGNSSm_PreciseGNSS,12,1.0,1.0,22.5,1,N2kGNSSt_surveyed,1,1);
  Serial.printf("Sending N2K GNSS: Lat %.6f Lon %.6f Time %04d-%02d-%02d %02d:%02d:%06.3f\n",
                latitude, longitude,
                year, month, day,
                hour, minute, second);
  NMEA2000.SendMsg(msg);
  SetN2kGNSSDOPData(msg,1,N2kGNSSdm_Auto,N2kGNSSdm_Auto,1.0,1.0,1.0);
  Serial.printf("Sending N2K DOP: PDOP %.2f HDOP %.2f VDOP %.2f\n",
                1.0, 1.0, 1.0);
  NMEA2000.SendMsg(msg);
}

void GenerateDepth(double depth)
{
  tN2kMsg msg;
  SetN2kWaterDepth(msg, 1, depth, 0.5, 100.0);
  Serial.printf("Sending N2K Depth: %.2f metres\n", depth);
  NMEA2000.SendMsg(msg);
}

void GenerateSystemTime(int year, int month, int day, int hour, int minute, double second)
{
  tN2kMsg msg;
  time_t utc_time = ConvertTime(year, month, day, hour, minute, second);
  
  int days_since_epoch = static_cast<int>(utc_time / 86400);
  int seconds_of_day = static_cast<int>(utc_time % 86400);

  SetN2kSystemTime(msg,1,days_since_epoch, seconds_of_day);
  Serial.printf("Sending N2K System Time: %04d-%02d-%02d %02d:%02d:%06.3f\n",
                year, month, day,
                hour, minute, second);
  NMEA2000.SendMsg(msg);
}

void ProcessMessages(void)
{
  NMEA2000.ParseMessages();
}

}