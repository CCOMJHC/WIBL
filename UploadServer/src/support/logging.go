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
	"log/slog"
	"net/http"
	"strings"
	"time"
)

func Infof(format string, args ...any) {
	slog.Default().Info(fmt.Sprintf(format, args...))
}

func Debugf(format string, args ...any) {
	slog.Default().Debug(fmt.Sprintf(format, args...))
}

func Warnf(format string, args ...any) {
	slog.Default().Warn(fmt.Sprintf(format, args...))
}

func Errorf(format string, args ...any) {
	slog.Default().Error(fmt.Sprintf(format, args...))
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

	Infof("%s - %s [%s] \"%s\" %d %d %s %s",
		remoteAddr, username, timestamp, request, status, r.ContentLength, referer, r.UserAgent())
}
