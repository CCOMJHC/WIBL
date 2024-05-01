package support

import (
	"bytes"
	"context"
	"errors"

	"github.com/aws/aws-sdk-go-v2/aws"
	"github.com/aws/aws-sdk-go-v2/service/s3"
	"github.com/aws/aws-sdk-go-v2/service/s3/types"
	"github.com/aws/aws-sdk-go-v2/service/sns"
	"github.com/aws/smithy-go"
)

type AWSInterface struct {
	S3Client  *s3.Client
	SnsClient *sns.Client
}

func (c AWSInterface) BucketExists(name string) (bool, error) {
	_, err := c.S3Client.HeadBucket(context.TODO(), &s3.HeadBucketInput{Bucket: aws.String(name)})
	exists := true
	var apiError smithy.APIError
	if err != nil {
		if errors.As(err, &apiError) {
			switch apiError.(type) {
			case *types.NotFound:
				Infof("Bucket %v is available.\n", name)
				exists = false
				err = nil
			default:
				Errorf("Either you don't have access to bucket %v or another error occurred. "+
					"Here's what happened: %v\n", name, err)
			}
		}
	} else {
		Infof("Bucket %v exists and you already own it.", name)
	}

	return exists, err
}

func (c AWSInterface) UploadFile(bucketName string, objectKey string, data []byte) error {
	_, err := c.S3Client.PutObject(context.TODO(), &s3.PutObjectInput{
		Bucket: aws.String(bucketName),
		Key:    aws.String(objectKey),
		Body:   bytes.NewReader(data),
	})
	if err != nil {
		Errorf("Couldn't upload data to %v:%v. Here's why: %v\n",
			bucketName, objectKey, err)
	}
	return err
}

func (c AWSInterface) PublishSNS(topicArn string, objectKey string) error {
	data := sns.PublishInput{TopicArn: aws.String(topicArn), Message: aws.String(objectKey + ".wibl")}
	_, err := c.SnsClient.Publish(context.TODO(), &data)
	if err != nil {
		Errorf("SNS: Could not publish conversion notification to %v; library said: %v",
			topicArn, err)
	}
	return err
}
