#!/usr/bin/env python
# -*- coding: utf-8 -*- vim:fileencoding=utf-8:
# vim: tabstop=4:shiftwidth=4:softtabstop=4:expandtab

import os, pwd, grp
import daemon, lockfile
import logging, logging.handlers
import ConfigParser
from transmissionrpc import Client, TransmissionError
import feedparser
from datetime import datetime, tzinfo
import time
import re
from urllib2 import URLError

CONF_FILE = 'transmission_mgtd.conf'
LOCK_FILE = '/run/lock/transmission_mgtd.pid'
STDERR_FILE = '/tmp/transmission_mgtd.stderr'

def find_torrents_to_delete(torrents, logger, max_days, series_max_days):

    now=datetime.now()
    todelete = []
    for t in torrents.keys():
        diff = now - torrents[t].date_added
        if re.search('S\d\dE\d\d',torrents[t].fields['name']) and diff.days > series_max_days:
            logger.info('Will remove: %s' % (torrents[t].fields['name']))
            todelete.append(torrents[t].fields['id'])
        if diff.days > max_days:
            logger.info('Will remove: %s' % (torrents[t].fields['name']))
            todelete.append(torrents[t].fields['id'])
    return todelete

def find_torrents_to_add(feeds, torrentnames, logger):
    now=datetime.utcnow()
    toadd = []
    for feed in feeds:
        f = feedparser.parse(feed[1])
        logger.debug('Successfully parsed feed with name: %s' % feed[0])
        for entry in f.entries:
            # entry.updated contains TZ. entry.updated_parsed returns a struct_time
            # that represents the time in UTC taking into account timezone info
            # time.mktime returns the number of seconds since Epoch
            # datetime.fromtimestamp() and now() both don't use explicitly here TZ info
            # so they are expressed in local TZ. So we should have no problems with
            # DST, timezone differences and the rest
            delta = now - datetime.fromtimestamp(time.mktime(entry.updated_parsed))
            if delta.days ==0 and delta.seconds < 7200 and unicode(entry.title) not in torrentnames:
                logger.info('Will add: %s with release date: %s' % (
                                        entry.title, entry.updated))
                toadd.append(entry.link)
    return toadd

def run(config, logger):
    logger.debug('Daemonized successfully')
    c = Client(address=config['address'],user=config['username'],password=config['password'])
    logger.debug('Connected to transmission successfully')
    while True:
        logger.debug('Starting run')
        torrents=c.info()
        torrentnames = map(lambda x: x.fields['name'], torrents.values())

        todelete = find_torrents_to_delete(torrents, logger, config['max_days'], config['series_max_days'])
        toadd = find_torrents_to_add(config['feeds'], torrentnames, logger)
        if config['dry_run'] == False:
            # Let's delete all old torrents
            if len(todelete) >0:
                c.remove(todelete, delete_data=True, timeout=config['timeout'])
            if len(toadd) > 0:
                for a in toadd:
                    try:
                        c.add_uri(a)
                    except (TransmissionError, URLError) as e:
                        if isinstance(e, TransmissionError):
                            e.message = e._message
                        if isinstance(e, URLError):
                            e.message = e.reason
                        if e.message == 'Query failed with result "duplicate torrent".':
                            logger.info('Torrent: %s already downloading' % (a))
                        else:
                            logger.warning('Failed to add: %s. Reason: %s' % (a, e.message))

        logger.debug('Ending run')
        time.sleep(config['interval'])

def initialize():
    configfile = ConfigParser.ConfigParser()
    configfile.read(CONF_FILE)

    config = {}
    config['address'] = configfile.get('transmission', 'address')
    config['username'] = configfile.get('transmission', 'username')
    config['password'] = configfile.get('transmission', 'password')
    config['timeout'] = int(configfile.get('transmission', 'timeout'))
    config['max_days'] = int(configfile.get('torrents', 'max_days'))
    config['series_max_days'] = int(configfile.get('torrents', 'series_max_days'))
    config['dry_run'] = (configfile.get('main', 'dry_run') == 'True')
    config['log_file'] = configfile.get('main', 'log_file')
    config['log_level'] = getattr(logging, configfile.get('main', 'log_level').upper())
    config['uid'] = configfile.get('main', 'uid')
    config['gid'] = configfile.get('main', 'gid')
    config['interval'] = int(configfile.get('main', 'interval'))
    config['feeds'] = configfile.items('feeds')

    logger = logging.getLogger('transmission_mgtd')
    logger.setLevel(config['log_level'])

    filelog = logging.handlers.TimedRotatingFileHandler(config['log_file'],
                                 when='W0',
                                 interval=4,
                                 backupCount=40)
    filelog.setFormatter(logging.Formatter('%(asctime)s:%(levelname)s:%(message)s'))
    logger.addHandler(filelog)
    logger.debug('Initialized successfully')
    running_uid = pwd.getpwnam(config['uid']).pw_uid
    running_gid = grp.getgrnam(config['gid']).gr_gid
    os.setuid(running_uid)
    os.setgid(running_gid)
    logger.debug('Dropped privileges successfully')
    return (config, logger)

def main():
    config, logger = initialize()
    context = daemon.DaemonContext(
            pidfile=lockfile.FileLock(LOCK_FILE),
            stderr=open(STDERR_FILE, 'w+'),
            detach_process=False,
            )
    f = logger.handlers[0].stream
    context.files_preserve = [f,]
    with context:
        run(config, logger)

if __name__ == '__main__':
    main()
