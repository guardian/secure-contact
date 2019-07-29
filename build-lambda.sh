#!/bin/bash

set -ev

APP=secure-contact
PROJECT=InfoSec::infosec-$APP

if [[ -z $BUILD_NUMBER ]]; then
  BUILD_NUMBER=0
fi

if [[ -z $BUILD_VCS_NUMBER ]]; then
  BUILD_NUMBER=unknown
fi

if [[ -z $BRANCH_NAME ]]; then
  BRANCH_NAME=unknown
fi

BUILD_START_DATE=$(date +"%Y-%m-%dT%H:%M:%S.000Z")

# Check if the target directory exists and delete it if so
# -d is a operator to test if the given directory exists or not
[ -d target ] && rm -rf target
mkdir -p target/packages
mkdir -p target/$APP

# Download required python packages so we can bundle them
pip install --target target/packages -r requirements.txt

# archive entire directory and subdirectories using maximum compression

cd target/packages
zip -r9 $OLDPWD/target/$APP/$APP.zip .
cd $OLDPWD

zip -gr target/$APP/$APP.zip static
zip -gr target/$APP/$APP.zip templates
zip -g target/$APP/$APP.zip pgp_listing.py
zip -g target/$APP/$APP.zip pgp_manager.py

# Create build.json containing RiffRaff metadata
cat >build.json << EOF
{
   "projectName":"$PROJECT",
   "buildNumber":"$BUILD_NUMBER",
   "startTime":"$BUILD_START_DATE",
   "revision":"$BUILD_VCS_NUMBER",
   "vcsURL":"git@github.com:guardian/secure-contact.git",
   "branch":"$BRANCH_NAME"
}
EOF

# upload the package to S3
aws s3 cp --acl bucket-owner-full-control --region=eu-west-1 --recursive target/packages s3://riffraff-artifact/$PROJECT/$BUILD_NUMBER
aws s3 cp --acl bucket-owner-full-control --region=eu-west-1 build.json s3://riffraff-builds/$PROJECT/$BUILD_NUMBER/build.json