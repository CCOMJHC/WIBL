package main

import (
	"bytes"
	"crypto/md5"
	"crypto/rand"
	"crypto/tls"
	"crypto/x509"
	"encoding/base64"
	"encoding/json"
	"flag"
	"fmt"
	"io"
	"log"
	"net/http"
	"os"

	"ccom.unh.edu/wibl-monitor/src/api"
	"ccom.unh.edu/wibl-monitor/src/support"
)

func generate_data(pkt_size int) []byte {
	data := make([]byte, pkt_size)
	rand.Read(data)
	return data
}

func generate_url(server string, port int) string {
	return fmt.Sprintf("https://%s:%d/update", server, port)
}

func auth_token(ident string, password string) string {
	return "Basic " + base64.StdEncoding.EncodeToString([]byte(ident+":"+password))
}

func simulate_upload(url string, data []byte, ident string, password string) error {
	caCert, err := os.ReadFile("./certs/ca.crt")
	if err != nil {
		fmt.Printf("ERR: failed to read CA certificate for transport (%v).\n", err)
		return err
	}
	caCertPool := x509.NewCertPool()
	caCertPool.AppendCertsFromPEM(caCert)

	client := &http.Client{
		Transport: &http.Transport{
			TLSClientConfig: &tls.Config{
				RootCAs: caCertPool,
			},
		},
	}
	request, err := http.NewRequest("POST", url, bytes.NewBuffer(data))
	if err != nil {
		fmt.Printf("ERR: failed to geneate POST request structure (%v).\n", err)
		return err
	}

	md5hash := fmt.Sprintf("%X", md5.Sum(data))
	auth_header := auth_token(ident, password)

	request.Header.Add("Digest", "md5="+md5hash)
	request.Header.Add("Authorization", auth_header)
	request.Header.Set("Content-Type", "application/octet-stream")
	request.ContentLength = (int64)(len(data))

	response, err := client.Do(request)
	if err != nil {
		fmt.Printf("ERR: failed to execute the POST request (%v).\n", err)
		return err
	}
	defer response.Body.Close()

	body, err := io.ReadAll(response.Body)
	if err != nil {
		fmt.Printf("ERR: failed to read body from server (%v).\n", err)
		return err
	}
	fmt.Printf("DBG: reponse body = |%s|.\n", string(body))

	var result api.TransferResult
	decoder := json.NewDecoder(bytes.NewBuffer(body))
	if err := decoder.Decode(&result); err != nil {
		fmt.Printf("ERR: failed to decode JSON response from server (%v).\n", err)
		return err
	}
	if result.Status == "success" {
		fmt.Printf("INF: server acknowledged upload success.\n")
	} else if result.Status == "failure" {
		fmt.Printf("INF: server acknowledged upload failure.\n")
	} else {
		fmt.Printf("INF: server responded with %q?!\n", result.Status)
	}
	return nil
}

func main() {
	log.SetFlags(log.Lmicroseconds | log.Ldate)
	fs := flag.NewFlagSet("uploader", flag.ExitOnError)
	loggerID := fs.String("logger", "", "Logger unique identifier")
	loggerPass := fs.String("password", "", "Logger pre-shared password")
	pktSize := fs.Int("size", 100000, "Packet size to pass")
	server := fs.String("server", "", "Upload server name/address")
	port := fs.Int("port", 80, "Upload server port")

	var err error
	if err = fs.Parse(os.Args[1:]); err != nil {
		support.Errorf("failed to parse command line parameters (%v)\n", err)
		os.Exit(1)
	}
	if len(*loggerID) == 0 || len(*loggerPass) == 0 {
		support.Errorf("must specify logger name and password.")
		os.Exit(1)
	}

	server_url := generate_url(*server, *port)

	packet := generate_data(*pktSize)

	if err := simulate_upload(server_url, packet, *loggerID, *loggerPass); err != nil {
		fmt.Printf("ERR: failed to upload to server (%v).\n", err)
	}
}
