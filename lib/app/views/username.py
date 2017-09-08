from flask import g, jsonify, request
from flask.ext.classy import FlaskView
from werkzeug.exceptions import BadRequest, NotFound

import app.config
import worker.scrape
from app.authorization import login_required
from app.rest import validate_request_json
from helper.functions import random_string
from model import Category, Site


_username_attrs = {
    'usernames': {'type': list, 'required': True},
    'category': {'type': int, 'required': False},
    'site': {'type': int, 'required': False},
    'test': {'type': bool, 'required': False},
}

_config = app.config.get_config()
_redis_worker = dict(_config.items('redis_worker'))


class UsernameView(FlaskView):
    '''
    Search and retrieve usernames from the web using background workers.
    '''

    decorators = [login_required]

    def post(self):
        '''
        Request search of usernames.

        **Example Request**

        .. sourcecode:: json

            {
                "usernames": [
                    "johndoe",
                    "janedoe",
                    ...
                ],
                "category": 3,
                "test": False,
            }

        **Example Response**

        .. sourcecode:: json

            {
                "tracker_ids": {
                        "johndoe": "tracker.12344565",
                }
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json list usernames: a list of usernames to search for
        :>json int category: ID of site category to use (optional)
        :>json int site: ID of site to search (optional)
        :>json bool test: test results (optional, default: false)

        :>header Content-Type: application/json
        :>json list jobs: list of worker jobs
        :>json list jobs[n].id: unique id of this job
        :>json list jobs[n].usename: username target of this job

        :status 202: accepted for background processing
        :status 400: invalid request body
        :status 401: authentication required
        '''
        test = False
        category = None
        category_id = None
        jobs = []
        tracker_ids = dict()
        redis = g.redis
        request_json = request.get_json()
        site = None

        if 'usernames' not in request_json:
            raise BadRequest('`usernames` is required')

        validate_request_json(request_json, _username_attrs)

        if len(request_json['usernames']) == 0:
            raise BadRequest('At least one username is required')

        if 'category' in request_json and 'site' in request_json:
            raise BadRequest('Supply either `category` or `site`.')

        if 'category' in request_json:
            category_id = request_json['category']
            category = g.db.query(Category) \
                .filter(Category.id == category_id).first()

            if category is None:
                raise NotFound("Category '%s' does not exist." % category_id)
            else:
                category_id = category.id

        if 'site' in request_json:
            site_id = request_json['site']
            site = g.db.query(Site).filter(Site.id == site_id).first()

            if site is None:
                raise NotFound("Site '%s' does not exist." % site_id)

        if 'test' in request_json:
            test = request_json['test']

        if category:
            sites = category.sites
        elif site:
            sites = g.db.query(Site).filter(Site.id == site.id).all()
        else:
            sites = g.db.query(Site).all()

        # Only check valid sites.
        valid_sites = []
        for site in sites:
            if site.valid:
                valid_sites.append(site)

        # sites = sites.filter(Site.valid == True).all() # noqa
        usernames = request_json['usernames']
        requests = len(valid_sites) * usernames
        if requests > g.user.credits:
            raise BadRequest('Insufficient credits.')

        if len(valid_sites) == 0:
            raise NotFound('No valid sites to check')

        for username in usernames:
            # Create an object in redis to track the number of sites completed
            # in this search.
            tracker_id = 'tracker.{}'.format(random_string(10))
            tracker_ids[username] = tracker_id
            redis.set(tracker_id, 0)
            redis.expire(tracker_id, 600)
            total = len(valid_sites)

            # Queue a job for each site.
            for site in valid_sites:
                description = 'Checking {} for user "{}"'.format(site.name,
                                                                 username)
                job = worker.scrape.check_username.enqueue(
                    username=username,
                    site_id=site.id,
                    category_id=category_id,
                    total=total,
                    tracker_id=tracker_id,
                    test=test,
                    jobdesc=description,
                    timeout=_redis_worker['username_timeout'],
                    user_id=g.user.id
                )
                jobs.append({
                    'id': job.id,
                    'username': username,
                    'category': category_id,
                })

        response = jsonify(tracker_ids=tracker_ids)
        response.status_code = 202

        return response
