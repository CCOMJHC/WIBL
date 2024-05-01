/*! @file config.go
 * @brief Configuration services for the demonstration upload server
 *
 * Centralised configuration management for the demonstration upload server.  This reads
 * a JSON file for the configuration, and defaults to a standard configuration if no file
 * is available, or specified on server start.
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

package support

import (
	"encoding/json"
	"io"
	"os"
)

// An APIParam provides parameters required to set up the server (e.g., the port to
// listen on).
type APIParam struct {
	Port int `json:"port"`
}

// An AWSParam provides all parameters required to talk with AWS.  Note that the credentials
// for interaction are typically done through environment variables, rather than from the JSON
// file
type AWSParam struct {
	Region       string `json:"region"`
	UploadBucket string `json:"upload_bucket"`
	SNSTopic     string `json:"sns_topic"`
}

// The Config object encapsulates all of the parameters required for the server, and
// subsequent upload of the data to the processing instances.
type Config struct {
	API APIParam `json:"api"`
	AWS AWSParam `json:"aws"`
}

// Generate a new Config object from a given JSON file.  Errors are returned
// if the file can't be opened, or if the JSON cannot be decoded to the Config type.
func NewConfig(filename string) (*Config, error) {
	config := new(Config)
	f, err := os.Open(filename)
	if err != nil {
		Errorf("failed to open %q for JSON configuration\n", filename)
		return nil, err
	}
	decoder := json.NewDecoder(f)
	if err := decoder.Decode(config); err != nil && err != io.EOF {
		Errorf("failed to decode JSON parameters from %q (%v)\n", filename, err)
		return nil, err
	}
	return config, nil
}

// Generate a basic-functionality Config structure if there is no further information
// from the user (e.g., not JSON configuration file).  In this case it's unlikely that
// the upload to the S3 bucket is going to work, but at least the error messages will be
// illuminating.
func NewDefaultConfig() *Config {
	config := new(Config)
	config.API.Port = 8000
	config.AWS.Region = "us-east-2"
	config.AWS.UploadBucket = "UNHJHC-wibl-incoming"
	config.AWS.SNSTopic = "UNHJHC-wibl-conversion"
	return config
}
