# Scripts 
This directory contains a number of utility scripts for Profiler.


## command_line.py
A command line client for interacting with the Profiler API.
Allows batch submission of lists of usernames and extraction of results
as csv or jsonlines.

### Installation

There are a few python requirements:

```
$ pip install click jsonlines requests pygments
```

You can supply the Profiler URL and authentication token as
as arguments to the functions:

```
$ python command_line.py --app-host=https://localhost --token=123 submit_usernames usernames.txt
```

To avoid being continually prompted for them, you can set the following
environment variables:

```
$ export PROFILER_APP_HOST=http://localhost
$ export PROFILER_API_TOKEN=123456789
```

Alternatively, save them in the configuration file:

```
$ cat ~/.config/profilercli/config.ini
[DEFAULT]
PROFILER_API_TOKEN=
LOG_FILE=None
PROFILER_APP_HOST=https://localhost
LOG_LEVEL=warning
```
[More about application config files](http://click.pocoo.org/5/utils/#finding-application-folders)

There is a helper function for obtaining the authentication token:

```
$ python command_line.py --app_host=https://localhost get_token
Username:
...
```

### Usage

```
$ python command_line.py
Usage: command_line.py [OPTIONS] COMMAND [ARGS]...

  Profiler API Client
  ----------------------------

  Command line client for interacting with the Profiler API.

  The following environment variables can be used:

      PROFILER_APP_HOST = host (protocol://address:port).
      PROFILER_API_TOKEN = API token (use get_token to obtain one).

  However the client largely uses config.ini which you can check config
  using print_config.

Options:
  --app-host TEXT                 App host: 'protocol://address:port'
  --token TEXT                    App access token.
  --log-file PATH                 Log file.
  --log-level [debug|info|warning|error|critical]
                                  Log level.
  --help                          Show this message and exit.

Commands:
  get               Fetch JSON from resource.
  get_results       Return results for list of usernames.
  get_token         Obtain an API token.
  get_zip_results   Return zip results for list of usernames.
  print_config      Print configuration.
  submit_usernames  Submit list of usernames to search for.

```
The client provides help for all all commands with the -h or --help options.
