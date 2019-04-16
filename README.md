# secure-contact


## Development

This project is using Python 3.

### 1. Install Python

Mac users can use homebrew to install Python 3:

```bash
brew install python3
```

### 2. Install and activate virtualenv

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

### 3. Install packages

With your virtualenv active, you should be in the directory where requirements.txt is located.

For installing the required packages run:

```bash
pip3 install -r requirements.txt
```

### 4. Start the server

Use the following command to start a server:

```bash
python3 -m http.server
```

The default port is 8000.