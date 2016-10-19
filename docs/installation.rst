.. _installation:

******************
Installation Guide
******************

.. contents::
    :depth: 3

Production Installation
=======================

Prerequisites
-------------

First, install Docker.

.. code::

    $ sudo apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 \
                       --recv-keys 58118E89F3A912897C070ADBF76221572C52609D
    $ echo "deb https://apt.dockerproject.org/repo ubuntu-trusty main" \
        | sudo tee /etc/apt/sources.list.d/docker.list
    $ sudo apt-get update
    $ sudo apt-get install docker-engine

You might want to add yourself to the ``docker`` group. If you don't do this,
you'll have to run all Docker commands with ``sudo``.

.. code::

    $ sudo usermod -aG docker <yourname>

Log out and back in to make the new group take effect. You can test this group
membership by running a Docker command.

.. code::

    $ docker ps
    CONTAINER ID    IMAGE    COMMAND    CREATED    STATUS    PORTS    NAMES

If successful, you'll see an empty table with the table headers. If
unsuccessful, you'll get an error: "Cannot connect to the Docker daemon..."

Next, install Docker Compose.

.. code::

    $ sudo -H pip install docker-compose

Now you need a copy of the `HG Docker repository <https://github.com/TeamHG-
Memex/docker>`__. You can clone this from GitHub or get just download a tarball.
We will assume that ``$DOCKER_REPO`` is set to the path where you
downloaded this repo.

.. code::

    $ DOCKER_REPO=/opt/docker
    $ cd $(dirname $DOCKER_REPO)

    # Clone it...
    $ git clone https://github.com/TeamHG-Memex/docker.git

    # ...or download a tarball.
    $ curl https://github.com/TeamHG-Memex/docker/archive/$master.tar.gz | \
           tar xf --transform='s:docker-[^/]*:docker:'

Either command will place the contents into a directory called ``docker`` in
your current directory.

Docker Registry
---------------

We use a private registry server. You need to log in to this server before you
can obtain any of the Docker image (this requires credentials).

.. code::

    $ docker login https://docker.hyperiongray.com

Running Profiler
----------------

Finally, use Docker Compose to start the entire stack. The first time you run
this, it will need to acquire a few images from Docker Hub and from the
private registry, which takes a while. Subsequent runs will generally be faster
because the images have already been downloaded.

.. code ::

    $ cd $DOCKER_REPO/profiler
    $ docker-compose up -d

Profiler will try to use ports 80 and 443 by default. On a shared server, this
may be undesirable, but unfortunately it seems that there is no command line
option to override this port number, so you need to edit ``docker-compose.yml``
and change ``443:443`` to ``8443:443`` (or whatever other port you have
selected).

The ``docker-compose`` command runs in the foreground, so typically you should
either run it inside ``screen``, run it with ``nohup``, or pass the background
daemon (``-d``) flag. The example above shows daemon mode, but running in the
foreground can be useful for debugging.

Upgrading Profiler
------------------

Docker also makes it easy to upgrade Profiler.

.. code ::

    $ cd $DOCKER_REPO/profiler
    $ git pull
    $ docker-compose up -d

Create TLS Certificates
-----------------------

The ``profiler_app`` container will generate a self-signed certificate when it
is first instantiated. This is useful for testing, but not practical for a
production deployment. We can generate a free, valid certificate using `Lets
Encrypt <https://letsencrypt.org/>`__.

First, we need to install the client.

.. code::

    $ cd /opt
    $ sudo git clone https://github.com/letsencrypt/letsencrypt

Now we need to generate our first certificate. (A private key will automatically
be generated for us.) LetsEncrypt uses a challenge/response mechanism over port
80 to verify that you are the owner of the claimed domain, but this isn't
possible while Profiler is running because Profiler will bind to port 80.

.. code::

    $ docker stop profiler_app
    $ /opt/letsencrypt/letsencrypt-auto certonly --standalone

When prompted, enter in the domain name(s) to be included in the certificate.

This script will generate certificates and keys and store them in
``/etc/letsencrypt/live/<domain>``, e.g. if the domain is ``foo.com``
then you'll see:

.. code::

    $ sudo ls -lah /etc/letsencrypt/live/foo.com
    lrwxrwxrwx 1 root root   54 May  3 17:02 cert.pem -> ../../archive/foo.com/cert2.pem
    lrwxrwxrwx 1 root root   55 May  3 17:02 chain.pem -> ../../archive/foo.com/chain2.pem
    lrwxrwxrwx 1 root root   59 May  3 17:02 fullchain.pem -> ../../archive/foo.com/fullchain2.pem
    lrwxrwxrwx 1 root root   57 May  3 17:02 privkey.pem -> ../../archive/foo.com/privkey2.pem

The TLS credentials are generated outside of the Profiler container, so you'll
need to mount them into the container. Edit the ``docker-compose.yml`` and add
two lines to the volumes directive:

.. code::

    services:
      app:
        image: docker.hyperiongray.com/profiler:0.1.0
        container_name: profiler_app
        volumes:
          - app_conf:/hgprofiler/conf
          - app_data:/hgprofiler/data
          - /etc/letsencrypt/live/foo.com/fullchain.pem:/etc/apache2/server.crt
          - /etc/letsencrypt/live/foo.com/privkey.pem:/etc/apache2/server.key

Only the last two lines are added. The other lines already exist in ``docker-
compose.yml``. Make sure to change ``foo.com`` to your actual domain name.

Now you can restart the docker container:

.. code::

    $ cd $DOCKER_REPO/profiler
    $ docker-compose up

Now you should browse to your server and verify that you have a valid TLS
certificate.

Renew TLS Certificates
----------------------

Certificates issued by LetsEncrypt expire after 90 days. This short window is
intended to motivate sysadmins to automate the process of renewing certificates
and reducing the likelihood of letting certificates expire.

We can implement the renewal process using a daily cron job. Once again, we
cannot use LetsEncrypt while Profiler is running, so we'll need to stop it
temporarily while we renew. Create a file called ``/opt/renew-letsencrypt.sh``
and paste in the following script.

.. note::

    This script assumes that ``hostname -f`` returns the same fully qualified
    domain name that is the primary name on the certificate. If this is not the
    case, you should supply the domain name via the ``$LETSENCRYPT_HOSTNAME``
    environment variable.

.. code:: bash

    #!/bin/bash

    hostname=${LETSENCRYPT_HOSTNAME:-$(hostname -f)}
    cert_path=/etc/letsencrypt/live/$hostname/cert.pem
    cert_mod_time=$(stat -c %Y $cert_path)
    # max_age is 80 days converted to seconds
    max_age=6912000
    cert_exp_time=$((cert_mod_time + max_age))
    now=$(date +%s)

    if (( $now > $cert_exp_time )); then
      echo "Certificate is 80 days or older."
      echo "Stopping Profiler application container..."
      docker stop profiler_app

      echo "Renewing TLS certificate..."
      /opt/letsencrypt/certbot-auto renew

      echo "Restarting Profiler application container..."
      docker start profiler_app
    else
      echo "Certificate is less than 80 days old... will not renew."
    fi

Now make this script executable.

.. code::

    $ sudo chmod +x /opt/renew-letsencrypt.sh

Finally, add a cron job:

.. code::

    $ sudo su
    $ echo '0 6 * * * root /opt/renew-letsencrypt.sh' > /etc/cron.d/renew-letsencrypt
    $ exit

The schedule ``0 6 * * *`` will run at a 6AM in the server's timezone. You
should choose a time that is unlikely to cause problems for your end users.

Now the TLS certificate should be renewed automatically every 80 days! If
renewal fails (e.g. LetsEncrypt server is offline), then this script will keep
trying to renew on each day until it succeeds.

Developer Installation
======================

Deployment
----------

A separate Docker image is provided for Profiler development: `profiler-dev`.
This image is based on the production image above, but the dev image replaces
the Profiler source code with a volume mount pointing towards your local repo.
Crucially: *we assume that your profiler repo and this docker repo are in the
same directory, i.e. siblings.* If this is not the case, then you'll need to
edit ``docker-compose-dev.yml`` to point towards the actual location of your
source code.

The dev image also provides default database credentials when a container is
instantiated:

- Regular DB account is ``profiler`` / ``profiler``.
- Superuser DB account is ``profiler_su`` / ``profiler_su``.

These credentials will be saved in a ``local.ini`` file which will be placed in
your Profiler repo's ``conf/`` directory. You should review this file so that
you understand what it contains. *If you already have a ``local.ini`` file, then
the container instantiation will try to run migrations instead!*

.. warning::

    The ``profiler-dev`` image is intended to be built locally on your machine
    and *should not be pushed* to any registry. Because this image is only used
    locally, it is fine to tag it without a version number.

To build the development image, you must first perform the production
installation as described above. Now build the development image:

.. code::

    $ cd $DOCKER_REPO/profiler-dev
    $ docker build -t profiler-dev app

You only need to build the development image when the underlying production
image changes.

Now to run the development environment:

.. code::

    $ cd $DOCKER_REPO/profiler-dev
    $ docker-compose up

In development, it's usually better to run ``docker-compose`` without the ``-d``
flag so that it stays in the foreground. This is easier to troubleshoot.

Immutability
------------

Docker containers are *immutable* by default, which can lead to some surprises
if you're treating a Docker container like a VM. Most importantly, every time
you stop your container, all of its internal state is lost. The next time you
start it, you'll get a blank slate container.

To preserve important state, Postgres, Redis, and Solr all save their data in
mounted volumes, so this data is preserved across container restarts. The
``/hgprofiler`` directory is also volume mounted, so changes to your source code
are preserved across container restarts (phew).

However, any other changes, such as installing packages with APT, installing
packages with Pub, doing a Dart build (see below) — all of these changes will
*not be preserved across a container restart*.

If you have modified a container and temporarily wish to save state, you might
use the Docker `commit
<https://docs.docker.com/engine/reference/commandline/commit/>`__ command.
However, for permanent changes to a container's configuration, the correct
procedure is to modify Profiler's ``Dockerfile`` or ``docker-compose.yml`` and
build a new Docker image.

Dev Server
----------

By default, the dev image runs an Apache server on ports 80 and 443, but for
development you'll want to use the `Flask microframework's
<http://flask.pocoo.org/>`_ built-in development server.

The dev server requires that you have symlinked Dart packages into your
``static/dart/lib``. Pub will do this for you:

.. code::

    $ docker exec -it profiler_app pub get

This will place the symlinks into your mounted volume. When viewed from the host
machine, the symlinks will look broken because they point to paths inside the
container like ``/pub-cache/hosted/pub.dartlang.org/foo``. The symlinks will
work fine when viewed from inside the container. You'll need to re-execute ``pub
get`` whenever you modify or update the Dart dependencies.

Now you should be ready to run the dev server:

.. code::

    $ docker exec -it profiler_app su profiler -c "python3 /hgprofiler/bin/run-server.py --ip 0.0.0.0 --debug"
     * Running on http://0.0.0.0:5000/ (Press CTRL+C to quit)
     * Restarting with inotify reloader
     * Debugger is active!
     * Debugger pin code: 184-387-657

.. warning::

    The Flask dev server allows arbitrary code execution, which makes it
    extremely dangerous to run the dev server on a public IP address!

Most of the time, you will want to enable the dev server's debug mode with
``--debug``. This mode has the following features:

- Automatically reloads when your Python source code changes. (It is oblivious
  to changes in configuration files, Dart source, Less source, etc.)
- Disables HTTP caching of static assets.
- Disables logging to /var/log/hgprofiler.log. Log messages are still displayed
  on the console.
- Uses Dart source instead of the Dart build product. (More on this later.)

You'll use the dev server in debug mode for 99% of your development.

Dartium
-------

If you are running the dev server in debug mode, then it will run the
application from Dart source code. This means you need a browser that has a Dart
VM! This browser is called *Dartium* and it's basically the same as Chromium
except with Dart support. It has the same basic features, web kit inspector,
etc.

*You should use Dartium while you develop.* Download Dartium from the `Dart
downloads page <https://www.dartlang.org/tools/download.html>`_. Make sure to
download Dartium by itself, not the whole SDK. (You already installed the SDK if
you followed the instructions above.)

You can unzip the Dartium archive anywhere you want. I chose to put it in
``/opt/dartium``. In order to run Dartium, you can either run it in place, e.g.
``/opt/dartium/chrome`` or for convenience, you might want to add a symlink:

.. code::

    $ ln -s /opt/dartium/chrome /usr/local/bin

Now you can run Dart from any directory by typing ``dartium``.

.. note::

    At this point, you should be able to run the Profiler dev server in debug
    mode and use Dartium to access it.

Dart Build
----------

If you run the dev server without ``--debug``, it will use the Dart build
product instead of the source code. Therefore, you need to run a Dart build if
you are going to run a server without debug mode. The Dart build process is
performed automatically when deploying a production image, but in the
development deployment, you'll need to do a manual build any time you modify
some Dart source and want to test in a real browser (like Chrome).

.. code::

    $ docker exec -it profiler_app /bin/bash
    $ cd /hgprofiler/static/dart
    $ pub get
    $ fixpub
    $ pub build

Now you can run your dev server in non-debug mode and use Profiler with a
standard web brower. If you encounter any errors in this mode, you'll find that
they are nearly impossible to debug because of the conversion from Dart to
JavaScript and the subsequent tree shaking and minification. Add
``--mode=debug`` to your ``pub build`` command to generate more readable
JavaScript errors.

Apache Server
-------------

At some point, you'll want to test against real Apache, not just the dev server.
Apache is already running inside your development deployment and it has a self-
signed certificate so that you can test it on port 443 (although you should
expect to get certificate verification errors).

.. warning::

    Profiler doesn't use ``http/80`` (except to redirect to port 443) and it
    uses `HSTS <http://en.wikipedia.org/wiki/HTTP_Strict_Transport_Security>`_
    to encourage user agents to only make requests over ``https/443``.

Unlike the Flask dev server, Apache does not automatically reload when the
Python source is modified. You can tell the server to reload by touching the
``/hgprofiler/application.wsgi`` file or by sending a hangup signal to
``supervisord``, e.g. ``kilall -HUP supervisord``.

Workers
-------

In the production deployment, a number of background workers are automatically
spawned for you. These workers receive jobs from the job queue and their status
can be viewed on the "Background Tasks" page inside the Profiler application.
You can also see the list of production workers in ``install/supervisor.conf``.

In the development deployment, these workers are not started automatically,
because it would probably be annoying to have all of them running (some of them
will try to download crawl results, for example) while you're trying to write
and test a small bit of new code. You can easily run them manually, though. For
example, if you want to test indexing you can spawn an index worker like this:

.. code::

    $ docker exec -it profiler_app python3 /hgprofiler/bin/run-worker.py archive

You can spawn another worker by repeating the command above but changing the
worker name from ``archive`` to something else (like ``worker``), or you can run
a single process that listens to multiple work queues:

.. code::

    $ docker exec -it profiler_app python3 /hgprofiler/bin/run-worker.py archive scrape

When a single worker listens to multiple queues, it is still limited to running
a single process and processes messages serially. If you want to process
messages in parallel, then you need to spawn multiple workers.

Aliases
-------

To simplify some of the long, difficult-to-remember Docker commands, I add some
aliases to my ``~/.bash_aliases`` file:

.. code:: bash

    alias prflask="docker exec -it profiler_app su hgprofiler -c 'python3 /hgprofiler/bin/run-server.py --ip 0.0.0.0 --debug'"
    alias prshell="docker exec -it profiler_app /bin/bash"
    alias prpython="docker exec -it profiler_app su hgprofiler -c 'PYTHONPATH=/hgprofiler/lib python3'"
    alias prpsql="docker exec -it profiler_postgres su postgres -c 'psql hgprofiler'"

    function prworker() {
      docker exec -it profiler_app su hgprofiler -c "python3 /hgprofiler/bin/run-worker.py $*"
    }
