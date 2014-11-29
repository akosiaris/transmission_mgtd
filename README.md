# Introduction #

A python daemon for managing transmission daemon. It is capable of:

* cleaning up old torrents
* Parsing remote RSS sources and adding torrents
* Logging to syslog or a time based log rotated file
* setuid/setgid support

# How to install #
I assume a Debian system here, amend accordingly for your system

If you have not already installed transmision, install it:

    apt-get install transmission-daemon

The above installs the daemon cause a headless box is assumed. It should
probably work with a non headless box as well and a normal transmission
installation but this has not been tested.

Install the python transmission bindings

    apt-get install python-transmissionrpc

## Use the python package ##

    pip install transmission_mgtd

## Do it manually ##
Clone the repo, copy the module directory somewhere in your fileystem

# Configure #

The daemon searches for a configuration file under the current dir named
transmission\_mgtd.conf. A sample exists in etc directory and
should be bundled with the installation. Here an explanation of the
settings:

    [server]
    # The URI of the transmission daemon. Unless you have changed it
    # /transmission/rpc is a must at the end
    address=http://localhost:9091/transmission/rpc
    # Self-explanatory
    username=myuser
    password=mypass
    # How long the HTTP connection to the transmission daemon will stay
    # open. Should it have to delete some very big torrents or has
    # terrible I/O performance, this might be handy
    timeout=300

    [torrents]
    # How long before torrents get auto-deleted
    max_days=30
    # How long before TV Series torrents get autodeleted. They are
    # detected via the regexp: S\d\dE\d\d
    # This matches SXYEZW where N,M,ZW numbers
    series_max_days=10

    [main]
    # Will not delete of add anything, just pretend it does
    dry_run=False
    # For now only log files are supported. They are autorotated on a
    # weekly basis. syslog support will be added later on though
    log_file=/var/log/transmission_mgtd.log
    log_level=info
    # The daemon will wake up every X seconds
    interval=300
    # Run as the user/group
    uid=transmission-mgtd
    gid=transmission-mgtd

    [feeds]
    # RSS/Atom Feeds to get and parse and add torrents from
    feed1=http://example.org/rss?feed=1
    feed2=http://example.org/rss?feed=2&param=3

# Start #

No init script exists for now. Just run the init manually. systemd and
initscripts to be added

# Compatibility #

Developed and tested on Debian Wheezy system. Feel free to submit PRs for other systems support

# Disclaimer #
This is still alpha stage and has a great number of issues
