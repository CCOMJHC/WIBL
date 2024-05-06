package cloud

import (
	"ccom.unh.edu/wibl-monitor/src/support"
)

type ObjectDescription struct {
	Destination string `json:"bucket"`
	Filename    string `json:"filename"`
	FileSize    int    `json:"size"`
}

type CloudInterface interface {
	Configure(config *support.Config) error
	DestinationExists(meta ObjectDescription) (bool, error)
	UploadFile(meta ObjectDescription, data []byte) error
	PublishNotification(topic string, meta ObjectDescription) error
}
