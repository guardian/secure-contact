#!/bin/bash

rm lambda.zip

pip install --target ./package -r requirements.txt

cd package
zip -r9 ${OLDPWD}/lambda.zip .
cd $OLDPWD
zip -gr lambda.zip static
zip -gr lambda.zip templates
zip -g lambda.zip pgp_listing.py
zip -g lambda.zip pgp_manager.py