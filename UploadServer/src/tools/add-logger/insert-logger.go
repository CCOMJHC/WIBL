package main

import (
	"encoding/json"
	"flag"
	"log"
	"os"

	"ccom.unh.edu/wibl-monitor/src/support"
	"github.com/google/uuid"
)

type Credentials struct {
	LoggerID string `json:"logger"`
	Password string `json:"password"`
	CACert   string `json:"ca_cert,omitempty"`
}

func main() {
	log.SetFlags(log.Lmicroseconds | log.Ldate)
	fs := flag.NewFlagSet("dbtool", flag.ExitOnError)
	loggerID := fs.String("logger", "", "Logger unique identifier")
	loggerPass := fs.String("password", "", "Logger pre-shared password")
	configFile := fs.String("config", "", "Filename to load JSON configuration")
	outCredsFile := fs.String("creds", "", "Filename in which to write logger credentials")

	var err error
	if err = fs.Parse(os.Args[1:]); err != nil {
		support.Errorf("failed to parse command line parameters (%v)\n", err)
		os.Exit(1)
	}
	if len(*loggerID) == 0 {
		support.Errorf("must specify logger name and password.")
		os.Exit(1)
	}
	if len(*loggerPass) == 0 {
		// This implies that the user doesn't have a password, and we should generate a UUID
		// for them.
		var password_uuid uuid.UUID
		var err error
		if password_uuid, err = uuid.NewUUID(); err != nil {
			support.Errorf("failed to generate a new UUID for logger's password (%s)\n", err)
			os.Exit(1)
		}
		*loggerPass = password_uuid.String()
	}

	var server_config *support.Config
	if len(*configFile) > 0 {
		var err error
		server_config, err = support.NewConfig(*configFile)
		if err != nil {
			support.Errorf("failed to generate configuration from %q (%v)\n", *configFile, err)
			os.Exit(1)
		}
	}
	support.ConfigureLogging(server_config)

	var db support.DBConnection
	if db, err = support.NewDatabase(server_config.DB.Connection); err != nil {
		support.Errorf("failed to open database connection for logger information (%v).\n", err)
		os.Exit(1)
	}
	if err = db.Setup(); err != nil {
		support.Errorf("database error.\n")
		os.Exit(1)
	}
	if err = db.InsertLogger(*loggerID, *loggerPass); err != nil {
		support.Errorf("database error.\n")
		os.Exit(1)
	}
	creds := Credentials{
		LoggerID: *loggerID,
		Password: *loggerPass,
	}
	data, err := json.MarshalIndent(creds, "", "  ")
	if len(*outCredsFile) > 0 {
		if err != nil {
			support.Errorf("failed to marshal logger credentials to JSON for output (%s)\n", err)
			os.Exit(1)
		}
		if err = os.WriteFile(*outCredsFile, data, 0644); err != nil {
			support.Errorf("failed to write logger credentials to %s (%s)\n", *outCredsFile, err)
			os.Exit(1)
		}
	}
	os.Stdout.WriteString("logger credentials:\n")
	os.Stdout.Write(data)
}
