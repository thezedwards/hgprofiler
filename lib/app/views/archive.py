from flask import g, jsonify, request
from flask.ext.classy import FlaskView
from werkzeug.exceptions import BadRequest, NotFound
from sqlalchemy.exc import IntegrityError

from app.authorization import login_required
from app.notify import notify_mask_client
from app.rest import (get_int_arg,
                      get_paging_arguments)
from model import Archive, Category


class ArchiveView(FlaskView):
    '''
    Profiler result archives list.
    '''

    decorators = [login_required]

    def index(self):
        '''
        Return an array of result archives.

        **Example Response**

        .. sourcecode:: json

            {
                "archives": [
                    {
                        "id": 1,
                        "job_id": '2298d96a-653d-42f2-b6d3-73ff337d51ce',
                        "user_id": 1,
                        "username": "bob",
                        "date": "",
                        "site_count": 166,
                        "found_count": 65,
                        "not_found_count": 101,
                        "error_count": 9,
                        "zip_file": "bob-2298d96a-653d-42f2.zip",
                        "category_id": 2,
                        "category_name": "Business",
                    },
                    ...
                ],
                "total_count": 5
            }

        :<header Content-Type: application/json
        :<header X-Auth: the client's auth token
        :query page: the page number to display (default: 1)
        :query rpp: the number of results per page (default: 10)
        :query username: filter by matching usernames

        :>header Content-Type: application/json
        :>json list archives: a list of result archive objects
        :>json str archives[n].job_id: the job_id of this archive
        :>json int archives[n].id: the unique id of this archive
        :>json str archives[n].user_id: the user_id of the owner of
            this archive
        :>json str archives[n].username: the archive username
        :>json str archives[n].date: the archive creation date
        :>json str archives[n].site_count: the number of site
            results in this archive
        :>json str archives[n].found_count: the number sites in
            this archive with a username match
        :>json str archives[n].not_found_count: the number sites in
            this archive with no username
        match
        :>json str archives[n].error_count: the number sites in
            this archive that raised an error
        while searching for username
        :>json str archives[n].zip_file: the zip file location for this archive
        :>json str archives[n].category_id: category ID of the archive
        :>json str archives[n].category_name: category name of the archive

        :status 200: ok
        :status 400: invalid argument[s]
        :status 401: authentication required
        '''

        page, results_per_page = get_paging_arguments(request.args)
        username = request.args.get('username', '')

        query = g.db.query(Archive).filter(Archive.user_id == g.user.id)

        if username:
            query = query.filter(Archive.username == username)

        total_count = query.count()

        query = query.order_by(Archive.date.desc()) \
                     .limit(results_per_page) \
                     .offset((page - 1) * results_per_page)

        # Get categories
        categories = {}
        for category in g.db.query(Category).all():
            categories[category.id] = category.name

        archives = list()

        for archive in query:
            archive_dict = archive.as_dict()
            try:
                archive_dict['category_name'] = categories[archive.category_id]
            except KeyError:
                archive_dict['category_name'] = 'All sites'

            archives.append(archive_dict)

        return jsonify(
            archives=archives,
            total_count=total_count
        )

    def get(self, id_):
        '''
        Get archive identified by `id_`.
        '''
        raise BadRequest('Endpoint not configured')

    def delete(self, id_):
        '''
        Delete archive identified by `id_`.
        '''
        # Get site.
        id_ = get_int_arg('id_', id_)
        archive = g.db.query(Archive).filter(Archive.id == id_).filter(
            Archive.user_id == g.user.id).first()

        if archive is None:
            raise NotFound("Archive '%s' does not exist." % id_)

        # Delete site
        try:
            g.db.delete(archive)
            g.db.commit()
        except IntegrityError:
            g.db.rollback()
            raise BadRequest('Could not delete archive.')

        # Send redis notifications
        notify_mask_client(
            channel='archive',
            message={
                'id': archive.id,
                'name': archive.username,
                'status': 'deleted',
                'resource': None
            }
        )

        message = 'Archive id "{}" deleted'.format(id_)
        response = jsonify(message=message)
        response.status_code = 200

        return response
