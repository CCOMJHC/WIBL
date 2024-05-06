package cloud

import (
	"bytes"
	"context"
	"encoding/json"
	"errors"

	"ccom.unh.edu/wibl-monitor/src/support"
	"github.com/aws/aws-sdk-go-v2/aws"
	awsConfig "github.com/aws/aws-sdk-go-v2/config"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/aws/aws-sdk-go-v2/service/sns"
	"github.com/aws/smithy-go"
)

type AWSInterface struct {
	S3Client  *s3.Client
	SnsClient *sns.Client
}

func (c *AWSInterface) Configure(config *support.Config) error {
	// Loading the default configuration will also do a search for AWS_ACCESS_KEY_ID and
	// AWK_SECRET_ACCESS_KEY in the environment variables to set up credentials
	cfg, err := awsConfig.LoadDefaultConfig(context.TODO(), awsConfig.WithRegion(config.AWS.Region))
	if err != nil {
		support.Errorf("failed to load configuration, %v", err)
		return err
	}
	c.S3Client = s3.NewFromConfig(cfg)
	c.SnsClient = sns.NewFromConfig(cfg)
	return nil
}

func (c AWSInterface) DestinationExists(meta ObjectDescription) (bool, error) {
	support.Debugf("AWS-S3: checking for bucket %s.\n", meta.Destination)
	_, err := c.S3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: aws.String(meta.Destination)})
	exists := true
	var apiError smithy.APIError
	if err != nil {
		if errors.As(err, &apiError) {
			switch apiError.(type) {
			case *types.NotFound:
				support.Infof("Bucket %v is available.\n", meta.Destination)
				exists = false
				err = nil
			default:
				support.Errorf("Either you don't have access to bucket %v or another error occurred. "+
					"Here's what happened: %v\n", meta.Destination, err)
			}
		}
	} else {
		support.Infof("Bucket %v exists and you already own it.", meta.Destination)
	}

	return exists, err
}

func (c AWSInterface) UploadFile(meta ObjectDescription, data []byte) error {
	support.Debugf("AWS-S3: transferring %s to bucket %s (%d bytes).\n", meta.Filename, meta.Destination, meta.FileSize)
	_, err := c.S3Client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket: aws.String(meta.Destination),
		Key:    aws.String(meta.Filename),
		Body:   bytes.NewReader(data),
	})
	if err != nil {
		support.Errorf("Couldn't upload data to %v:%v. Here's why: %v\n",
			meta.Destination, meta.Filename, err)
	}
	return err
}

func (c AWSInterface) PublishNotification(topic string, meta ObjectDescription) error {
	support.Debugf("AWS-SNS: publishing key %s on topic %s.\n", meta.Filename, topic)
	msgstr, err := json.Marshal(meta)
	if err != nil {
		support.Errorf("SNS: failed to marshal message details for notification (%v).\n", err)
		return err
	}
	data := sns.PublishInput{TopicArn: aws.String(topic), Message: aws.String(string(msgstr))}
	_, err = c.SnsClient.Publish(context.TODO(), &data)
	if err != nil {
		support.Errorf("SNS: Could not publish conversion notification to %v; library said: %v",
			topic, err)
	}
	return err
}
