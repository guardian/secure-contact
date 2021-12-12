# secure-contact

> The pen might not be mightier than the sword, but maybe the printing press was heavier than the siege weapon.  Just a few words can change everything ...

> ~ Terry Pratchett

Automation and tooling for the [PGP contact](https://www.theguardian.com/pgp) and [SecureDrop status](https://www.theguardian.com/securedrop) pages of The Guardian.


## Secure Contact Monitor

Secure Contact Monitor (SCM) performs status monitoring of our onion site and updates our status page accordingly.

The monitor script attempts to reach our onion site five times, with a 60 second interval between each attempt. The timeouts and sleep are quite generous, which gives the Tor network the benefit of the doubt.

SCM will send notifications via Hangouts Chat and/or email. The channel it messages is determined by the webhook URL that is stored in AWS parameter store.

Most of the configuration, including the Onion URL, is stored in AWS Parameter Store and fetched every time the script runs.

### Local Development

Clone the repository and move into the directory:
```
git clone https://github.com/guardian/secure-contact.git
cd secure-contact/
```

#### 1. Install and Configure Tor

For the healthchecks to work, the machine needs to be running Tor. Even though Tor Browser comes with a regular Tor, it will only run while Tor Browser is open. Therefore, Tor should be installed as a command line tool.

MacOS users can use Homebrew to install Tor:

```bash
brew install tor
```

The `.sample` extension will then need to be removed from the `torrc` configuration file. If you installed Tor using Homebrew The file should be in your `/usr/local/etc/tor/` directory.

More instructions are available on [The Tor Project site](https://2019.www.torproject.org/docs/tor-doc-osx.html.en).

#### 2. Install Python and Pipenv

This project is using Python 3 and [Pipenv](https://pypi.org/project/pipenv/). Pipenv automatically creates and manages a virtualenv for  projects, as well as adds/removes packages from your Pipfile as you install/uninstall packages.

MacOS users can use Homebrew to install both:

```bash
brew install python3 pipenv
```

If you install Python via Homebrew you should now also have pip installed. If you are on Linux and installed with an OS package manager, you may have to install pip separately.

#### 3. Install dependencies with Pipenv

It is a good idea to use a virtual environment with Python; this project uses Pipenv.
From the `secure-contact/` directory, use pipenv to install the required packages and start the virtual environment:

```bash
pipenv install && pipenv shell
```

If you run into any issues setting up Python and pipenv, this guide may help: https://docs.python-guide.org/dev/virtualenvs/

Keep the virtual environment running while completing the remaining steps! If you need to terminate the virtual environment, enter `deactivate` in the terminal. This will return you to the default Python interpreter of the system.

#### Running Locally

start Tor running in a terminal:

```bash
tor
```

In another terminal window, navigate to the secure-contact directory and start the virtual environment if it is not already running:

```bash
pipenv shell
```

You should now be able to run the modules and tests. To run the healthcheck locally use:

```bash
python3 -m src.monitor
```

## Validation

The following command will run the Python tests:

```bash
python -m unittest discover -s tests
```

It is possible to specify a single test case to run, for example:

```bash
python -m unittest tests.test_database
```


## Deployment

### Monitor service

The Secure Contact Monitor service is an EC2 instance running in AWS. The CloudFormation template can be found in this repository and will also create a load balancer and autoscaling group (ASG).

When an instance launches it will perform the status check and update the status page in S3. Subsequent checks are performed via a cron job that is configured in the launch config UserData.

To manually run the monitor script, either use [SSM-Scala](https://github.com/guardian/ssm-scala) or start a session in AWS Systems Manager and run the following command:

```bash
cd /secure-contact && sudo -u www-data python3 -m src.monitor
```

To release the latest version of the service, consider using [Amiup](https://github.com/guardian/amiup) in yolo mode so that the AMI can be updated at the same time.

Alternatively, login to the AWS console and terminate the currently running instance. Once the ASG healthchecks fail, the ASG will launch a new instance using the launch config in the CloudFormation template. The status page will remain available during the replacement since the page is served from an S3 bucket.


## TODO:

- Store healthcheck history and only send notifications on state change
- Decrease interval between healthchecks
- Serve a page displaying health information, including the healthcheck history
- Create a UI that only allows access to authorised users
- Add functionality to disable the S3 upload via UI
- Add toggle to override healthcheck results and force page update to desired state