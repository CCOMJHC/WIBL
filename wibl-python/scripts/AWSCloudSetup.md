# IMPORTANT: 
This file describes the deprecated scripting build approach. The intended build method is to use Terraform. Follow the 
instructions in the README.md located in the Terraform folder, which is located at the relative path `./cloud/AWS/Terraform`.

# Packaging and deploying AWS lambdas for DCDB processing
There are a number of steps required to set up the AWS Lambdas, the S3 buckets, and associated triggers and permissions in order to make processing work in the cloud.  The steps are covered in detail below, and a corresponding set of scripts are available in the `wibl-python/AWS-setup` directory in the repository.  These scripts should *mostly* work, but will likely need some modficiation for a local configuration before being fully executable.  Consider the `configuration-parameters.sh` file first for this.

## Creating S3 Buckets
The cloud processing segment uses two AWS S3 buckets to receive the incoming data (`INCOMING_BUCKET`) and to stage processed data (`STAGING_BUCKET`) for further analysis, or before they're sent to DCDB for archive.  Creating these from the CLI is relatively straightforward:

```bash
aws s3api create-bucket \
    --bucket INCOMING_BUCKET \
    --region REGION \
    --create-bucket-configuration LocationConstraint=REGION
aws s3api create-bucket \
    --bucket STAGING_BUCKET \
    --region REGION \
    --create-bucket-configuration LocationConstraint=REGION
```

where `INCOMING_BUCKET` and `STAGING_BUCKET` are the short names for the buckets (i.e., not the full ARN), and `REGION` is the AWS region.  Since S3 buckets are global objects, you do not need to specifically set the `REGION`, but doing so can be advantageous since the data will stay within the same facility as the Lambdas, which can improve performance.  If you do not specify the region, us-east-1 (Virginia) is used.  Specifying the `create-bucket-configuration` is only required if you do specify the `REGION`.

## Create IAM roles for WIBL lambdas
First, create an IAM role for each lambda (e.g., processing and submission). We'll do this using the AWS CLI rather
than the AWS web console since this enables us to automate lambda configuration. Also, the CLI tends to change less
often than the web console user interface, so these instructions should last much longer without updating.

First create the following trust policy JSON file:
```bash
$ cat > trust-policy.json <<-HERE
{
 "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": ["lambda.amazonaws.com"]
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
HERE
```
Then create the IAM role for the processing lambda:
```bash
$ aws iam create-role \
  --role-name wibl-processing-lambda \
  --assume-role-policy-document file://trust-policy.json
```

Next, create the IAM role for the submission lambda:
```bash
$ aws iam create-role \
  --role-name wibl-submission-lambda \
  --assume-role-policy-document file://trust-policy.json
```

> Make a copy of the role ARNs returned to you after running these commands. We'll need them to create the lambdas below.

Attach the following policy to allow Lambda to write logs in CloudWatch, processing lambda:
```bash
$ aws iam attach-role-policy \
  --role-name wibl-processing-lambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

also for submission lambda:
```bash
$ aws iam attach-role-policy \
  --role-name wibl-submission-lambda \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

> Note: it takes a little while for the roles to propagate out to the rest of the AWS infrastructure, so if you
> attempt to use the roles to create Lambdas before they've finished, you'll get odd errors.  Something on the
> order to 5-10 s appears to work, but this could vary depending on the region that you're in.

## Package lambdas as zipfile
> Note: the following is based on [AWS lambda deployment instructions](https://docs.aws.amazon.com/lambda/latest/dg/python-package.html#python-package-create-package-with-dependency)

Since all WIBL AWS lambdas are part of the same Python package called `wibl`, we'll only need to create a single
package. We can specify different lambda handler functions when creating the individual lambdas below.

First (and optionally), run a shell within the Amazon Linux Python 3.8 lambda runtime:
```
$ docker run \
  --mount type=bind,source="$(pwd)/.",target=/build \
  -it --entrypoint /bin/bash \
  public.ecr.aws/lambda/python:3.8-x86_64
```

The reason you might want to package lambdas within Amazon Linux Python 3.8 lambda runtime is that it should be nearly
identical to the environment where the lambda will run. This way, you can reduce the risk of introducing any platform-
or architecture-specific dependencies. That said, since we are using AWS layers to configure some of the dependencies
for our lambdas (e.g., including platform- and architecture-specific dependencies such as numpy), and since the
dependencies we *are* bundlying in our lambda zipfile (as specified by
[requirements-lambda.txt](requirements-lambda.txt)) *should* be pure Python, it *should* be okay to create this
package on either non-Amazon versions of Linux, or under recent versions of macOS. However, it is probably a good idea
to use Amazon Linux Python 3.8 lambda runtime to package these lambdas.

> It should be possible to use the ARM64 architecture to package and deploy the Lambdas, but there are limitations
> to the support facilities in the currently available Lambda runtimes, particularly with respect to Python versions
> and SciPy installed versions.  This can cause the Lambda to abort before booting when triggered.

> Similarly, it should be possible to use more recent Python runtimes, but they often don't have good support for the
> SciPy layer that's required for the WIBL code.  This may change over time; the WIBL code is typically tested with
> the most recent version of Python.

Second, install WIBL and its dependencies into a target directory called `package` located in the current directory:
```
$ cd /build
$ pip install --target ./package -r requirements-lambda.txt
$ pip install --target ./package ./wibl-manager
$ pip install --target ./package --no-deps .
```

> Note: if building in Amazon Linux Python 3.8 lambda runtime, make sure to run these in the shell you started in
> Docker above rather than in a shell on your host OS.  You can do this by hand, or by sending the commands into a file, and then piping it into the docker command (remove the ``-t`` option if you do this).

> Note: we break out the install into two steps so that we package *only* the subset of `wibl` dependencies that will
> not be provided by AWS lambda layers used when we create the lambda below.

Next, make a zipfile of the `package` directory:
```
$ pushd .
$ cd package
$ zip -r ../wibl-package.zip .
$ popd
```

> Note: if building in Amazon Linux Python 3.8 lambda runtime, you'll have to run this from your host since `zip` is not
> installed by default.

## Create the processing lambda
```
$ aws lambda create-function \
  --function-name wibl-processing \
  --role arn:aws:iam::ACCOUNT_NUMBER:role/wibl-processing-lambda \
  --runtime python3.8 --timeout 30 --memory-size 2048 \
  --handler wibl.processing.cloud.aws.lambda_function.lambda_handler \
  --zip-file fileb://wibl-package.zip \
  --architectures x86_64 \
  --layers LAYER1 ... LAYERN \
  --environment "Variables={PROVIDER_ID=MY_PROVIDER_ID,STAGING_BUCKET=MY_STAGING_BUCKET,UPLOAD_POINT=https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/}"
```

where `ACCOUNT_NUMBER` is your AWS account number, and where `LAYER1 ... LAYERN` are replaced by the names of the AWS lambda layers we would like to deploy this lambda on top of (to avoid repackaging dependencies).  See the example configuration file for definitions of the environment variables.

> Note: by default, the lambda will use the configuration file installed as part of the `wibl` Python package. You can
> find this default file in [here](wibl/defaults/processing/cloud/aws/configure.json). If you want to use another file,
> make sure to add it to the `package` directory created above and set an environment variable named `WIBL_CONFIG_FILE`
> (value is the path within the package to the desired configuration file) when creating the lambda function.

> Note: if you want to use ARM64 instead of x86_64 architecture, change `--architectures x86_64` to
> `--architectures arm64`.

> The `timeout` and `memory-size` settings may have to be adjusted for your implementation; these defaults work
> reasonably for the default code-base.

> Note: the layer name is the full ARN for the layer required.  You will need at least the SciPy layer for a
> default build of the code; this is likely
> arn:aws:lambda:us-east-2:259788987135:layer:AWSLambda-Python38-SciPy1x:107 (or the equivalent for your AWS region).

## Configure the Processing Lambda to Trigger from S3
To have the processing lambda triggered by the upload of a file into an S3 bucket, you need to configure the lambda to be triggerable, configure the bucket to generate notifications (and send them to the lambda), and then configure the lambda to allow for access to the S3 bucket.  In order:

```
$ aws lambda add-permission \
  --function-name wibl-processing \
  --action lambda:InvokeFunction \
  --statement-id s3invoke \
  --principal s3.amazonaws.com \
  --source-arn arn:aws:s3:::INCOMING_BUCKET \
  --source-account ACCOUNT_NUMBER
```
where `INCOMING_BUCKET` is the name of the S3 bucket that you'll upload data into from the outside world, and `ACCOUNT_NUMBER` is the AWS account number for your installation.

> Note: Some services can invoke functions in other accounts. If you specify a source
> ARN that has your account ID in it, that isn't an issue. For Amazon S3, however, the
> source is a bucket whose ARN doesn't have an account ID in it. It's possible that you
> could delete the bucket and another account could create a bucket with the same name.
> Using the source-account option with your account ID ensures that only resources in
> your account can invoke the function.

> Note: Once the permissions are added to the Lambda, there's a propagation time for the Lambda to complete
> setup, and then propagate this out to the rest of the AWS infrastructure.  If you attempt to target the
> Lambda (e.g., to do the next stage of adding the trigger) without waiting for this to happen, odd errors
> occur.  A delay of 5-10 s seems to be appropriate, but may depend on the region that you're in.

Generate a configuration file for the bucket to notify the lambda:
```bash
$ cat > bucket-notification-cfg.json <<-HERE
{
    "LambdaFunctionConfigurations": [
        {
            "Id": "IDENTIFIER",
            "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT_NUMBER:function:wibl-processing",
            "Events": [
                "s3:ObjectCreated:Put",
                "s3:ObjectCreated:CompleteMultipartUpload"
            ]
        }
    ]
}
HERE
```
where `IDENTIFIER` is a unique identifier (e.g., a UUID), `REGION` is your AWS region, and `ACCOUNT_NUMBER` is as above.  You can obtain the ARN for your bucket directly from the AWS console if necessary.  Then apply the notification to the bucket:

```bash
$ aws s3api put-bucket-notification-configuration \
  --bucket INCOMING_BUCKET \
  --notification-configuration file://bucket-notification-cfg.json
```
where `INCOMING_BUCKET` is the short form name of the bucket you're using for incoming files, as above.

Finally, generate a configuration file to allow the lambda access to the S3 bucket:
```bash
$ cat > lambda-s3-access.json <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::INCOMING_BUCKET",
                "arn:aws:s3:::INCOMING_BUCKET/*",
                "arn:aws:s3:::STAGING_BUCKET",
                "arn:aws:s3:::STAGING_BUCKET/*"
            ]
        }
    ]
}
HERE
```
and apply it to the lambda:
```bash
$ aws iam put-role-policy \
  --role-name wibl-processing-lambda \
  --policy-name lambda-s3-access \
  --policy-document file://lambda-s3-access.json
```
and then convince yourself that it has been applied:
```bash
$ aws iam list-role-policies --role-name wibl-processing-lambda
```
which should report something like:
```
{
    "PolicyNames": [
        "lambda-s3-access"
    ]
}
```

At this stage, submitting a WIBL file to the `INCOMING_BUCKET` should result in the file being processed and written into the `STAGING_BUCKET` that was specified in the environment variables of the WIBL package.

## Create the submission lambda
```bash
$ aws lambda create-function \
  --function-name wibl-submission \
  --role arn:aws:iam::ACCOUNT_NUMBER:role/wibl-submission-lambda \
  --runtime python3.8 --timeout 30 --memory-size 2048 \
  --handler wibl.submission.cloud.aws.lambda_function.lambda_handler \
  --zip-file fileb://wibl-package.zip \
  --architectures x86_64 \
  --environment "Variables={PROVIDER_ID=MY_PROVIDER_ID,PROVIDER_AUTH=MY_PROVIDER_AUTH_KEY,STAGING_BUCKET=MY_STAGING_BUCKET,UPLOAD_POINT=https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/}"
```

> Note: the submission lambda takes an additional environment variable `PROVIDER_AUTH`, which is an authentication key
> used for making submissions to the HTTP service denoted by `UPLOAD_POINT`.

> Note: by default, the lambda will use the configuration file installed as part of the `wibl` Python package. You can
> find this default file in [here](wibl/defaults/submission/cloud/aws/configure.json). If you want to use another file,
> make sure to add it to the `package` directory created above and set an environment variable named `WIBL_CONFIG_FILE`
> (value is the path within the package to the desired configuration file) when creating the lambda function.

## Configure the Submission Lambda to Automatically Trigger
The process for this is essentially the same as for the processing Lambda, with some obvious modifications to match the particular buckets in use.

First, create a bucket notification so that files being added to the STAGING_BUCKET by the processing Lambda trigger the submission Lambda:
```bash
cat >bucket-notification-cfg.json <<-HERE
{
    "LambdaFunctionConfigurations": [
        {
            "Id": "${UUID}",
            "LambdaFunctionArn": "arn:aws:lambda:REGION:ACCOUNT_NUMBER:function:wibl-submission",
            "Events": [
                "s3:ObjectCreated:Put",
                "s3:ObjectCreated:CompleteMultipartUpload"
            ]
        }
    ]
}
HERE
```

and then apply it to the STAGING_BUCKET as before:
```bash
aws s3api put-bucket-notification-configuration \
	--bucket STAGING_BUCKET \
	--notification-configuration file://bucket-notification-cfg.json
```

Next, generate an access policy to allow the submission Lambda to access the STAGING_BUCKET:
```bash
cat >lambda-s3-access.json <<-HERE
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "LambdaAllowS3Access",
            "Effect": "Allow",
            "Action": [
                "s3:*"
            ],
            "Resource": [
                "arn:aws:s3:::STAGING_BUCKET",
                "arn:aws:s3:::STAGING_BUCKET/*"
            ]
        }
    ]
}
HERE
```

and then add the permissions on the submission Lambda to allow it to be invoked by S3,
```bash
aws lambda add-permission \
  --function-name wibl-submission \
	--action lambda:InvokeFunction \
	--statement-id s3invoke \
	--principal s3.amazonaws.com \
	--source-arn arn:aws:s3:::STAGING_BUCKET \
	--source-account ACCOUNT_NUMBER
```

and then add the policy for permissions,
```bash
aws iam put-role-policy \
	--role-name wibl-submission-lambda \
	--policy-name lambda-s3-access \
	--policy-document file://lambda-s3-access.json
```

> Note: The same delays between Lambda creation and adding the trigger as for the processing Lambda are required.

# Upload a New Version of a Lambda
```bash
$ aws lambda update-function-code --function-name wibl-processing \
  --zip-file fileb://wibl-package.zip
```

# Change Lambda Environment
```bash
$ aws lambda update-function-configuration \
  --function-name wibl-submission \
  --environment "Variables={PROVIDER_ID=MY_PROVIDER_ID_UPDATED,PROVIDER_AUTH=MY_PROVIDER_AUTH_KEY_UPDATED,STAGING_BUCKET=MY_STAGING_BUCKET_UPDATED,UPLOAD_POINT=https://www.ngdc.noaa.gov/ingest-external/upload/csb/geojson/}"
```
