/*! \file ydvr_decoder.cpp
 *  \brief CLI driver to read Yacht Devices DAT files and convert to another foramt.
 *
 *  This code is used to parse Yacht Devices DAT files from the YDVR04 NMEA2000 data logger,
 *  and then transcode to another, more useful, format.  The intent is to use this for debugging
 *  of the logger, but also to provide means to convert volunteer data for archives such as the
 *  IHO Data Center for Digital Bathymetry at NCEI Boulder.
 *
 * Copyright (c) 2021, University of New Hampshire, Center for Coastal and Ocean Mapping and
 * NOAA/UNH Joint Hydrographic Center.  All Rights Reserved.
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this software
 * and associated documentation files (the "Software"), to deal in the Software without restriction,
 * including without limitation the rights to use, copy, modify, merge, publish, distribute,
 * sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is
 * furnished to do so, subject to the following conditions:
 *
 * The above copyright notice and this permission notice shall be included in all copies or
 * substantial portions of the Software.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING
 * BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
 * NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM,
 * DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 * OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
*/

#include <cstdio>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "boost/program_options.hpp"
#include "boost/format.hpp"
namespace po = boost::program_options;

#include "YDVRSource.h"
#include "TeamSurvSource.h"
#include "N2kMessages.h"
#include "NMEA2000.h"
#include "serialisation.h"
#include "SerialisableFactory.h"

const char *version = "1.2.0";

/// Dummy code to allow the system to pretend that there's a millisecond counter
///
/// \return Nominally the millisecond counter since boot; there, uniformly zero
uint32_t millis(void)
{
    return 0;
}

const std::map<uint32_t, std::string> pgn_lut(
{   {59392, "ISO ACK" },
    {59904, "ISO REQ" },
    {60928, "ISO Address" },
    {126208, "RequestGroupFunction" },
    {126464, "TxRxPGNListGroup" },
    {126992, "SystemTime" },
    {126996, "ProductInfo" },
    {127245, "Rudder" },
    {127250, "Heading" },
    {127251, "RateOfTurn" },
    {127257, "Attitude" },
    {127258, "MagneticVariation" },
    {127488, "EngineParamRapid" },
    {127489, "EngineParamDynamic" },
    {127493, "TransmissionParam" },
    {127497, "EngineTripParam" },
    {127501, "BinaryStatus" },
    {127505, "FluidLevel" },
    {127506, "DCStatus" },
    {127507, "ChargerStatus" },
    {127508, "BatteryStatus" },
    {127513, "BatteryConfig" },
    {128000, "Leeway" },
    {128259, "BoatSpeed" },
    {128267, "WaterDepth" },
    {128275, "DistanceLog" },
    {129025, "PositionRapid" },
    {129026, "COGSOGRapid" },
    {129029, "GNSS" },
    {129033, "LocalOffset" },
    {129039, "AISClassBPosition" },
    {129040, "AISClassBPosExt" },
    {129291, "SetDriftRapid" },
    {129539, "GNSSDOP" },
    {129540, "GNSSSatsInView" },
    {129542, "GNSSNoiseStats" },
    {129547, "GNSSErrorStats" },
    {129038, "AISClassAPosition" },
    {129039, "AISClassBPosition" },
    {129283, "CrossTrackError" },
    {129284, "NavigationInfo" },
    {129285, "WaypointList" },
    {129794, "AISClassAStatic" },
    {129808, "DSCCallInfo" },
    {129809, "AISClassBStaticA" },
    {129810, "AISClassBStaticB" },
    {130074, "AppendWaypointList" },
    {130306, "WindSpeed" },
    {130310, "OutsideEnvironment" },
    {130311, "Environment" },
    {130312, "Temperature" },
    {130313, "Humidity" },
    {130314, "Pressure" },
    {130315, "SetPressure" },
    {130316, "Temperature" },
    {130576, "TrimTabPosition" },
    {130577, "DirectionData" }
});

/// Construct a text string name for a given packet PGN.  This attempts to translate
/// into a human-comprehendable packet name if the packet is a known NMEA2000 type,
/// but will fabricate a name from the PGN otherwise.
///
/// \param pgn          Packet PGN to translate
/// \param is_nmea2000  Flag: true if the packet is known to be NMEA2000
/// \return String with a reportable name for the packet

std::string NamePacket(uint32_t pgn, bool is_nmea2000)
{
    std::string rtn;
    if (is_nmea2000) {
        try {
            rtn = pgn_lut.at(pgn);
        }
        catch(...) {
            rtn = "Unknown";
        }
    } else {
        char tag[4];
        tag[0] = (char)((pgn >> 16) & 0xFF);
        tag[1] = (char)((pgn >> 8) & 0xFF);
        tag[2] = (char)(pgn & 0xFF);
        tag[3] = '\0';
        rtn = std::string(tag);
    }
    return rtn;
}

std::string NameOutputPacket(uint32_t packet_id)
{
    std::vector<std::string> names {"Version", "SystemTime", "Attitude", "Depth", "Course Over Ground", "GNSS", "Environment", "Temperature", "Humidity", "Pressure", "NMEA-0183 Sentence", "Local IMU Data", "Base Metadata", "Algorithm Request", "JSON Metadata Definition", "NMEA-0183 Sentence Filters", "Sensor Scales", "Raw IMU Data", "Setup Configuration"};
    std::string rtn;
    if (packet_id >= names.size()) {
        rtn = std::string("Not Known");
    } else {
        rtn = names[packet_id];
    }
    return rtn;
}

/// Report to the user the syntax for the conversion tool
///
/// \param cmdopt   Boost command-line options structure with parameter settings

void Syntax(po::options_description const& cmdopt)
{
    std::cout << "logconvert [" << __DATE__ << ", " << __TIME__ << "] v." << version
              << " - Convert VGI log output to WIBL for upload." << std::endl;
    std::cout << "  Serialiser Version: " << SerialiserVersionMajor << "." << SerialiserVersionMinor << std::endl;
    std::cout << "Syntax: logconvert [opt] <input><output>" << std::endl;
    std::cout << cmdopt << std::endl;
}

/// Constructor for the PacketSource derivative to use, given the user's description string.  This
/// simply checks for exact matches against the list of known formats:
///     ydvr|YDVR           Yacht Devices YDVR-4 files in proprietary (but documents) DAT format
///     teamsurv|TeamSurv   TeamSurv "tab separated" (but actually plain ASCII) NMEA0183 strings
/// and makes the appropriate sub-class, casting back to base for uniform handling in the rest of
/// the code.
///
/// \param format   Format recognition string, typically from the end-user's command line
/// \param in       Pointer to the file to read from (must be opened in binary mode if NMEA2000 data)
/// \return PacketSource pointer to use for the specified input file and format

PacketSource *GeneratePacketSource(std::string const& format, FILE *in)
{
    PacketSource *rtn = nullptr;
    
    if (format == "ydvr" || format == "YDVR") {
        rtn = new YDVRSource(in);
    } else if (format == "teamsurv" || format == "TeamSurv") {
        rtn = new TeamSurvSource(in);
    } // No additional else clause --- returns nullptr if the source is not recognised.
    
    return rtn;
}

/// Each NMEA2000 talker contains a lot of information on the type of device, model version, software code,
/// etc.  This routine breaks out that information, and reports on a standard FILE output stream.  This can
/// be very useful in identifying talkers that should not be generating data (which can then be ignored if
/// required).
///
/// \param msg  NMEA2000 message (PGN 126996) with product information
/// \param out  File on which to write broken-out data

void ReportProductInformation(tN2kMsg const& msg, FILE *out)
{
    const int string_buffer_sizes = 255;
    unsigned short n2k_version, product_code;
    unsigned char cert_level, load_equiv;
    char model_id[string_buffer_sizes], sw_code[string_buffer_sizes],
         model_version[string_buffer_sizes], model_serial_code[string_buffer_sizes];
    
    int Index=0;
    n2k_version = msg.Get2ByteUInt(Index);
    product_code = msg.Get2ByteUInt(Index);
    msg.GetStr(string_buffer_sizes,model_id,Max_N2kModelID_len,0xff,Index);
    msg.GetStr(string_buffer_sizes,sw_code,Max_N2kSwCode_len,0xff,Index);
    msg.GetStr(string_buffer_sizes,model_version,Max_N2kModelVersion_len,0xff,Index);
    msg.GetStr(string_buffer_sizes,model_serial_code,Max_N2kModelSerialCode_len,0xff,Index);
    cert_level = msg.GetByte(Index);
    load_equiv = msg.GetByte(Index);
    
    fprintf(out, "Product Information for source %d:\n", msg.Source);
    fprintf(out, " NMEA2000 Version:\t%hd\n", n2k_version);
    fprintf(out, " Product code:\t\t%hd\n", product_code);
    fprintf(out, " Model ID:\t\t%s\n", model_id);
    fprintf(out, " Software Code:\t\t%s\n", sw_code);
    fprintf(out, " Model Version:\t\t%s\n", model_version);
    fprintf(out, " Model Serial Code:\t%s\n", model_serial_code);
    fprintf(out, " Certification Level:\t%d\n", (uint32_t)cert_level);
    fprintf(out, " Load Equivalent:\t%d\n\n", (uint32_t)load_equiv);
}

int main(int argc, char **argv)
{
    // Get command line options
    po::options_description cmdopt("Options");
    cmdopt.add_options()
        ("help,h", "Generate syntax list")
        ("input,i",         po::value<std::string>(),           "Specify input log file")
        ("output,o",        po::value<std::string>(),           "Specify output WIBL file")
        ("name,n",          po::value<std::string>(),           "Specify logger name string")
        ("id",              po::value<std::string>(),           "Specify logger unique ID string")
        ("metadata,m",      po::value<std::string>(),           "Provide a JSON-formatted metadata for the platform")
        ("format,f",        po::value<std::string>(),           "Specify the format of the input file")
        ("stats,s",                                             "Show detailed packet statistics")
        ("ignore",          po::value<std::vector<uint32_t>>(), "Ignore one or more data source senders")
        ("prodinfo,p",      po::value<std::string>(),           "Write product information messages to file")
        ;
    po::positional_options_description cmdline;
    cmdline.add("input", 1);
    cmdline.add("output", 1);
    
    po::variables_map optvals;
    po::store(po::command_line_parser(argc, argv).options(cmdopt).positional(cmdline).run(), optvals);
    po::notify(optvals);
    
    bool show_statistics = false;
    std::set<uint32_t>  reject_sources;
    FILE *prod_info_file = nullptr;
    
    // Check on command line parameters that are mandatory
    if (optvals.count("help")) {
        Syntax(cmdopt);
        return 1;
    }
    
    if (optvals.count("input") != 1) {
        std::cout << "error: need an input file." << std::endl;
        return 1;
    }
    if (optvals.count("output") != 1) {
        std::cout << "error: need an output file." << std::endl;
        return 1;
    }
    if (optvals.count("format") != 1) {
        std::cout << "error: need an input format specified." << std::endl;
        return 1;
    }
    if (optvals.count("stats") == 1) {
        show_statistics = true;
    }
    if (optvals.count("ignore") > 0) {
        auto ign = optvals["ignore"].as<std::vector<uint32_t>>();
        for (auto it = ign.begin(); it != ign.end(); ++it) {
            reject_sources.insert(*it);
        }
    }
    if (optvals.count("prodinfo") != 0) {
        prod_info_file = fopen(optvals["prodinfo"].as<std::string>().c_str(), "w");
    }

    FILE *in = fopen(optvals["input"].as<std::string>().c_str(), "rb");
    FILE *out = fopen(optvals["output"].as<std::string>().c_str(), "wb");
    std::string log_format(optvals["format"].as<std::string>().c_str());
    
    std::string logger_name("UNKNOWN"), logger_id("UNKNOWN");
    std::string metadata;
    if (optvals.count("name") != 0) {
        logger_name = optvals["name"].as<std::string>();
    }
    if (optvals.count("id") != 0) {
        logger_id = optvals["id"].as<std::string>();
    }
    if (optvals.count("metadata") != 0) {
        metadata = optvals["metadata"].as<std::string>();
    }
    
    PacketSource *source = GeneratePacketSource(log_format, in);
    if (source == nullptr) {
        std::cout << "error: failed to generate packet source for input format \"" << log_format << "\"." << std::endl;
        return 1;
    }
    
    tN2kMsg msg;
    
    uint32_t elapsed_time;
    std::string sentence;
    
    uint32_t n_packets = 0;
    uint32_t n_control_packets = 0;
    uint32_t n_bad_packets = 0;
    uint32_t n_conversions = 0;
    uint32_t n_rejected = 0;
    std::map<uint32_t, uint32_t> packet_counts, packet_counts_by_source, source_count;
    std::set<uint32_t> product_info;
    
    Version n2k(1, 1, 0);
    Version n1k(1, 0, 1);
    Version imu(1, 0, 0);

    bool noDataReject_done = false;
    uint32_t no_data_packets = 0;
    std::map<uint32_t, uint32_t> noData_packet_by_type;
    
    StdSerialiser ser(out, n2k, n1k, imu, logger_name, logger_id);
    if (!metadata.empty()) {
        PayloadID metadata_id;
        std::shared_ptr<Serialisable> metadata_payload = SerialisableFactory::Convert(metadata, metadata_id);
        if (!ser.Process(metadata_id, metadata_payload)) {
            std::cout << "error: could not generate metadata packet on output." << std::endl;
            exit(1);
        }
    }
    
    if (source->IsN2k()) {
        while (source->NextPacket(msg)) {
            packet_counts[msg.PGN]++;
            
            uint32_t pkt_tag = (uint32_t)msg.PGN << 8 | ((uint32_t)msg.Source & 0xFF);
            packet_counts_by_source[pkt_tag]++;
            source_count[(uint32_t)msg.Source]++;

            if (msg.PGN == 126996 &&
                prod_info_file != nullptr &&
                product_info.find((uint32_t)msg.Source) == product_info.end()) {
                product_info.insert((uint32_t)msg.Source);
                ReportProductInformation(msg, prod_info_file);
            }
            
            if (msg.PGN == 0xFFFFFFFF)
                ++n_control_packets;
                        
            ++n_packets;
            
            if (reject_sources.find((uint32_t)msg.Source) == reject_sources.end()) {
                PayloadID payload_id;
                bool no_data_detected = false;
                std::shared_ptr<Serialisable> pkt = SerialisableFactory::Convert(msg, payload_id, no_data_detected);
                if (no_data_detected) {
                    ++no_data_packets;
                    noData_packet_by_type[pkt_tag]++;
                    if (!noDataReject_done) {
                        std::cerr << "warning: generating algorithm request for 'nodatareject' due to bad data." << std::endl;
                        std::shared_ptr<Serialisable> alg_req = std::make_shared<Serialisable>(255);
                        std::string alg("nodatareject");
                        std::string params("phase=raw");
                        *alg_req += (uint32_t)alg.length();
                        *alg_req += alg.c_str();
                        *alg_req += (uint32_t)params.length();
                        *alg_req += params.c_str();
                        ser.Process(Pkt_AlgorithmRequest, alg_req);
                        noDataReject_done = true;
                    }
                }
                if (pkt) {
                    ++n_conversions;
                    if (!ser.Process(payload_id, pkt)) {
                        ++n_bad_packets;
                    }
                }
            } else {
                ++n_rejected;
            }
        }
    } else {
        while (source->NextPacket(elapsed_time, sentence)) {
            ++n_packets;
            uint32_t tag = (uint32_t)sentence[3]<<16 | (uint32_t)sentence[4]<<8 | (uint32_t)sentence[5];
            packet_counts[tag]++;
            PayloadID payload_id;
            std::shared_ptr<Serialisable> pkt = SerialisableFactory::Convert(elapsed_time, sentence, payload_id);
            if (pkt) {
                ++n_conversions;
                if (!ser.Process(payload_id, pkt)) {
                    ++n_bad_packets;
                }
            }
        }
    }
    
    fclose(in);
    fclose(out);
    
    printf("Total:\t\t%8d packets read, of which %d control packets\n", n_packets, n_control_packets);
    printf("Rejected:\t%8d packets by user ignore list (%lu sources", n_rejected, reject_sources.size());
    if (!source_count.empty()) {
        printf(": IDs");
        for (auto it = reject_sources.begin(); it != reject_sources.end(); ++it) {
            printf(" %d", *it);
        }
    }
    printf(")\n");
    printf("Conversions:\t%8d packets attempted, %d failed to write\n", n_conversions, n_bad_packets);
    printf("Unique packets:\t%8lu\n", packet_counts.size());
    if (no_data_packets > 0) {
        printf("NoData Packets:\t%8d consisting of:\n", no_data_packets);
        printf("       Packet ID   Sender ID  Count Packet Name\n");
        printf("    -------------- --------- ------ ------------------\n");
        for (auto it = noData_packet_by_type.begin(); it != noData_packet_by_type.end(); ++it) {
            uint32_t sender = it->first & 0xFF;
            uint32_t pgn = (it->first >> 8) & 0xFFFFF;
            printf("    %05X [%06u] %9d %6d %s\n", pgn, pgn, sender, it->second, NamePacket(pgn, true).c_str());
        }
    }
    
    if (show_statistics) {
        printf("\nTotal Packet Counts (All Senders):\n");
        printf("\n  Packet ID   \tCount  Packet Name\n");
        printf("--------------\t------ -----------------------\n");
        for (auto it = packet_counts.begin(); it != packet_counts.end(); ++it) {
            printf("%05X [%06u]\t%6d %s\n", it->first & 0xFFFFF, it->first & 0xFFFFF, it->second, NamePacket(it->first, source->IsN2k()).c_str());
        }
        
        printf("\nSource #Packets\n");
        printf("------ --------\n");
        for (auto it = source_count.begin(); it != source_count.end(); ++it) {
            printf("%6d %8d\n", it->first, it->second);
        }
        
        printf("\nPacket Counts by Sender:\n");
        printf("\n  Packet ID   \tSender\tCount  Packet Name\n");
        printf("______________\t______\t______ -----------------------\n");
        for (auto it = packet_counts_by_source.begin(); it != packet_counts_by_source.end(); ++it) {
            uint32_t sender = it->first & 0xFF;
            uint32_t pgn = (it->first >> 8) & 0xFFFFF;
            printf("%05X [%06u]\t%6d\t%6d %s\n",pgn, pgn, sender, it->second, NamePacket(pgn, source->IsN2k()).c_str());
        }
        
        printf("\nSource Packet Inventory:\n");
        for (auto it = source_count.begin(); it != source_count.end(); ++it) {
            uint32_t sender = it->first, n_unknown = 0;
            printf("%3d: ", sender);
            uint32_t n_out = 0;
            for (auto itp = packet_counts_by_source.begin(); itp != packet_counts_by_source.end(); ++itp) {
                uint32_t pkt_sender = itp->first & 0xFF;
                if (pkt_sender != sender) continue;
                uint32_t pkt_pgn = (itp->first >> 8) & 0xFFFFF;
                std::string packet_name = NamePacket(pkt_pgn, source->IsN2k());
                if (packet_name == "Unknown") {
                    n_unknown++;
                    continue;
                }
                printf("%-25s", NamePacket(pkt_pgn, source->IsN2k()).c_str());
                ++n_out;
                if ((n_out % 3) == 0) {
                    printf("\n     ");
                }
            }
            printf("(+%d Unknown)\n", n_unknown);
        }
    }
    delete source;
    return 0;
}
