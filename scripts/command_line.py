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
with no information on how to fix :-(

"""
import click
import configparser
import csv
import datetime
import getpass
import json
import logging
import math
import os
import requests
import sys
import time
import urllib
from pygments import highlight, lexers, formatters

# ToDo - remove and provide proper instructions:
requests.packages.urllib3.disable_warnings()

APP_NAME = 'profilercli'


def download_zip(url, output_dir):
    """
    Download zip file from url.
    """
    raise NotImplemented


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


class ProfilerError(Exception):
    """
    Represents a human-facing exception.
    """
    def __init__(self, message):
        self.message = message


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
        self._load_settings()
        self.log_level = self.log_levels[self.settings.get('log_level',
                                                           'warning').lower()]
        self.headers = {}

    def _load_settings(self):
        """
        Load settings from config.ini.
        The file will be created if it does not exist.
        """
        if os.path.exists(self.config_path):
            self.settings = self._read_config()
        else:
            click.secho('You are not authenticated.', fg='red')
            self.settings = {
                'log_level': 'warning',
                'profiler_app_host': None,
                'profiler_api_token': None,
                'log_file': None,
            }
            os.makedirs(self.config_dir, exist_ok=True)
            self.settings['profiler_app_host'] = input('App host:')
            username = input('Username:')
            password = getpass.getpass('Password:')
            auth_url = os.path.join(self.settings['profiler_app_host'],
                                    '/api/authentication/')
            payload = {'email': username, 'password': password}
            response = requests.post(auth_url, json=payload, verify=False)
            response.raise_for_status()

            try:
                self.settings['profiler_api_token'] = response.json()['token']
            except KeyError:
                raise ProfilerError('Authentication failed.')

            with open(self.config_path, 'w+') as f:
                f.write('[DEFAULT]\n')
                for setting, value in self.settings.items():
                    f.write('{}n'.format(setting, value))

                click.echo('Created configuration file: {}'
                           .format(self.config_path))

    def _read_config(self):
        cfg = os.path.join(click.get_app_dir(APP_NAME), 'config.ini')
        parser = configparser.ConfigParser()
        parser.read([cfg])
        rv = {}

        for k, v in parser['DEFAULT'].items():
            rv[k] = v

        return rv


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
        PROFILER_API_TOKEN = API token (use get_token to obtain one).

    However the client largely uses config.ini which you can check config using
    print_config.
    """
    if token:
        config.settings['profiler_api_token'] = token

    if not config.settings['profiler_api_token']:
        click.secho('You are not authenticated.', fg='red')

    else:
        config.headers['X-Auth'] = config.settings['profiler_api_token']

    if app_host:
        config.settings['profiler_app_host'] = app_host

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
@click.option('--username', type=click.STRING, prompt=True, required=True)
@click.option('--password', type=click.STRING, prompt=True, required=True)
def get_token(config, username, password):
    """
    Obtain an API token.
    """
    auth_url = config.settings['profiler_app_host'] + '/api/authentication/'
    payload = {'email': username, 'password': password}
    response = requests.post(auth_url, json=payload, verify=False)
    response.raise_for_status()

    try:
        token = response.json()['token']
    except KeyError:
        raise ProfilerError('Authentication failed.')

    click.secho(token, fg='green')
    click.echo("Don't forget to update config.ini with the new token")


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
              default=60)
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
        click.secho('You need an API token for this. Run "get_token" '
                    'before proceeding', fg='red')
        sys.exit()

    reader = csv.reader(input_file)
    usernames = [item[0] for item in list(reader)]

    if not usernames:
        raise ProfilerError('No usernames found.')
    else:
        click.echo('[*] Extracted {} usernames.'.format(len(usernames)))

    username_url = config.settings['profiler_app_host'] + '/api/username/'
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
            response.raise_for_status()
            responses.append(response.content.decode('utf-8'))
            time.sleep(interval)

    click.secho('Submitted {} usernames.'.format(len(usernames)), fg='green')

    for response in responses:
        print_json(responses)


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
@pass_config
def get_results(config,
                input_file,
                output_file,
                interval,
                ignore_missing):
    """
    \b
    Return results for list of usernames.

    Each username requires minimum 2 API calls:

        1. Fetch archive for the username
        2. Fetch the results for the archive job ID

    Further API calls are required to fetch more than one page
    of results, e.g. if there are 160 results for a username, this
    rquires 3 request in total.

    Updates to Profiler should allow querying of the result
    endpoint by username.

    :param input_file (file): csv file containing 1 username per line.
    :param output_file (file): output file csv or jsonlines.
    :param interval (int): interval in seconds between API requests.
    """
    if not config.settings['profiler_api_token']:
        click.secho('You need an API token for this. Run "get_token" '
                    'before proceeding', fg='red')
        sys.exit()

    reader = csv.reader(input_file)
    usernames = [item[0] for item in list(reader)]

    if not usernames:
        raise ProfilerError('No usernames found.')
    else:
        click.echo('[*] Extracted {} usernames.'.format(len(usernames)))

    writer = csv.writer(output_file)

    with click.progressbar(usernames,
                           label='Getting username results: ') as bar:
        start = datetime.datetime.now()
        for username in bar:
            # Get results for username
            archive_url = '{}/api/archive/?username={}' \
                          .format(config.settings['profiler_app_host'],
                                  username)
            response = requests.get(archive_url,
                                    headers=config.headers,
                                    verify=False)
            time.sleep(interval)

            if ignore_missing:
                if response.status_code != 200:
                    continue
            else:
                response.raise_for_status()

            # Parse results
            archives = response.json().get('archives', [])

            for archive in archives:
                data = []
                results = get_job_results(config.settings['profiler_app_host'],
                                          config.headers,
                                          archive['tracker_id'],
                                          interval)

                for result in results:
                    row = [username,
                           result['site_name'],
                           result['site_url'],
                           result['status'],
                           result['error']
                           ]
                    data.append(row)
                # Write to output file
                writer.writerows(data)
                time.sleep(interval)

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
                type=click.Path(dir_okay=True, allow_dash=True),
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
    \b
    Return zip results for list of usernames.


    :param input_file (file): csv file containing 1 username per line.
    :param output_dir (dir): output directory for zip archives.
    :param interval (int): interval in seconds between API requests.
    """
    if not config.settings['profiler_api_token']:
        click.secho('You need an API token for this. Run "get_token" '
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
            archive_url = '{}/api/archive/?username={}' \
                          .format(config.settings['profiler_app_host'],
                                  username)
            response = requests.get(archive_url,
                                    headers=config.headers,
                                    verify=False)
            time.sleep(interval)

            if ignore_missing:
                if response.status_code != 200:
                    continue
            else:
                response.raise_for_status()

            # Parse results
            archives = response.json().get('archives', [])

            for archive in archives:
                filename = '{}-{}.zip' \
                           .format(username,
                                   archive['date'])
                response = requests.get(archive['zip_url'],
                                        headers=config.headers,
                                        verify=False)

                response.raise_for_status()

                with open(os.join(output_dir, filename), 'wb') as f:
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

    url = urllib.parse.urljoin(config.settings['profiler_app_host'], resource)
    response = requests.get(url, headers=config.headers, verify=False)
    response.raise_for_status()

    try:
        if pretty:
            print_json(response.content.decode('utf-8'))
        else:
            print(json.dumps(response.json()))
    except Exception:
        raise


def get_job_results(app_host, headers, tracker_id, interval):
    """
    Fetch all results for tracker_id.
    """
    result_url = '{}/api/result/job/{}'.format(app_host, tracker_id)
    page = 1
    pages = 1
    results = []

    while page <= pages:
        params = {'rpp': 100, 'page': page}
        response = requests.get(result_url,
                                headers=headers,
                                params=params,
                                verify=False)

        if response.status_code != 200:
            return results
        else:
            data = response.json()
            total = int(data['total_count'])
            if total > 0:
                pages = math.ceil(total / 100)

            results += data['results']
            page += 1
            time.sleep(interval)

    return results


if __name__ == '__main__':
    cli()
