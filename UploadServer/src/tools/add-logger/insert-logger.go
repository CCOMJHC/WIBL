package main

import (
	"flag"
	"log"
	"os"

	"ccom.unh.edu/wibl-monitor/src/support"
)

func main() {
	log.SetFlags(log.Lmicroseconds | log.Ldate)
	fs := flag.NewFlagSet("dbtool", flag.ExitOnError)
	loggerID := fs.String("logger", "", "Logger unique identifier")
	loggerPass := fs.String("password", "", "Logger pre-shared password")
	configFile := fs.String("config", "", "Filename to load JSON configuration")

	var err error
	if err = fs.Parse(os.Args[1:]); err != nil {
		support.Errorf("failed to parse command line parameters (%v)\n", err)
		os.Exit(1)
	}
	if len(*loggerID) == 0 || len(*loggerPass) == 0 {
		support.Errorf("must specify logger name and password.")
		os.Exit(1)
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
}
