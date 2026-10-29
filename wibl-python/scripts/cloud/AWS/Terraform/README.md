# Terraform AWS Build Instructions

## Setup
The following software items must be installed and configured before continuing

- Docker
- AWS CLI
- Terraform

### 1. Changing default configurations
Inside the [tf-configure-step-1.bash](./tf-configure-step-1.bash) file there are two variables that must be examined.
First is a variable called `PROVIDER_PREFIX`, which must be unique to each installation of the WIBL cloud processing
tools on AWS. Replace the value inside the quotation marks with a unique name to apply to all resources. Due to the 
nature of the cloud, all AWS components must have name unique to its region, type. So, the value given will be used 
to create unique names for all necessary resources.

Example: `PROVIDER_PREFIX='UNHJHC'`

Next, verify that the variable `WIBL_AWS_REGION` is set to the AWS region you wish to deploy to. This must be a 
[valid AWS region code](https://docs.aws.amazon.com/global-infrastructure/latest/regions/aws-regions.html).

Once you have made the desired changes to `tf-configure-step-1.bash`, run it. This script will generate two files:
`main.tf` and `terraform.tfvars`, both inside the [Terraform](../Terraform) folder. You shouldn't need to make any
changes in `main.tf`. `terraform.tfvars` contains three sections, variables that must be changed, variables that 
are optional to change, and variables that do not need to be changed. 

#### Variables That Need To Be Changed:
- `DCDB_provider_id`: Replace with your given DCDB provider id.
- `superuser_username`/`superuser_password`: Choose the main username and password used to access the frontend dashboard.
- `frontend_secret_key`: Following the directions is the `terraform.tfvars` file to generate a Django secret. The script 
to do so is located [here](./generate_secret.sh).
- `origin_secret`: This password phrase adds an extra level of security between the CloudFront module and the 
frontend's load balancer. Run the generate_secret script again to create a new value.
- `DCDB_mode`: By default the test mode is active. To switch to using the production URL, set this variable to 1.

#### Variables That Can Optionally Changed: 
- `frontend_db_size`/`manager_db_size`: This variable sets the size, in gigabytes, of the respective databases. The frontend database only contains bookkeeping information for user logins and common caching while the manager database contains 
all the file metadata that is currently in the system. If you come across storage space issues, 99% of the time it will be the 
manager database. 
- `frontend_db_user`/`manager_db_user`/`frontend_db_password`/`manager_db_password`: The database usernames and passwords are only used to internally access the database contents inside each separate AWS RDS instance. These values can be set for added security.

#### Other Mandatory Replacement Area:
- The `tf-configure-step-1.bash` script will also generate an empty text file name `default_auth.txt`. Inside of this file you must put your DCDB provider secret. If the secret is not copied into this file, the final steps of the data pipeline will fail.

### 2. Bootstrapping Terraform
Terraform is able to create, modify, and delete computing resources that were created using Terraform. To do this, 
Terraform must store state information about what resources have been created. This state information can be stored 
locally on a single computer. However, if the locally stored state information is lost, then you lose the ability to
automatically update or delete the AWS computing resources originally created by Terraform. To avoid this problem, 
Terraform state can be stored remotely in an S3 bucket. In addition to providing a disaster recovery solution, 
storing state in S3 allows multiple people/computers to manage a WIBL cloud processing system created with Terraform, 
and to do so asynchronously, without having to worry about one person's updates overwriting the other.

You can use the script [tf-configure-step-2.bash](tf-configure-step-2.bash) to create the S3 bucket to store Terraform state in. The 
name of the Terraform state bucket was automatically set in `main.tf` and `terraform.tfvars` by running 
`tf-configure-step-1.bash`. If for some reason you wish to change the Terraform state bucket name, key, or region,
make sure to make the same change in both `main.tf` and `terraform.tfvars`; the reason for the duplication is that
the Terraform S3 backend is initialized early when Terraform runs, before Terraform can read variables from 
`terraform.tfvars`. You must not change these values after you have run `tf-configure-step-2.bash`.

Before running `tf-configure-step-2.bash`, you must edit the `AWS_PROFILE` variable in [tf-aws-init.sh](tf-aws-init.sh)
to match the name of the [AWS CLI profile](https://docs.aws.amazon.com/cli/latest/userguide/cli-configure-files.html)
you wish to use.

Running `tf-configure-step-2.bash` will look something like this:

```
CONTENT_ROOT: /Users/USER_NAME/.../WIBL/wibl-python
Using AWS_TF_ROOT: /Users/USER_NAME/.../WIBL/wibl-python/scripts/cloud/AWS/Terraform
Using AWS_PROFILE: default
Using TF_VARS: /Users/USER_NAME/.../WIBL/wibl-python/scripts/cloud/AWS/Terraform/terraform.tfvars
Using AWS_REGION: us-east-2
Using TF_STATE_BUCKET: unhjhc-wibl-tf-state
Using TF_STATE_KEY: terraform/state/wibl-processing-server-deploy.tfstate
Using AWS_CLI: aws --profile default --region us-east-2
Using AWS_ACCOUNT_NUMBER: XXXXXXXXXXXX
Creating terraform state bucket unhjhc-wibl-tf-state in AWS region us-east-2...
{
    "Location": "https://unhjhc-wibl-tf-state.s3.amazonaws.com/"
}
Enabling bucket versioning in terraform state bucket unhjhc-wibl-tf-state...
Done.
```

### 3. Building The Lambda Package
This step only works if `docker` is currently running on your system. This step also require the "zip" command line tool.
Inside the outer [AWS](../../AWS) folder is a script called [build-lambda.sh](../build-lambda.sh), run this script. Even if the script 
is successful, there may still be a lingering `build` or `package` folder, pay these no mind and continue to the next step.

### 4. Building The System With Terraform
This step also requires `docker` to work, so ensure it is running. First, run the `plan.sh` script inside the Terraform 
folder. This is where any you will be alerted of any misconfigured or missing variables. If script says "Plan: 125 to 
add, 0 to change, 0 to destroy." without returning any errors, run the next script `build.sh`. If you do experience any 
errors when running the `build.sh` script, you need to then run the `destroy.sh` script before you can attempt another 
build. 

If you experience this error, **Error: Backend configuration changed**, then run the [tf-reconfigure.sh](./tf-reconfigure.sh) 
script and try to build again.

#### IMPORTANT: The system can take upwards of 15 to 25 minutes to fully build or destroy.

### How To Tear Down The System
#### WARNING: This script destroys ALL resources, meaning all data put into the system will be unrecoverable.
To destroy the resources in the cloud, including all AWS and docker resources, run the `destroy.sh` script. 
The following resources tend to take longer to destroy than their counter-parts. 
- module.configure-manager-ecs.aws_internet_gateway.ig_public
- module.configure-manager-ecs.aws_cloudfront_distribution.frontend

This is mostly due to a bug with AWS's resource state management system. AWS believes select lambda functions are still 
running, which can often leave multiple components hanging on each other waiting for the other to be destroyed. If it 
seems like this might be the case, using ^c to cancel the script and rerunning it may solve the issue.

