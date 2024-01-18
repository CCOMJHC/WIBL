/*! @file middleware.go
 * @brief Support code for HTTP BasicAuth implementation
 *
 * This code provides support for BasicAuth in HTTP requests, where the user provides a username:password
 * pair in the "Authorization" header (base-64 encoded).  For simplicity here, we specify the expected
 * username and password directly, although in production you'd obviously want to have these in a database
 * somewhere, encrypted at rest (the conventional method for this would be to have them in environment
 * variables, but since you need one for each logger you have deployed, that's not going to work here).  Since
 * the details of how you'd manage this are implementation dependent and this code is only provided to
 * demonstrate the server side of the upload protocol, this issue is not addressed.
 *
 * The code here is heavily based on the article at https://www.alexedwards.net/blog/basic-authentication-in-go
 * That code has an MIT license, which is the same as that used for the rest of the project, so it's
 * repeated below.
 *
 * Copyright (c) 2024, University of New Hampshire, Center for Coastal and Ocean Mapping, and
 * Alex Edwards (original implementation, adapted here).
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
	"crypto/sha256"
	"crypto/subtle"
	"net/http"
)

func BasicAuth(next http.HandlerFunc) http.HandlerFunc {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		username, password, ok := r.BasicAuth()
		if ok {
			usernameHash := sha256.Sum256([]byte(username))
			passwordHash := sha256.Sum256([]byte(password))
			// You should typically Look up the username and password in a well-known list of loggers
			// that you're supporting.  For testing, however, you can set the values directly here.
			var known_username string = "wibl-logger"
			var known_password string = "1f808ca8-9ae3-4db1-9838-002cd7be04a8"

			// Note the use of SHA256 to generate a fixed-length string here for the authentication information.
			// You can apparently carefully craft messages to expose how long it takes to do comparisons
			// of strings on the server, and therefore work out how many characters of the username or
			// password you have correct ...  This process avoids this attack by making fixed-length strings,
			// and then using the constant-time compare (i.e., without short-circuit comparison).  SHA256 is
			// of course not recommended for encryption of data at rest (e.g., in your password file or
			// database).

			expectedUsernameHash := sha256.Sum256([]byte(known_username))
			expectedPasswordHash := sha256.Sum256([]byte(known_password))

			usernameMatch := (subtle.ConstantTimeCompare(usernameHash[:], expectedUsernameHash[:]) == 1)
			passwordMatch := (subtle.ConstantTimeCompare(passwordHash[:], expectedPasswordHash[:]) == 1)

			if usernameMatch && passwordMatch {
				next.ServeHTTP(w, r)
				return
			}
		}

		w.Header().Set("WWW-Authenticate", `Basic realm="restricted", charset="UTF-8"`)
		http.Error(w, "Unauthorized", http.StatusUnauthorized)
	})
}
