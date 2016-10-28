************
Architecture
************

.. contents::
    :depth: 2

Diagram
=======

The following diagram shows the high level components of this system and how
they are interconnected.

.. graphviz::

    digraph system_diagram {
        node [shape=box, target="_top"];

        // Nodes
        dart           [label="Dart Client"];
        flask          [label="Flask"];
        other_client   [label="Other API Client"];
        redis          [label="Redis"];
        postgres       [label="Postgres"];
        worker_archive [label="Archive Worker"];
        worker_scrape  [label="Scrape Worker"];

        // Edges
        flask -> redis [dir=both];
        flask -> postgres [dir=both];
        flask -> dart [dir=both];
        flask -> other_client [dir=both];
        redis -> {worker_archive, worker_scrape} [dir=both];
    }

Dart & Other API Clients
========================

The web client is written in Dart as a single-page application (SPA) that
communicates with the server exclusively through the API (and also to load
static assets). This design ensures that anything that can be done through the
human user interface can also be done by a machine through the REST API. It also
opens up the possibility of writing clients for other platforms, such as Android
or iOS.

Although primarily targeting desktop/laptop users, the Dart client is also
intended (although not yet thoroghly tested) to work smoothly on smaller devices
like tablets and phones. The Dart client should scale its UI appropriately for
all of these devices and should be accessible to users who are not using a
mouse.

Flask
=====

Flask is the main application server and the hub of the entire system. It
exposes a REST API for communication with its clients. It also serves static
assets such as Dart/JavaScript source code, images, styles, etc. Flask also
interacts with various data stores to persist and query data.

.. note:: We use Apache as
    sort of a front-end proxy for Flask because Apache automatically manages
    workers (Flask does not) and Apache can serve static assets much more
    quickly than Flask. Apache and WSGI are transparent in this setup,
    so we did not include them in the diagram above.

Postgres
========

The application uses Postgres as its authoritative data store. Redundant data
may be stored in other places (e.g. Redis, Solr) but in the case of conflicts,
Postgres is always assumed to be correct.

Redis
=====

Redis serves two purposes: it is both a cache and a message queue. The cache is
used to store state that is expensive to compute and changes infrequently. The
message queue is used for decentralized processing. In particular, we want the
REST API to have low latency. Any API call that triggers lengthy computation
should be delegated to an external worker using the message queue, allowing the
API to return a response before that lengthy computation finishes.

Workers
=======

As an example of an external worker, the Index Worker handles requests to update
search indicies. In a typical workflow, the Flask server will process an API
request that updates some data in Postgres. Postgres and Solr are now
inconsistent, and the Solr index needs to be updated in order to become
consistent again. Flask will queue a request with Redis, Redis will dequeue the
request to an index worker, and then the worker will update the Solr index.
