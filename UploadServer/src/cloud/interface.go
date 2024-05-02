package cloud

import (
	"ccom.unh.edu/wibl-monitor/src/support"
)

type CloudInterface interface {
	Configure(config *support.Config) error
	DestinationExists(name string) (bool, error)
	UploadFile(destination string, key string, data []byte) error
	PublishNotification(topic string, key string) error
}
