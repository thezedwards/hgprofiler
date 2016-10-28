.. _configuration:

*******************
Configuration Guide
*******************

.. contents::
    :depth: 3

Change Password & Create Users
==============================

After you have finished the :ref:`installation`, log in with the default
administrator username ``admin`` and default password ``MemexPass1``. After
logging in, you'll see a menu in the top right corner that shows your username:
"admin". Under that menu, click "My Profile" and then change the password to
something strong and random. You may also wish to change the administrator's
e-mail address. Other users will be able to see this address and may try sending
mail to it if they need technical support.

Under the same menu, click "User Directory". You can add additional user
accounts on this screen. Set up a new account for yourself and any other users,
making sure to use strong, random passwords for each one. (Other users can
change their own password after they log in for the first time.) When creating
an account for yourself, be sure to select the 'Administrator' role.

.. important::

    When logged in as an administrator, you will find administrator-only options
    under the user menu. Regular users do not see these options.

The admin account should be used only for emergencies and should not be used for
day-to- day work, so log out from the admin account and log back in with the new
account that you just created for yourself.

Configuration
=============

While logged in as an administrator, go to the user menu and select
"Configuration". This page allows you to set important configuration options for
the application.

scrape_request_timeout
    The number of seconds to wait before a request to scrape a profile times
    out.

splash_url
    The URL of the splash instance of splash cluster that should be used for
    scraping profiles.
