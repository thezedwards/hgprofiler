from flask import g, jsonify, request
from flask.ext.classy import FlaskView, route

from app.authorization import login_required
from app.rest import get_paging_arguments
from model import Result


class ResultView(FlaskView):
    '''
    Profiler result list.
    '''

    decorators = [login_required]

    def index(self):
        '''
        Return an array of results.

        **Example Response**

        .. sourcecode:: json

            {
                "results": [
                    {
                        "id": 1,
                        "tracker_id": '2298d96a-653d-42f2-b6d3-73ff337d51ce',
                        "user_id": 1,
                        "site_id": 100,
                        "site_name": "Acme",
                        "site_url": "https://www.acme.com/%s",
                        "username": "bob",
                        "created_at": "2017-01-30T16:22:19.826841",
                        "status": "Found",
                        "html": "<html><head><title....",
                        "number": "5",
                        "total": "166",
                        "image_file_id": "1234"
                        "error": "",
                    },
                    ...
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list results: a list of result objects
        :>json int results[n].id: the unique id of this result
        :>json str results[n].tracker_id: the tracker_id of this result
        :>json str results[n].user_id: the id of owner of this result
        :>json str results[n].site_id: the ID of the result site
        :>json str results[n].site_name: the site name of this result
        :>json str results[n].site_url: the site URL of this result
        :>json str results[n].username: the username for this result
        :>json str results[n].created_at: the UTC time of the result
            in ISO-8601 format string
        :>json str results[n].status: result status (Found, Not Found, Error)
        :>json str results[n].image_file_id: the file
            ID of the result screenshot
        :>json str results[n].error: result error message

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)

        query = g.db.query(Result).filter(Result.user_id == g.user.id)

        total_count = query.count()

        query = query.limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        results = list()

        for result in query:
            results.append(result.as_dict())

        return jsonify(
            results=results,
            total_count=total_count
        )

    @route('/tracker/<string:tracker_id>')
    def get_by_tracker_id(self, tracker_id):
        '''
        Return results identified by `tracker_id`.

        **Example Response**

        .. sourcecode:: json

            {
                "results": [
                    {
                        "id": 1,
                        "tracker_id": '2298d96a-653d-42f2-b6d3-73ff337d51ce',
                        "user_id": 1,
                        "site_id": 100,
                        "site_name": "Acme",
                        "site_url": "https://www.acme.com/%s",
                        "username": "bob",
                        "created_at": "2017-01-30T16:22:19.826841",
                        "status": "Found",
                        "html": "<html><head><title....",
                        "number": "5",
                        "total": "166",
                        "image_file_id": "1234"
                        "error": "",
                    },
                    ...
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list results: a list of result objects
        :>json int results[n].id: the unique id of this result
        :>json str results[n].tracker_id: the tracker_id of this result
        :>json str results[n].user_id: the ID of the owner of this result
        :>json str results[n].site_id: the ID of the result site
        :>json str results[n].site_name: the site name of this result
        :>json str results[n].site_url: the site URL of this result
        :>json str results[n].username: the username for this result
        :>json str results[n].created_at: the UTC time of the result
            in ISO-8601 format string
        :>json str results[n].status: result status (Found, Not Found, Error)
        :>json str results[n].image_file_id: the file ID
            of the result screenshot
        :>json str results[n].error: result error message

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)

        query = g.db.query(Result).filter(
            Result.tracker_id == tracker_id).filter(
                Result.user_id == g.user.id)

        total_count = query.count()

        query = query.limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        results = list()

        for result in query:
            results.append(result.as_dict())

        return jsonify(
            results=results,
            total_count=total_count
        )

    @route('/username/<string:username>')
    def get_by_username(self, username):
        '''
        Return latest results for `username`.

        **Example Response**

        .. sourcecode:: json

            {
                "results": [
                    {
                        "id": 1,
                        "tracker_id": '2298d96a-653d-42f2-b6d3-73ff337d51ce',
                        "user_id": 1,
                        "site_id": 100,
                        "site_name": "Acme",
                        "site_url": "https://www.acme.com/%s",
                        "username": "bob",
                        "created_at": "2017-01-30T16:22:19.826841",
                        "status": "Found",
                        "html": "<html><head><title....",
                        "number": "5",
                        "total": "166",
                        "image_file_id": "1234"
                        "error": "",
                    },
                    ...
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list results: a list of result objects
        :>json int results[n].id: the unique id of this result
        :>json str results[n].tracker_id: the tracker_id of this result
        :>json str results[n].user_id: the ID of the owner of this result
        :>json str results[n].site_id: the ID of the result site
        :>json str results[n].site_name: the site name of this result
        :>json str results[n].site_url: the site URL of this result
        :>json str results[n].username: the username for this result
        :>json str results[n].created_at: the UTC time of the result
            in ISO-8601 format string
        :>json str results[n].status: result status (Found, Not Found, Error)
        :>json str results[n].image_file_id: the file ID
            of the result screenshot
        :>json str results[n].error: result error message

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)

        query = g.db.query(Result).filter(
            Result.username == username).filter(
                Result.user_id == g.user.id).order_by(
                    Result.site_name,
                    Result.created_at.desc()).distinct(
                        Result.site_name)

        total_count = query.count()

        query = query.limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        results = list()

        for result in query:
            results.append(result.as_dict())

        return jsonify(
            results=results,
            total_count=total_count
        )
