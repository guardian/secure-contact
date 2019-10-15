# secure-contact

> The pen might not be mightier than the sword, but maybe the printing press was heavier than the siege weapon.  Just a few words can change everything ...

> ~ Terry Pratchett

Scripts for building and running the Guardian's PGP contact and SecureDrop pages

## Overview

### Secure Contact Monitor

Secure Contact Monitor (SCM) performs status monitoring of our onion website and updates our status page accordingly.

The monitor script attempts to reach our onion site five times, with a 60 second interval between each attempt. The timeouts and sleep are quite generous, which gives the Tor network the benefit of the doubt.

SCM will send notifications via Hangouts Chat and/or email. The channel it messages is determined by the webhook URL that is stored in AWS parameter store.

Most of the configuration, including the Onion URL, is stored in AWS Parameter Store and fetched each time the script is run.

### Notifications and alerts

TODO: document monitor history and how the application uses DynamoDB

## Contributing

### Python and virtualenv

This project is using Python 3.

#### 1. Install Python

MacOS users can use homebrew to install Python 3:

```bash
brew install python3
```

#### 2. Install and activate virtualenv

It is a good idea to use virtualenv with Python, this can be done with Pip:

```bash
pip3 install virtualenv
```

If you are setting up this project for the first time you will need to create a virtualenv.
From the root directory of the project run:

```bash
virtualenv venv
```

Once that is done, this command will activate virtualenv:

```bash
source venv/bin/activate
```

More details on virtual environments can be found here: https://docs.python-guide.org/dev/virtualenvs/

When you are finished with the virtualenv enter `deactivate` in the terminal to return to the default Python interpreter of the system. However, keep the virtualenv running while completing the remaining steps!

#### 3. Install packages

With your virtualenv active, you should be in the directory where requirements.txt is located.

For installing the required packages run:

```bash
pip3 install -r requirements.txt
```

### Running locally

#### DynamoDB

Secure Contact Monitor uses DynamoDB to persist some information. Therefore to run it locally you will need to make sure you have DynamoDB running. [You can download DynamoDB to run as a local jar from the AWS website](http://docs.aws.amazon.com/amazondynamodb/latest/developerguide/Tools.DynamoDBLocal.html).

To run DynamoDB for development, execute the following:

```bash
java -Djava.library.path=~/etc/DynamoDBLocal_lib -jar ~/etc/DynamoDBLocal.jar -sharedDb -inMemory

```

You'll also need to set up the required tables. The easiest way to do this is to run the script that exists for this purpose.

```bash
python3 dev/dev_database.py
```

Since this runs an in-memory version of DynamoDB, you'll need to set the tables up again each time you restart DynamoDB.

#### Tor

For the healthchecks to pass, the machine needs to be running Tor. Even though Tor Browser comes with a regular Tor, it will only run as long as you keep Tor Browser open.

MacOS users can use homebrew to install Tor as a command line tool:

```bash

brew install tor
```

The `.sample` extension will then need to be removed from the `torrc` configuration file. The file should be in your   /usr/local/etc/tor/ directory.

More instructions are available on [The Tor Project website](https://2019.www.torproject.org/docs/tor-doc-osx.html.en).

While developing locally, use a separate terminal window to run:

```bash
tor
```

## Validation

The following command will run the Python tests:

```bash
python -m unittest discover -s tests
```


## Deployment

### Monitor service

The Secure Contact Monitor service is an EC2 instance running in AWS. The CloudFormation template can be found in this repository and will also create a load balancer and autoscaling group (ASG).

To release the latest version of master to a stage, login to the AWS console and terminate the currently running instance. Once the ASG healthchecks fail, the ASG will launch a new instance using the launch config in the CloudFormation template.

The status page will remain available during the replacement since the page is served from an S3 bucket. While the new instance is launching it will perform the status check and update the status page in S3.


## TODO:

- Store healthcheck history and only send notifications on state change
- Decrease interval between healthchecks
- Serve a page displaying health information, including the healthcheck history
- Create a UI that only allows access to authorised users
- Add functionality to disable the S3 upload via UI
- Add toggle to override healthcheck results and force page update to desired state