/*! @file logging.go
 * @brief Simple structured logging with string formatting.
 *
 * In order to provide systematic logging with formatting, this module provides support
 * code to generate syslog(1)-like logging levels.  This might not be the best way to do
 * this (according to the Go book), but it works well enough for simple cases.
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
	"fmt"
	"log"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"gopkg.in/natefinch/lumberjack.v2"
)

var loggingInitialized bool = false
var consoleLogFile *slog.Logger
var consoleLogStdout *slog.Logger
var accessLog *lumberjack.Logger

// ConfigureLogging configures logging. Assumption: This is called once during server initialization. There are no
// locks so calling this multiple times/concurrently will cause problems.
func ConfigureLogging(config *Config) {
	if loggingInitialized {
		panic("Expected logging to not be already configured, but it was.")
	}

	// Determine level for console log
	var level slog.Level
	switch config.Logging.Level {
	case "debug":
		level = slog.LevelDebug
	case "info":
		level = slog.LevelInfo
	case "warning":
		level = slog.LevelWarn
	case "error":
		level = slog.LevelError
	default:
		fmt.Printf("Console log level (%v) not recognised.\n", config.Logging.Level)
		os.Exit(1)
	}

	log.SetFlags(log.Lmicroseconds | log.Ldate)
	handlerOpts := slog.HandlerOptions{Level: level}

	// Configure two console logs, one for file one for stdout
	consoleLogFile = slog.New(
		slog.NewTextHandler(
			&lumberjack.Logger{
				Filename:   config.Logging.ConsoleLog,
				MaxSize:    config.Logging.MaxSizeMB,
				MaxAge:     config.Logging.MaxAge,
				MaxBackups: config.Logging.MaxBackups,
			},
			&handlerOpts))
	consoleLogStdout = slog.New(
		slog.NewTextHandler(os.Stdout, &handlerOpts),
	)

	// Configure access log file
	accessLog = &lumberjack.Logger{
		Filename:   config.Logging.AccessLog,
		MaxSize:    config.Logging.MaxSizeMB,
		MaxAge:     config.Logging.MaxAge,
		MaxBackups: config.Logging.MaxBackups,
	}

	loggingInitialized = true
}

func Infof(format string, args ...any) {
	mesg := fmt.Sprintf(format, args...)
	consoleLogStdout.Info(mesg)
	consoleLogFile.Info(mesg)
}

func Debugf(format string, args ...any) {
	mesg := fmt.Sprintf(format, args...)
	consoleLogStdout.Debug(mesg)
	consoleLogFile.Debug(mesg)
}

func Warnf(format string, args ...any) {
	mesg := fmt.Sprintf(format, args...)
	consoleLogStdout.Warn(mesg)
	consoleLogFile.Warn(mesg)
}

func Errorf(format string, args ...any) {
	mesg := fmt.Sprintf(format, args...)
	consoleLogStdout.Error(mesg)
	consoleLogFile.Error(mesg)
}

// LogAccess Logs a request in Combinded Log Format (CLF)
func LogAccess(r *http.Request, status int) {
	remoteAddr := r.RemoteAddr
	if idx := strings.LastIndex(remoteAddr, ":"); idx != -1 {
		remoteAddr = remoteAddr[:idx] // Remove port
	}

	username := "-"
	if user, _, ok := r.BasicAuth(); ok {
		username = user
	}

	timestamp := time.Now().Format("02/Jan/2006:15:04:05 -0700")
	request := fmt.Sprintf("%s %s %s", r.Method, r.RequestURI, r.Proto)

	referer := r.Referer()
	if referer == "" {
		referer = "-"
	}

	mesg := fmt.Sprintf("%s - %s [%s] \"%s\" %d %d %s %s\n",
		remoteAddr, username, timestamp, request, status, r.ContentLength, referer, r.UserAgent())
	_, err := accessLog.Write([]byte(mesg))
	if err != nil {
		panic("Unable to write to access log.")
	}
}
