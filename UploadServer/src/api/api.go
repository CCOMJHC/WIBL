/*! @file api.go
 * @brief Specification for types used in the interaction between the client and server
 *
 * WIBL loggers that are going to upload files to the server send a system status message as
 * the first phase of the transaction, and then send data files.  This file specifies the
 * internal and JSON encoding of the status message that's sent to the server.
 *
 * Copyright (c) 2024, University of New Hampshire, Center for Coastal and Ocean Mapping.
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

package api

type VersionInfo struct {
	Firmware         string `json:"firmware"`
	CommandProcessor string `json:"commandproc"`
	NMEA0183         string `json:"nmea0183"`
	NMEA2000         string `json:"nmea2000"`
	IMU              string `json:"imu"`
	Serialiser       string `json:"serialiser"`
}

type WebServerInfo struct {
	CurrentStatus string `json:"current"`
	BootStatus    string `json:"boot"`
}

type DataSentence struct {
	Name      string  `json:"name"`
	Tag       string  `json:"tag"`
	Time      float64 `json:"time"`
	TimeUnits string  `json:"time_units"`
	Display   string  `json:"display"`
}

type DataInfo struct {
	Count  uint           `json:"count"`
	Detail []DataSentence `json:"detail"`
}

type DataSummary struct {
	Nmea0183 DataInfo `json:"nmea0183"`
	Nmea2000 DataInfo `json:"nmea2000"`
}

type FileEntry struct {
	Id  uint   `json:"id"`
	Len uint32 `json:"len"`
	MD5 string `json:"md5"`
	Url string `json:"url"`
}

type FileInfo struct {
	Count  uint        `json:"count"`
	Detail []FileEntry `json:"detail"`
}

type Status struct {
	Versions    VersionInfo   `json:"version"`
	Elapsed     uint32        `json:"elapsed"`
	Supply      float64       `json:"supply"`
	Server      WebServerInfo `json:"webserver"`
	CurrentData DataSummary   `json:"data"`
	Files       FileInfo      `json:"files"`
}

type TransferResult struct {
	Status string `json:"status"`
}
