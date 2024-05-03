package cloud

import (
	"errors"

	"ccom.unh.edu/wibl-monitor/src/support"
)

type LocalInterface struct {
	configured bool
}

func (dbg LocalInterface) Configured() bool {
	return dbg.configured
}

func (dbg *LocalInterface) Configure(config *support.Config) error {
	support.Debugf("DBGINT: configure call for AWS region %s, bucket %s, topic %s\n",
		config.AWS.Region, config.AWS.UploadBucket, config.AWS.SNSTopic)
	dbg.configured = true
	return nil
}

func (dbg LocalInterface) DestinationExists(name string) (bool, error) {
	if !dbg.Configured() {
		return false, errors.New("interface not configured")
	}
	support.Debugf("DBGINT: check for existence of %q for upload.\n", name)
	return true, nil
}

func (dbg LocalInterface) UploadFile(destination string, key string, data []byte) error {
	if !dbg.Configured() {
		return errors.New("interface not configured")
	}
	support.Debugf("DBGINT: request to upload to %q with key %q for data of length %d\n",
		destination, key, len(data))
	return nil
}

func (dbg LocalInterface) PublishNotification(topic string, key string) error {
	if !dbg.Configured() {
		return errors.New("interface not configured")
	}
	support.Debugf("DBGINT: notification on topic %q for key %q.\n", topic, key)
	return nil
}
