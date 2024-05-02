package cloud

import (
	"bytes"
	"context"
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

func (c AWSInterface) DestinationExists(name string) (bool, error) {
	_, err := c.S3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: aws.String(name)})
	exists := true
	var apiError smithy.APIError
	if err != nil {
		if errors.As(err, &apiError) {
			switch apiError.(type) {
			case *types.NotFound:
				support.Infof("Bucket %v is available.\n", name)
				exists = false
				err = nil
			default:
				support.Errorf("Either you don't have access to bucket %v or another error occurred. "+
					"Here's what happened: %v\n", name, err)
			}
		}
	} else {
		support.Infof("Bucket %v exists and you already own it.", name)
	}

	return exists, err
}

func (c AWSInterface) UploadFile(destination string, key string, data []byte) error {
	_, err := c.S3Client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket: aws.String(destination),
		Key:    aws.String(key),
		Body:   bytes.NewReader(data),
	})
	if err != nil {
		support.Errorf("Couldn't upload data to %v:%v. Here's why: %v\n",
			destination, key, err)
	}
	return err
}

func (c AWSInterface) PublishNotification(topic string, key string) error {
	data := sns.PublishInput{TopicArn: aws.String(topic), Message: aws.String(key + ".wibl")}
	_, err := c.SnsClient.Publish(context.TODO(), &data)
	if err != nil {
		support.Errorf("SNS: Could not publish conversion notification to %v; library said: %v",
			topic, err)
	}
	return err
}
