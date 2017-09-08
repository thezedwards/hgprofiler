#!/usr/bin/env python
"""
Command line client for the Profiler API.

Configuration is via config.ini which is created
automatically when it cannot be found in default locations:

http://click.pocoo.org/5/utils/#finding-application-folders

For example
===========

$ cat ~/.config/profilercli/config.ini:

[DEFAULT]
log_level=warning
profiler_app_host=None
profiler_api_token=None
log_file=None

ToDo
====

1. There is no handling for when token expires. An error will be thrown
with no information on how to fix.

"""
import click
import configparser
import csv
import datetime
import json
import jsonlines
import logging
import math
import os
import requests
import sys
import urllib
import time
from pygments import highlight, lexers, formatters
from validators.url import url as valid_url

# ToDo - remove and provide proper instructions:
requests.packages.urllib3.disable_warnings()

APP_NAME = 'profilercli'

# Terminal colours
RED = "\033[1;31m"
BLUE = "\033[1;34m"
CYAN = "\033[1;36m"
GREEN = "\033[0;32m"
RESET = "\033[0;0m"
BOLD = "\033[;1m"
REVERSE = "\033[;7m"

CONFIG_DIR = click.get_app_dir(APP_NAME)
CONFIG_PATH = os.path.join(CONFIG_DIR, 'config.ini')
CONFIG_DEFAULTS = {
    'log_level': 'warning',
    'profiler_app_host': None,
    'profiler_api_token': None,
    'log_file': None,
}


class NoTraceBackError(Exception):
    """
    Represents a human-facing exception with
    color highlighting and no traceback.
    """
    def __init__(self, msg):
        text = "{0.__name__}: {1}".format(type(self), msg)
        coloured_text = RED + text + RESET
        self.args = coloured_text,
        sys.exit(self)


class ProfilerError(Exception):
    """
    Represents a human-facing exception.
    """
    def __init__(self, message):
        self.message = message


class BadConfigError(NoTraceBackError):
    """
    Represents a human-facing configuration error.
    """
    pass


class UnauthorisedError(NoTraceBackError):
    """
    Represents a human-facing HTTP Error.
    """
    pass


class APIError(NoTraceBackError):
    """
    Represents a human-facing HTTP Error.
    """
    pass


def print_json(json_string):
    """
    Thanks arnushky:
    http://stackoverflow.com/questions/25638905/coloring-json-output-in-python
    """
    formatted_json = json.dumps(json.loads(json_string), indent=4)
    colourful_json = highlight(formatted_json,
                               lexers.JsonLexer(),
                               formatters.TerminalFormatter())
    print(colourful_json)


def _create_config_ini(config=CONFIG_DEFAULTS):
    """
    Create default config.ini in config_path.
    """
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_PATH, 'w+') as f:
        f.write('[DEFAULT]\n')
        for setting, value in config.items():
            f.write('{}={}\n'.format(setting, value if value else ''))

        logging.info('Created configuration file: {}'
                     .format(CONFIG_PATH))


def _get_config_ini():
    """
    Return dictionary of DEFAULT config.ini settings.

    File will be created if it does not exist.
    """
    if not os.path.exists(CONFIG_PATH):
        _create_config_ini()

    cfg = os.path.join(CONFIG_PATH)
    parser = configparser.ConfigParser()
    parser.read([cfg])
    rv = {}

    for k, v in parser['DEFAULT'].items():
        rv[k] = v

    return rv


def _get_token(api_host, username, password):
    """
    Obtain an API token.
    """
    # auth_url = config.settings['profiler_app_host'] + '/api/authentication/'
    auth_url = urllib.parse.urljoin(api_host, 'api/authentication/')
    payload = {'email': username, 'password': password}
    response = requests.post(auth_url, json=payload, verify=False)
    response.raise_for_status()

    try:
        token = response.json()['token']
    except KeyError:
        raise ProfilerError('Authentication failed.')

    return token


def _validate_response(response):
    """
    Return True if response valid else
    raise Exception.
    """
    # Provide some useful feedback if client
    # is unauthorised.
    # Otherwise just raise Exception
    if response.status_code == 401:
        raise UnauthorisedError('Configure or renew token!')
    else:
        raise APIError(response.text)

    return True


def _get_all_results(endpoint_url, key, headers, interval=5):
    """
    Fetch all results for endpoint_url.

    :param endpoint_url (str): api endpoint URL.
    :param key (str): json result key.
    :param key (dict): request headers.
    :param interval (int): request interval (seconds) (default:5).
    """
    page = 1
    pages = 1
    results = []

    while page <= pages:
        params = {'rpp': 100, 'page': page}
        response = requests.get(endpoint_url,
                                headers=headers,
                                params=params,
                                verify=False)

        _validate_response(response)

        data = response.json()
        try:
            total = int(data['total_count'])
        except KeyError:
            raise ProfilerError('Could not parse total_count')
        except:
            raise

        if total > 0:
            pages = math.ceil(total / 100)

        try:
            results += data[key]
        except KeyError:
            raise ProfilerError('Json result does not contain "{}"'.format(key))

        page += 1
        time.sleep(interval)

    return results


def _flatten_data(b, delim):
    val = {}
    for i in b.keys():
        if isinstance(b[i], dict):
            get = _flatten_data(b[i], delim)
            for j in get.keys():
                val[i + delim + j] = get[j]
        else:
            val[i] = b[i]

    return val


def _print_data_as_csv(data):
    flat_data = list(map(lambda x: _flatten_data(x, "__"), data))
    columns = list(set(x for y in flat_data for x in y.keys()))

    writer = csv.writer(sys.stdout)  # stdout file doesn't require open()/close()
    writer.writerow(columns)

    for row in flat_data:
        writer.writerow(list(map(lambda x: row.get(x, ""), columns)))


# Click command line client


class Config(object):
    """
    Base configuration class.
    """
    def __init__(self):
        self.config_dir = click.get_app_dir(APP_NAME)
        self.config_path = os.path.join(self.config_dir, 'config.ini')
        self.log_levels = {
            'debug': logging.DEBUG,
            'info': logging.INFO,
            'warning': logging.WARNING,
            'error': logging.ERROR,
            'critical': logging.CRITICAL
        }
        # Store config.ini values as settings
        # These can be overriden by user with
        # command line options
        self.settings = _get_config_ini()
        self.log_level = self.log_levels[self.settings.get('log_level',
                                                           'warning').lower()]
        self.headers = {}

    def is_valid(self):
        """
        Return True if configuration settings are valid.
        """
        if self._validate_app_host() \
           and self._validate_token():
            return True
        else:
            return False

        return True

    def _validate_app_host(self):
        """
        Return True if app host is valid URL.
        """
        app_host = self.settings['profiler_app_host']

        if not app_host:
            logging.critical('profiler_app_host is required')
            return False

        if not valid_url(self.settings['profiler_app_host']):
            logging.critical('{} is not a valid URL'
                             .format(app_host))
            return False

        return True

    def _validate_token(self):
        """
        Return True if token is set.
        """
        token = self.settings.get('profiler_api_token', None)

        if not token:
            logging.critical('profiler_api_token is required')
            return False

        return True


# Create decorator allowing configuration to be passed between commands.
pass_config = click.make_pass_decorator(Config, ensure=True)


@click.group()
@click.option('--app-host',
              prompt=False,
              envvar='PROFILER_APP_HOST',
              type=click.STRING,
              help="App host: 'protocol://address:port'")
@click.option('--token',
              envvar='PROFILER_API_TOKEN',
              type=click.STRING,
              help="App access token.")
@click.option('--log-file',
              type=click.Path(),
              default='',
              help='Log file.')
@click.option('--log-level',
              type=click.Choice(['debug',
                                 'info',
                                 'warning',
                                 'error',
                                 'critical']),
              default='warning',
              help='Log level.')
@pass_config
def cli(config, app_host, token, log_file, log_level):
    """ \b
    Profiler API Client
    ----------------------------

    Command line client for interacting with the Profiler API.

    The following environment variables can be used:

        PROFILER_APP_HOST = host (protocol://address:port).
        PROFILER_API_TOKEN = API token (use renew_token to obtain one).

    However you may prefer to save your settings in the config.ini file - you can check config using
    print_config.
    """
    # Update config with command line options
    if token:
        config.settings['profiler_api_token'] = token

    if app_host:
        config.settings['profiler_app_host'] = app_host

    # Validate or get input from user
    if not config.is_valid():
        click.echo('Please authenticate..')
        config.settings['profiler_app_host'] = click.prompt('API host')
        username = click.prompt('Username')
        password = click.prompt('Password', hide_input=True)
        config.settings['profiler_api_token'] = _get_token(
            api_host=config.settings['profiler_app_host'],
            username=username,
            password=password)
        click.secho(config.settings['profiler_api_token'],
                    fg='green')

        if click.confirm('Save settings?'):
            _create_config_ini(config.settings)

    config.headers['X-Auth'] = config.settings['profiler_api_token']
    config.api_host = urllib.parse.urljoin(config.settings['profiler_app_host'], 'api/')
    config.log_file = log_file
    config.log_level = config.log_levels[log_level]

    if config.log_file:
        logging.basicConfig(filename=config.settings['log_file'],
                            level=config.settings['log_level'],
                            format='%(asctime)s - %(levelname)s - %(message)s')
    else:
        logging.basicConfig(level=config.log_level,
                            format='%(asctime)s - %(levelname)s - %(message)s')


@cli.command()
@pass_config
def print_config(config):
    """
    Print configuration.
    """
    click.echo('Contents of {}:'.format(config.config_path))
    for k, v in config.settings.items():
        print('{}={}'.format(k.upper(), v))


@cli.command()
@click.argument('input-file',
                type=click.File(),
                required=True)
@click.option('--group-id',
              type=click.INT,
              required=False)
@click.option('--chunk-size',
              type=click.INT,
              required=False,
              default=100)
@click.option('--interval',
              type=click.INT,
              required=False,
              default=1)
@pass_config
def submit_usernames(config,
                     input_file,
                     group_id,
                     chunk_size,
                     interval):
    """
    Submit list of usernames to search for.

    :param input_file (file): csv file containing 1 username per line.
    :param group_id (int): id of site group to use.
    :param chunk_size (int): usernames to sumbit per API requests.
    :param interval (int): interval in seconds between API requests.
    """
    if not config.settings['profiler_api_token']:
        click.secho('You need an API token for this. Run "renew_token" '
                    'before proceeding', fg='red')
        sys.exit()

    reader = csv.reader(input_file)
    usernames = [item[0] for item in list(reader)]

    if not usernames:
        raise ProfilerError('No usernames found.')
    else:
        click.echo('[*] Extracted {} usernames.'.format(len(usernames)))

    username_url = urllib.parse.urljoin(config.api_host, 'username/')
    responses = []

    with click.progressbar(length=len(usernames),
                           label='Submitting usernames: ') as bar:
        for chunk_start in range(0, len(usernames), chunk_size):
            chunk_end = chunk_start + chunk_size
            chunk = usernames[chunk_start:chunk_end]
            bar.update(len(chunk))
            payload = {
                'usernames': chunk,
            }
            response = requests.post(username_url,
                                     headers=config.headers,
                                     json=payload,
                                     verify=False)
            _validate_response(response)
            responses.append(response.content.decode('utf-8'))
            time.sleep(interval)

    click.secho('Submitted {} usernames.'.format(len(usernames)), fg='green')

    for response in responses:
        print_json(response)


@cli.command()
@click.argument('input-file',
                type=click.File(),
                required=True)
@click.argument('output-file',
                type=click.File(mode='a+'),
                required=True)
@click.option('--interval',
              type=click.FLOAT,
              required=False,
              default=1)
@click.option('--ignore-missing',
              is_flag=True,
              help='Ignore missing results.')
@click.option('--output-format',
              '-f',
              type=click.Choice(['csv',
                                 'json']),
              default='csv')
@pass_config
def get_results(config,
                input_file,
                output_file,
                interval,
                ignore_missing,
                output_format):
    """
    Return results for list of usernames.


    :param input_file (file): text file containing 1 username per line.

    :param output_file (file): output file [csv|json].

    :param interval (int): interval in seconds between API requests.

    :param ignore_missing (bool): ignore failed requests.

    :param output_format (str): output format [csv|json].
    """
    if not config.settings['profiler_api_token']:
        click.secho('You need an API token for this. Run "renew_token" '
                    'before proceeding', fg='red')
        sys.exit()

    reader = csv.reader(input_file)
    usernames = [item[0] for item in list(reader)]

    if not usernames:
        raise ProfilerError('No usernames found.')
    else:
        click.echo('[*] Extracted {} usernames.'.format(len(usernames)))

    if output_format == 'csv':
        writer = csv.writer(output_file)
        writer.writerow(['Username',
                         'Site Name',
                         'Site URL',
                         'Status',
                         'Error'])
    elif output_format == 'json':
        writer = jsonlines.Writer(output_file)
    else:
        raise TypeError('{} is not supported'.format(output_format))

    with click.progressbar(usernames,
                           label='Getting username results: ') as bar:
        start = datetime.datetime.now()
        for username in bar:
            # Get results for username
            results_url = urllib.parse.urljoin(
                config.api_host, 'results/')
            username_url = urllib.parse.urljoin(
                results_url, 'username/{}'.format(username))
            response = requests.get(username_url,
                                    headers=config.headers,
                                    verify=False)
            time.sleep(interval)

            if ignore_missing:
                if response.status_code != 200:
                    continue
            else:
                _validate_response(response)

            # Parse results
            results = response.json().get('results', [])

            for result in results:
                if output_format == 'csv':
                    row = [username,
                           result['site_name'],
                           result['site_url'],
                           result['status'],
                           result['error']
                           ]
                    # Write to output file
                    writer.writerow(row)
                elif output_format == 'json':
                    writer.write(result)

            output_file.flush()
            time.sleep(interval)

    # Cleanup
    if input_file:
        input_file.close()

    if output_file:
        output_file.close()

    if output_format == 'json' and writer:
        writer.close()

    end = datetime.datetime.now()
    elapsed = end - start
    hours, remainder = divmod(elapsed.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)

    msg = '{} username results completed in {} hours, {} minutes, ' \
          'and {} seconds.' \
          .format(len(usernames), hours, minutes, seconds)

    click.secho(msg, fg='green')


@cli.command()
@click.argument('input-file',
                type=click.File(),
                required=True)
@click.argument('output-dir',
                type=click.Path(dir_okay=True,
                                exists=True,
                                writable=True,
                                resolve_path=True,
                                allow_dash=True),
                required=True)
@click.option('--interval',
              type=click.FLOAT,
              required=False,
              default=0.25)
@click.option('--ignore-missing',
              is_flag=True,
              help='Ignore missing results.')
@pass_config
def get_zip_results(config,
                    input_file,
                    output_dir,
                    interval,
                    ignore_missing):
    """
    Return zip results for list of usernames.


    :param input_file (file): csv file containing 1 username per line.
    :param output_dir (dir): output directory for zip archives.
    :param interval (int): interval in seconds between API requests.
    """
    if not config.settings['profiler_api_token']:
        click.secho('You need an API token for this. Run "renew_token" '
                    'before proceeding', fg='red')
        sys.exit()

    reader = csv.reader(input_file)
    usernames = [item[0] for item in list(reader)]

    if not usernames:
        raise ProfilerError('No usernames found.')
    else:
        click.echo('[*] Extracted {} usernames.'.format(len(usernames)))

    with click.progressbar(usernames,
                           label='Getting username results: ') as bar:
        start = datetime.datetime.now()
        for username in bar:
            # Get results for username
            archive_url = urllib.parse.urljoin(
                config.api_host, 'archives/')
            archive_url = archive_url + '?username={}'.format(username)
            response = requests.get(archive_url,
                                    headers=config.headers,
                                    verify=False)
            time.sleep(interval)
            # Allow user to ignore errors and missing results
            if ignore_missing:
                if response.status_code != 200:
                    continue
            # Log warnings if no result
            else:
                if response.status_code != 200:
                    msg = 'Failed to download archive for {}: {} - {}'.format(
                        username, response.status_code, response.text)
                    logging.warn(msg)

            archives = response.json().get('archives', [])

            # Only get first archive, getting all archives
            # for the same username is not normally useful.
            archives = archives[0:1]

            for archive in archives:
                filename = '{}-{}.zip' \
                           .format(username,
                                   archive['date'])
                zip_url = urllib.parse.urljoin(config.settings['profiler_app_host'],
                                               archive['zip_file_url'])
                response = requests.get(zip_url,
                                        headers=config.headers,
                                        verify=False)

                if response.status_code != 200:
                    msg = 'Failed to download zip for {} archive ID : {} - {}'.format(
                        username, archive['id'], response.status_code, response.text)
                    logging.warn(msg)

                outpath = os.path.join(output_dir, filename)

                with open(outpath, 'wb') as f:
                    f.write(response.content)

                time.sleep(interval)

    end = datetime.datetime.now()
    elapsed = end - start
    hours, remainder = divmod(elapsed.total_seconds(), 3600)
    minutes, seconds = divmod(remainder, 60)
    msg = '{} username results completed in {} hours, ' \
          '{} minutes, and {} seconds.' \
          .format(len(usernames), hours, minutes, seconds)
    click.secho(msg, fg='green')


@cli.command()
@pass_config
@click.argument('resource',
                type=click.STRING,
                required=True)
@click.option('--pretty',
              is_flag=True,
              help='Pretty print output.')
def get(config, resource, pretty):
    """
    Fetch JSON from resource.

    Example: /api/workers/
    """
    if not config.settings.get('profiler_api_token', None):
        raise ProfilerError('"--token" is required for this function.')

    url = urllib.parse.urljoin(config.api_host, resource)
    response = requests.get(url, headers=config.headers, verify=False)
    _validate_response(response)

    try:
        if pretty:
            print_json(response.content.decode('utf-8'))
        else:
            print(response.text)

    except Exception:
        raise


@cli.command()
@pass_config
@click.option('-f',
              '--output_format',
              type=click.Choice(['json',
                                 'csv']),
              default='json',
              help='Output format.')
def get_sites(config, output_format):
    """
    Return all sites data.
    """
    if not config.settings.get('profiler_api_token', None):
        raise ProfilerError('"--token" is required for this function.')

    resource = 'sites'
    url = urllib.parse.urljoin(config.api_host, resource)
    results = _get_all_results(url, 'sites', headers=config.headers)

    if output_format == 'json':
        print(results)
    elif output_format == 'csv':
        _print_data_as_csv(results)


@cli.command()
@pass_config
def renew_token(config):
    """
    Renew authentication token.
    """
    username = click.prompt('Username')
    password = click.prompt('Password', hide_input=True)
    config.settings['profiler_api_token'] = _get_token(
        api_host=config.settings['profiler_app_host'],
        username=username,
        password=password)
    click.secho(config.settings['profiler_api_token'],
                fg='green')

    if click.confirm('Update config.ini with new token?'):
        _create_config_ini(config.settings)


if __name__ == '__main__':
    cli()
