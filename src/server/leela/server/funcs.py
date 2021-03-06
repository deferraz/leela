# -*- coding: utf-8; -*-
#
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

import time
import calendar
from datetime import datetime
from leela.server import logger
from leela.server import tzutil

def suppress(f):
    def g(*args, **kwargs):
        try:
            f(*args, **kwargs)
        except:
            pass
    g.__name__ = f.__name__
    return(g)

def suppress_e(p, default):
    def suppress_f(f):
        def g(*args, **kwargs):
            try:
                return(f(*args, **kwargs))
            except Exception as e:
                if (p(e)):
                    return(default)
                else:
                    raise
        g.__name__ = f.__name__
        return(g)
    return(suppress_f)

def logerrors(logger):
    def proxy_f(f):
        def g(*args, **kwargs):
            try:
                f(*args, **kwargs)
            except:
                logger.exception()
        g.__name__ = f.__name__
        return(g)
    return(proxy_f)

def retry_on_fail(f, retries=3, wait=0.3):
    def g(*args, **kwargs):
        attempt = 0
        while (True):
            try:
                return(f(*args, **kwargs))
            except:
                if (attempt > retries):
                    raise
                attempt += 1
                time.sleep(wait)
    g.__name__ = f.__name__
    return(g)

def dict_set(d, k, v):
    d[k] = v
    return(d)

def dict_update(f, d, k, v):
    if (k in d):
        d[k] = f(d[k], v)
    else:
        d[k] = v
    return(d)

def dict_merge(o, n):
    tmp = {}
    tmp.update(o)
    tmp.update(n)
    return(tmp)

def datetime_date(date):
    y = str(date.year)
    m = str(date.month).zfill(2)
    d = str(date.day).zfill(2)
    return(y + m + d)

def datetime_time(date):
    h = str(date.hour).zfill(2)
    m = str(date.minute).zfill(2)
    return(h + m)

def timetuple_timestamp(ttuple):
    return(calendar.timegm(ttuple))

def datetime_timestamp(date):
    return(timetuple_timestamp(date.timetuple()))

def datetime_fromtimestamp(timestamp):
    return(datetime.fromtimestamp(timestamp, tzutil.UTC()))

def time_to_slot(hour, minute):
    if (hour > 23 or hour < 0):
        raise(RuntimeError("invalid range (0 ≤ hour < 24)"))
    if (minute > 59 or minute < 0):
        raise(RuntimeError("invalid range (0 ≤ minute < 60)"))
    return(hour * 60 + minute)

def slot_to_time(slot):
    if (slot < 0 or slot > 1439):
        raise(RuntimeError("invalid range (0 ≤ slot < 1439)"))
    return(divmod(slot, 60))

def slot_to_timestamp(year, month, day, slot):
    (hour, minute) = slot_to_time(slot)
    return(datetime_timestamp(datetime(year, month, day, hour, minute)))

def timer_start():
    return(time.time())

def timer_stop(t):
    return(time.time() - t)

def norm_key(k):
    return(k.lower())
