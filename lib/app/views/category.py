from flask import g, jsonify, request
from flask.ext.classy import FlaskView
from sqlalchemy.exc import IntegrityError, DBAPIError
from werkzeug.exceptions import BadRequest, NotFound

from app.authorization import login_required
from app.notify import notify_mask_client
from app.rest import (get_int_arg,
                      url_for,
                      get_paging_arguments,
                      validate_request_json,
                      validate_json_attr)
from model.category import Category
from model.site import Site

# Dictionary of category attributes used for
# validation of json POST/PUT requests
GROUP_ATTRS = {
    'name': {'type': str, 'required': True},
    'sites': {'type': list, 'required': True},
}


class CategoryView(FlaskView):
    '''
    Create, edit and retrieve sites categories used for username search.
    '''

    decorators = [login_required]

    def get(self, id_):
        '''
        Get the category identified by `id`.

        **Example Response**

        .. sourcecode: json

            {
                "id": 1,
                "name": "gender",
                "sites": [
                    {
                        "id": 2,
                        "name": "",
                        "url": "".
                        "status_code": "",
                        "search_pattern": "",
                        "category": ""
                    },
                    ...
                ]
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json int id: unique identifier for category
        :>json str name: the category name
        :>json str url: URL url-for for retriving more data about this category

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        :status 404: category does not exist
        '''

        # Get category.
        id_ = get_int_arg('id_', id_)
        category = g.db.query(Category).filter(Category.id == id_).first()

        if category is None:
            raise NotFound("Category '%s' does not exist." % id_)

        response = category.as_dict()
        response['url-for'] = url_for('CategoryView:get', id_=category.id)

        # Send response.
        return jsonify(**response)

    def post(self):
        '''
            Create a category.

            **Example Request**

            ..sourcode:: json

                {
                    "categories": [
                        {
                            "name": "gender",
                            "sites": [1, 2, 7]
                        },
                        ...
                    ]
                }

        **Example Response**

        ..sourcecode:: json

            {
                "message": "2 new categories created."
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json list categories: a list of categories to create
        :>json str categories[n].name: name of category to create

        :>header Content-Type: application/json
        :>json str message: api response message

        :status 200: created
        :status 400: invalid request body
        :status 401: authentication required
        '''

        request_json = request.get_json()
        categories = list()

        # Validate input
        for category_json in request_json['categories']:
            validate_request_json(category_json, GROUP_ATTRS)

            try:
                request_site_ids = [int(s) for s in category_json['sites']]
            except TypeError:
                raise BadRequest('Sites must be integer site ids')

            if len(request_site_ids) == 0:
                raise BadRequest('At least one site is required.')

            sites = g.db.query(Site)\
                        .filter(Site.id.in_(request_site_ids))\
                        .all()
            site_ids = [site.id for site in sites]
            missing_sites = list(set(request_site_ids) - set(site_ids))

            if len(missing_sites) > 0:
                raise BadRequest('Site ids {} do not exist'
                                 .format(
                                     ','.join(str(s) for s in missing_sites))
                                 )

        # Create categories
        for category_json in request_json['categories']:
            try:
                category = Category(
                    name=category_json['name'].lower().strip(),
                    sites=sites
                )
                g.db.add(category)
                g.db.flush()
                # Create dict for API JSON response
                category_dict = category.as_dict()
                # Add a link to the created category
                category_dict['url-for'] = url_for('CategoryView:get',
                                                   id_=category.id)
                categories.append(category_dict)
            except IntegrityError:
                g.db.rollback()
                raise BadRequest(
                    'Category "{}" already exists'.format(category.name)
                )

        # Save categories
        g.db.commit()

        # Send redis notifications
        for category in categories:
            notify_mask_client(
                channel='category',
                message={
                    'id': category['id'],
                    'name': category['name'],
                    'status': 'created',
                    'resource': category['url-for']
                }
            )

        message = '{} new categories created' \
                  .format(len(request_json['categories']))
        response = jsonify(
            message=message,
            categories=categories
        )
        response.status_code = 200

        return response

    def index(self):
        '''
        Return an array of all categories.

        **Example Response**

        .. sourcecode: json

            {
                "categories": [
                    {
                        "id": 1,
                        "name": "gender",
                        "sites": [
                            {
                                "category": "books",
                                "id": 2,
                                "name": "aNobil",
                                "search_text": "- aNobii</title>",
                                "status_code": 200,
                                "url": "http://www.anobii.com/%s/books"
                            },
                            ...
                        ]
                    },
                    ...
                ],
                "total_count": 2
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)

        :>header Content-Type: application/json
        :>json list categories: a list of category objects
        :>json str categories[n].category: the category category
        :>json int categories[n].id: unique identifier for category
        :>json str categories[n].name: the category name
        :>json list categories[n].sites: list of sites
            associated with this category
        :>json str categories[n].sites[n].category: the site category
        :>json str categories[n].sites[n].id: the unique id for site
        :>json str categories[n].sites[n].name: the site name
        :>json str categories[n].sites[n].search_text: string search pattern
        :>json str categories[n].sites[n].status_code:
            server response code for site
        :>json str categories[n].sites[n].url: the site url

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)
        query = g.db.query(Category)
        total_count = query.count()
        query = query.order_by(Category.name.asc()) \
                     .limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        categories = list()

        for category in query:
            data = category.as_dict()
            data['url-for'] = url_for('CategoryView:get', id_=category.id)
            categories.append(data)

        return jsonify(
            categories=categories,
            total_count=total_count
        )

    def put(self, id_):
        '''
        Update the category identified by `id`.

            **Example Request**

            ..sourcode:: json

                {
                    {
                        "name": "priority sites"
                        "sites": [1,5]
                    },
                }

        **Example Response**

        ..sourcecode:: json

            {
                "id": 1,
                "name": "priority sites",
                "sites": [
                    {
                        "category": "books",
                        "id": 1,
                        "name": "aNobil",
                        "search_text": "- aNobii</title>",
                        "status_code": 200,
                        "url": "http://www.anobii.com/%s/books"
                    },
                    {
                        "category": "coding",
                        "id": 5,
                        "name": "bitbucket",
                        "search_text": "\"username\":",
                        "status_code": 200,
                        "url": "https://bitbucket.org/api/2.0/users/%s"
                    },
                    ...
                ]
            },

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :>json str name: the value of the name attribute

        :>header Content-Type: application/json
        :>json int id: unique identifier for category
        :>json str name: the category name
        :>json list sites: list of sites associated with this category
        :>json str sites[n].category: the site category
        :>json str sites[n].id: the unique id for site
        :>json str sites[n].name: the site name
        :>json str sites[n].search_text: string search pattern
        :>json str sites[n].status_code: server response code for site
        :>json str sites[n].url: the site url

        :status 200: updated
        :status 400: invalid request body
        :status 401: authentication required
        '''
        editable_fields = ['name', 'sites']
        # Get category.
        id_ = get_int_arg('id_', id_)
        category = g.db.query(Category).filter(Category.id == id_).first()

        if category is None:
            raise NotFound("Category '%s' does not exist." % id_)

        request_json = request.get_json()

        # Validate data and set attributes
        if request_json is None:
            raise BadRequest("Specify at least one editable field: {}"
                             .format(editable_fields))

        for field in request_json:
            if field not in editable_fields:
                raise BadRequest("'{}' is not one of the editable fields: {}"
                                 .format(field, editable_fields)
                                 )

        if 'name' in request_json:
            validate_json_attr('name', GROUP_ATTRS, request_json)
            category.name = request_json['name'].lower().strip()

        if 'sites' in request_json:
            try:
                request_site_ids = [int(s) for s in request_json['sites']]
            except ValueError:
                raise BadRequest('Sites must be a list of integer site ids')

            if len(request_site_ids) == 0:
                raise BadRequest('Categorys must have at least one site')

            sites = g.db.query(Site) \
                .filter(Site.id.in_(request_site_ids)) \
                .all()
            site_ids = [site.id for site in sites]
            missing_sites = list(set(request_site_ids) - set(site_ids))

            if len(missing_sites) > 0:
                raise BadRequest('Site ids "{}" do not exist'
                                 .format(','.join(missing_sites)))
            else:
                category.sites = sites

        # Save the updated category
        g.db.add(category)
        try:
            g.db.commit()
        except DBAPIError as e:
            g.db.rollback()
            raise BadRequest('Database error: {}'.format(e))

        # Send redis notifications
        notify_mask_client(
            channel='category',
            message={
                'id': category.id,
                'name': category.name,
                'status': 'updated',
                'resource': url_for('CategoryView:get', id_=category.id)
            }
        )

        response = category.as_dict()
        response['url-for'] = url_for('CategoryView:get', id_=category.id)

        # Send response.
        return jsonify(**response)

    def delete(self, id_):
        '''
        Delete the category identified by `id`.

        **Example Response**

        ..sourcecode:: json

            {
                "message": "Category `main` deleted",
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token

        :>header Content-Type: application/json
        :>json str message: the API response message

        :status 200: deleted
        :status 400: invalid request body
        :status 401: authentication required
        :status 404: category does not exist
        '''

        # Get label.
        id_ = get_int_arg('id_', id_)
        category = g.db.query(Category).filter(Category.id == id_).first()

        if category is None:
            raise NotFound("Category '%s' does not exist." % id_)

        # Delete label
        g.db.delete(category)

        try:
            g.db.commit()
        except IntegrityError:
            g.db.rollback()
            raise BadRequest('You must delete archived results that'
                             'use category "{}" before it can be deleted.'
                             .format(category.name))
        except DBAPIError as e:
            g.db.rollback()
            raise BadRequest('Database error: {}'.format(e))

        # Send redis notifications
        notify_mask_client(
            channel='category',
            message={
                'id': category.id,
                'name': category.name,
                'status': 'deleted',
                'resource': None
            }
        )

        message = 'Category id "{}" deleted'.format(category.id)
        response = jsonify(message=message)
        response.status_code = 200

        return response
