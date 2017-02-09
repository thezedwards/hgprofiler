import base64
import json

import app.database
import cli
from worker.scrape import splash_request


class DebugCli(cli.BaseCli):
    """ A tool for debugging. """

    def _get_args(self, arg_parser):
        """ Customize arguments. """

        sub_parsers = arg_parser.add_subparsers(dest='action',
                                                help='Action help')
        sub_parsers.required = True

        # Splash sub-commands
        splash_parser = sub_parsers.add_parser('splash',
                                               help='Print splash response')

        splash_parser.add_argument('-H',
                                   '--headers',
                                   action='store_true',
                                   help='Print response headers')

        splash_parser.add_argument('-B',
                                   '--body',
                                   action='store_true',
                                   help='Print response body')

        splash_parser.add_argument('--har',
                                   action='store_true',
                                   help='Print request interaction '
                                        'in har format')

        splash_parser.add_argument('-S',
                                   '--status-code',
                                   action='store_true',
                                   help='Print response status code')

        splash_parser.add_argument('-I',
                                   '--image',
                                   action='store_true',
                                   help='Print response image')

        splash_parser.add_argument('-o',
                                   '--output-file',
                                   type=str,
                                   help='Output file')

        splash_parser.add_argument('url', type=str, help='The request URL')

    def _validate_splash_args(self, args):
        """
        Validate conditional splash arguments.
        """
        # Exclusive opts cannot be combined with one another
        exclusive_opts = [args.headers, args.body,
                          args.status_code, args.image, args.har]

        selected_opts = [x for x in exclusive_opts if x]

        if len(selected_opts) > 1:
            raise ValueError('Select only one from {}'
                             .format(','.join(selected_opts)))

        # Require output file for image
        if args.image and not args.output_file:
            raise ValueError('--output-file required for --image')

        if args.output_file:
            try:
                open(args.output_file, 'w')
            except:
                raise ValueError('--output-file not writeable')

    def _run(self, args, config):
        """ Main entry point. """

        # Connect to database.
        database_config = dict(config.items('database'))
        self._db = app.database.get_engine(database_config, super_user=True)

        # Run splash commands.
        if args.action == 'splash':
            data = None
            self._validate_splash_args(args)
            self._logger.info('Requesting {}'.format(args.url))
            splash_response = splash_request(target_url=args.url)

            try:
                response_json = splash_response.json()
            except:
                raise

            # Get response headers
            try:
                json_data = response_json['history'][0]['response']['headers']
                headers = json.dumps(json_data,
                                     indent=4,
                                     sort_keys=True)
            except:
                print('Request failed entering python debugger..')
                import pdb
                pdb.set_trace()

            if args.headers:
                data = headers

            elif args.body:
                try:
                    data = response_json['html']
                except KeyError:
                    # Print headers on failure
                    data = headers

            elif args.status_code:
                data = splash_response.status_code

            elif args.image:
                try:
                    img = splash_response.json()['png']
                    data = base64.decodestring(img.encode('utf8'))
                except KeyError:
                    # Print headers if no png
                    data = headers
                except:
                    raise

            elif args.har:
                try:
                    data = json.dumps(splash_response.json()['har'],
                                      indent=4,
                                      sort_keys=True)
                except KeyError:
                    # Print headers if no har
                    data = headers

            else:
                data = json.dumps(splash_response.json(),
                                  indent=4,
                                  sort_keys=True)

            # Write to output file if given
            if args.output_file:
                with open(args.output_file, 'wb') as f:
                    f.write(data)
            else:
                print(data)
