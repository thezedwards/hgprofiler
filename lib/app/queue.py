''' Message queues. '''

from functools import wraps
from rq import Connection, Queue

import coalesce as co
import app.config

_config = app.config.get_config()
_redis = app.database.get_redis(dict(_config.items('redis')))
_redis_worker = dict(_config.items('redis_worker'))
scrape_queue = Queue('scrape', connection=_redis)
archive_queue = Queue('archive', connection=_redis)


def dummy_job():
    '''
    This dummy job is used by init_queues().
    It must be defined at the module level so that Python RQ can import it;
    it cannot be an anonymous or nested function.
    '''
    pass


def init_queues(redis):
    '''
    Python RQ creates queues lazily, but we want them created eagerly.
    This function submits a dummy job to each queue to force Python RQ to
    create that queue.
    '''
    queues = {q for q in globals().values() if type(q) is Queue}

    with Connection(redis):
        for queue in queues:
            queue.enqueue(dummy_job)


def clear_queues(*names):
    ''' Remove all jobs from the named queues. '''

    queues = get_queues()

    with Connection(_redis):
        for name in names:
            queues[name].empty()


def get_queues():
    '''
    Return a dict of all the queues exported by this module.
    Keys are queue names and values are the queue objects.
    '''

    return {q.name: q for q in globals().values() if type(q) is Queue}


class queueable:
    '''
    A decorator for indicating that a function can be queued for later
    execution via python-rq.
    The decorated function will have an ``enqueue()`` method added to it that,
    when invoked, pushes the function onto a pre-specified job queue.
    Based on the ``job`` decorator in python-rq but it supports some extra
    arguments unique to this application.
    The constructor supports the following keyword arguments:
        * "jobdesc" is assigned to job.meta['description'].
        * "jobflags" is a list of strings assigned to job.meta['flags']
        * "queue" is the default queue that this job will be sent to.
        * "timeout" is the job's timeout.
    Any of these keywords can be passed to the decorator's constructor or to
    the ``enqueue()`` method.
    '''

    def __init__(self, queue=None, timeout=60, jobdesc=None, jobflags=None):
        ''' Constructor. '''

        self.queue = queue
        self.timeout = timeout
        self.jobdesc = jobdesc
        self.jobflags = co.first(jobflags, lambda: list)

    def __call__(self, fn):
        ''' Wraps a queue-able function. '''

        @wraps(fn)
        def enqueue(*args, **kwargs):
            jobdesc = co.first(kwargs.pop('jobdesc', None), self.jobdesc)
            jobflags = co.first(kwargs.pop('jobflags', None), self.jobflags)
            queue = co.first(kwargs.pop('queue', None), self.queue)
            timeout = co.first(kwargs.pop('timeout', None), self.timeout)

            if queue is None:
                raise ValueError('This job has no queue defined.')

            job = queue.enqueue_call(
                fn,
                args=args,
                kwargs=kwargs,
                timeout=timeout
            )

            job.meta['description'] = jobdesc
            job.meta['flags'] = list(jobflags)
            job.save()
            return job

        fn.enqueue = enqueue
        return fn


def remove_unused_queues(redis):
    '''
    Remove queues in RQ that are not defined in this file.
    This is useful for removing queues that used to be defined but were later
    removed.
    '''
    queue_names = {q.name for q in globals().values() if type(q) is Queue}

    with Connection(redis):
        for queue in Queue.all():
            if queue.name not in queue_names:
                queue.empty()
                redis.srem('rq:queues', 'rq:queue:{}'.format(queue.name))


#def schedule_username(username, site, category_id,
#                      total, tracker_id, test=False):
#    '''
#    Queue a job to fetch results for the specified username from the specified
#    site.
#
#    Keyword arguments:
#    test -- don't archive, update site with result (default: False)
#    '''
#
#    kwargs = {
#        'username': username,
#        'site_id': site.id,
#        'category_id': category_id,
#        'total': total,
#        'tracker_id': tracker_id,
#        'test': test
#    }
#
#    job = scrape_queue.enqueue_call(
#        func=worker.scrape.check_username,
#        kwargs=kwargs,
#        timeout=_redis_worker['username_timeout']
#    )
#
#    description = 'Checking {} for user "{}"'.format(site.name, username)
#
#    worker.init_job(job=job, description=description)
#
#    return job.id
#
#
#def schedule_archive(username, category_id, tracker_id):
#    ''' Queue a job to archive results for the job id. '''
#
#    job = archive_queue.enqueue_call(
#        func=worker.archive.create_archive,
#        args=[username, category_id, tracker_id],
#        timeout=_redis_worker['archive_timeout']
#    )
#
#    description = 'Archiving results for username "{}"'.format(username)
#
#    worker.init_job(job=job, description=description)
#
#
#def schedule_site_test(site, tracker_id):
#    '''
#    Queue a job to test a site.
#
#    Arguments:
#    site -- the site to test.
#    tracker_id -- the unique tracker ID for the job.
#    '''
#
#    job = scrape_queue.enqueue_call(
#        func=worker.scrape.test_site,
#        args=[site.id, tracker_id],
#        timeout=30
#    )
#
#    description = 'Testing site "{}"'.format(site.name)
#
#    worker.init_job(job=job, description=description)
#
#    return job.id
