#!/usr/bin/python
# -*- coding: utf-8; -*-
#
# Copyright 2012 Juliano Martinez
# Copyright 2012 Diego Souza
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#

import re
import sys
import time
import pycassa
from datetime import datetime
from leela import config
from leela import funcs
from leela import logger
from leela import storage

def read_hostsrv_tuple(line):
    """
    line format: hostname|service||field|value||field|value
    """
    hostname, service = line.split('||')[0].split('|')
    hostname = hostname.replace('-', '_')
    return(funcs.norm_hostname(hostname), funcs.norm_service(service))

def read_data_points(line):
    """
    line format: hostname|service||field|value||field|value
    """
    to_data = lambda (x,y): (funcs.norm_field(x), float(y))
    return(map(lambda x: to_data(x.split("|")), line.split("||")[1:]))

class Lasergun(object):

    def __init__(self, config, cassandra, carbon):
        self.config    = config
        self.cassandra = cassandra
        self.carbon    = carbon

    def retrieve(self, hostname, service, timestamp):
        date = datetime.fromtimestamp(timestamp)
        row  = "%s:%s:%s" % (funcs.norm_hostname(hostname), funcs.norm_service(service), funcs.datetime_date(date))
        with self.cassandra.day_scf() as cf:
            return(funcs.service_map_slot(lambda s: int(s), cf.get(row, column_count=1440)))

    def send2carbon(self, line, timestamp):
        message = ""
        (hostname, service) = read_hostsrv_tuple(line)
        for (name, value) in read_data_points(line):
            message += "%s.%s.%s %s %d\n" % (hostname, service, name, value, int(timestamp))
        timer0 = funcs.timer_start()
        self.carbon.write(message)
        logger.debug("finishing writing data carbon: (time=%.6f)" % (funcs.timer_stop(timer0)))

    def store(self, line, timestamp):
        (hostname, service) = read_hostsrv_tuple(line)
        logger.debug("processing event: %s,%s" % (hostname, service))
        date   = datetime.fromtimestamp(timestamp)
        slot   = str(funcs.time_to_slot(date.hour, date.minute))
        t_date = funcs.datetime_date(date)
        row    = "%s:%s" % (hostname, service)
        timer0 = funcs.timer_start()
        with self.cassandra.day_scf() as cf:
            for (name, value) in read_data_points(line):
                krow = "%s:%s" % (row, t_date)
                timer1 = funcs.timer_start()
                cf.insert(krow, {name: {slot: value}}, write_consistency_level=pycassa.ConsistencyLevel.ONE)
                logger.debug("writing data point day_scf[%s:%s:%s] = %.2f (time=%.6f)" % (krow, name, slot, value, funcs.timer_stop(timer1)))
        logger.debug("finishing writing data onto day_scf[%s]: (time=%.6f)" % (row, funcs.timer_stop(timer0)))
