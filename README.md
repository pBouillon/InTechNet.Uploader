# InTechNet.Uploader

InTechNet module and resources uploader

## Installation

First, clone the repository

```bash
~$ git clone https://github.com/pBouillon/InTechNet.Uploader
```

Then install the required dependencies

```bash
~$ cd InTechNet.Uploader
~$ pip install -r requirements.txt
```

> Please update the `database.ini` file with your database credentials.

## Usage

Provide the path of the module you would like to update, you may add the tag
`--verbose` to see the uploads progression.

```bash
~$ python uploader.py my/awesome/module/
```

Use the option `--help` for help

```bash
~$ python ./uploader.py --help
Usage: uploader.py [OPTIONS] PATH

  Upload a module and its resources in the correct order

Options:
  -m, --module PATH               Path to the module description file
  -s, --subscriptionplan INTEGER  Id of the subscription plan to which this
                                  module is intended

  --verbose                       Set verbosity to True to display actions in
                                  the console on execution

  --help                          Show this message and exit.
```
