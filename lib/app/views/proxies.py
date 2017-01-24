from flask import g, jsonify, request
from flask.ext.classy import FlaskView
from werkzeug.exceptions import BadRequest, NotFound
from sqlalchemy.exc import DBAPIError, IntegrityError

from app.authorization import admin_required
from app.notify import notify_mask_client
from app.rest import get_int_arg, validate_request_json

from model import Proxy


# Dictionary of proxy attributes used for validation of json POST/PUT requests
PROXY_ATTRS = {
    'protocol': {'type': str, 'required': True},
    'host': {'type': str, 'required': True},
    'port': {'type': int, 'required': True},
    'username': {'type': str, 'required': False, 'allow_null': True},
    'password': {'type': str, 'required': False, 'allow_null': True},
    'active': {'type': bool, 'required': True},
}


class ProxiesView(FlaskView):
    '''
    Set proxies.

    Requires an administrator account.
    '''

    decorators = [admin_required]

    def index(self):
        '''
        List proxies.

        **Example Response**

        .. sourcecode:: json

            {
                "proxies": [
                    {
                        "id": 1,
                        "protocol": "http",
                        "host": "192.168.0.1",
                        "port": 80,
                        "username": "user",
                        "password": "pass",
                        "active": true,
                    },
                    ...
                ]
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json list proxies: list of proxies
        :>json int proxies[n]["id"]: unique identifier
        :>json str proxies[n]["protocol"]: protocol of proxy address
        :>json str proxies[n]["host"]: host of proxy address
        :>json int proxies[n]["port"]: port of proxy address
        :>json str proxies[n]["username"]: username of proxy
        :>json str proxies[n]["password"]: password of proxy
        :>json bool proxies[n]["active"]: proxy active status

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        '''

        proxies = list()
        query = g.db.query(Proxy)
        total_count = query.count()

        for proxy in query:
            proxies.append(proxy.as_dict())

        return jsonify(proxies=proxies, total_count=total_count)

    def get(self, id_):
        raise BadRequest('End point not configured')

    def post(self):
        '''
        Create new proxies.

        **Example Request**

        .. sourcecode:: json

            {
                "proxies": [
                    {
                        "protocol": "http",
                        "host": "192.168.0.2",
                        "port": 80,
                        "username": "user",
                        "password": "pass",
                        "active": true,
                    },
                    ...
                ]
            }

        **Example Response**

        .. sourcecode:: json

            {
                "message": "1 proxy created."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :<json list proxies: list of proxies
        :<json str proxies[n]["protocol"]: protocol of proxy address
        :<json str proxies[n]["host"]: host of proxy address
        :<json int proxies[n]["port"]: port of proxy address
        :<json str proxies[n]["username"]: username of proxy
        :<json str proxies[n]["password"]: password of proxy
        :<json bool proxies[n]["active"]: proxy active status

        :>header Content-Type: application/json
        :>json string message: API response message

        :status 200: created
        :status 400: invalid request body
        :status 401: authentication required
        '''
        request_json = request.get_json()
        proxies = []

        # Ensure all data is valid before db operations
        for proxy_json in request_json['proxies']:
            validate_request_json(proxy_json, PROXY_ATTRS)

        # Save proxies
        for proxy_json in request_json['proxies']:
            proxy = Proxy(protocol=proxy_json['protocol'].lower().strip(),
                          host=proxy_json['host'].lower().strip(),
                          port=proxy_json['port'],
                          active=proxy_json['active'])

            # Username is optional, and can be None
            try:
                proxy.username = proxy_json['username'].lower().strip()
            except KeyError:
                pass
            except AttributeError:
                proxy.username = None

            # Password is optional, and can be None
            try:
                proxy.password = proxy_json['password'].strip()
            except KeyError:
                pass
            except AttributeError:
                proxy.password = None

            g.db.add(proxy)

            try:
                g.db.flush()
                proxies.append(proxy)
            except IntegrityError:
                g.db.rollback()
                raise BadRequest(
                    'Proxy {}://{}:{} already exists.'.format(proxy.protocol,
                                                              proxy.host,
                                                              proxy.port)
                )

        g.db.commit()

        # Send redis notifications
        for proxy in proxies:
            notify_mask_client(
                channel='proxy',
                message={
                    'proxy': proxy.as_dict(),
                    'status': 'created',
                    'resource': None
                }
            )

        message = '{} new proxies created'.format(len(request_json['proxies']))
        response = jsonify(message=message)
        response.status_code = 202

        return response

    def put(self, id_):
        '''
        Update proxy identified by `id`.

        **Example Request**

        .. sourcecode:: json

            PUT /api/proxies/id
            {
                "protocol": "http",
                "host": "192.168.0.2",
                "port": 80,
                "username": "user",
                "password": "pass",
                "active": true,
            }

        **Example Response**

        .. sourcecode:: json

            {
                "id": 1,
                "protocol": "http",
                "host": "192.168.0.22",
                "port": 80,
                "username": "user",
                "password": "pass",
                "active": true,
            },

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json str protocol: protocol of proxy address
        :>json str host: host of proxy address
        :>json int port: port of proxy address
        :>json str username: username of proxy
        :>json str password: password of proxy
        :>json bool active: proxy active status

        :>header Content-Type: application/json
        :>json int id: unique identifier
        :>json str protocol: protocol of proxy address
        :>json str host: host of proxy address
        :>json int port: port of proxy address
        :>json str username: username of proxy
        :>json str password: password of proxy
        :>json bool active: proxy active status

        :status 200: ok
        :status 401: authentication required
        :status 403: must be an administrator
        '''

        # Get proxy
        id_ = get_int_arg('id_', id_)
        proxy = g.db.query(Proxy).filter(Proxy.id == id_).first()

        if proxy is None:
            raise NotFound("Proxy '%s' does not exist." % id_)

        # Validate request json
        request_json = request.get_json()
        validate_request_json(request_json, PROXY_ATTRS)

        # Update proxy
        proxy.protocol = request_json['protocol']
        proxy.host = request_json['host']
        proxy.port = request_json['port']
        proxy.active = request_json['active']

        try:
            proxy.username = request_json['username']
        except KeyError:
            pass

        try:
            proxy.password = request_json['password']
        except KeyError:
            pass

        # Save the updated proxy
        try:
            g.db.commit()
        except DBAPIError as e:
            g.db.rollback()
            raise BadRequest('Database error: {}'.format(e))

        # Send redis notifications
        notify_mask_client(
            channel='proxy',
            message={
                'proxy': proxy.as_dict(),
                'status': 'updated',
                'resource': None
            }
        )

        response = jsonify(proxy.as_dict())
        response.status_code = 200

        # Send response
        return response

    def delete(self, id_):
        '''
        Delete proxy identified by `id_`.
        '''
        # Get proxy.
        id_ = get_int_arg('id_', id_)
        proxy = g.db.query(Proxy).filter(Proxy.id == id_).first()

        if proxy is None:
            raise NotFound("Proxy '%s' does not exist." % id_)

        # Delete proxy
        try:
            g.db.delete(proxy)
            g.db.commit()
        except IntegrityError:
            g.db.rollback()
            raise BadRequest('Could not delete proxy.')

        # Send redis notifications
        notify_mask_client(
            channel='proxy',
            message={
                'proxy': proxy.as_dict(),
                'status': 'deleted',
                'resource': None
            }
        )

        message = 'Proxy id "{}" deleted'.format(id_)
        response = jsonify(message=message)
        response.status_code = 200

        return response
