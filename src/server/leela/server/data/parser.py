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

import re
import json
import time
from leela.server import config
from leela.server.data import event
from leela.server.data import data
from leela.server.data import metric

def parse_json(x):
    return(json.loads(x))

def parse_string(s, w):
    if (s.startswith(w)):
        return(s[len(w):])
    raise(ValueError("string should start with: %s" % w))

def parse_istring(s, w):
    if (s.lower().startswith(w.lower())):
        return(s[len(w):])
    raise(ValueError("string should start with: %s" % w))

def parse_take(s, n):
    return(s[:n], s[n:])

def parse_takewhile(s, p):
    tmp = []
    for c in s:
        if (p(c)):
            tmp.append(c)
        else:
            break
    return(("".join(tmp), s[len(tmp):]))

def parse_double(s):
    if (s.startswith("nan") or s.startswith("NaN")):
        return(float("nan"), s[3:])
    elif (s.startswith("inf")):
        return(float("inf"), s[3:])
    elif (s.startswith("Infinity")):
        return(float("inf"), s[8:])
    elif (s.startswith("-inf")):
        return(float("-inf"), s[4:])
    elif (s.startswith("-Infinity")):
        return(float("-inf"), s[9:])
    else:
        (d, s) = parse_takewhile(s, lambda c: c in "0123456789.e-+")
        return(float(d), s)

def parse_int(s):
    tmp = []
    for c in s:
        if (not c.isdigit()):
            break
        tmp.append(c)
    if (len(tmp) == 0):
        raise(ValueError("number was expected"))
    return(int("".join(tmp), 10), s[len(tmp):])

def parse_event(s):
    s      = parse_string(s, "event ")
    (l, s) = parse_int(s)
    s      = parse_string(s, "|")
    (n, s) = parse_take(s, l)
    s      = parse_string(s, " ")
    (v, s) = parse_double(s)
    s      = parse_string(s, " ")
    (t, s) = parse_double(s)
    if (s[0] == ";"):
        return(event.Event(n, v, t), s[1:])
    else:
        raise(ValueError("; was expected"))

def parse_data(s):
    s      = parse_string(s, "data ")
    (l, s) = parse_int(s)
    s      = parse_string(s, "|")
    (n, s) = parse_take(s, l)
    s      = parse_string(s, " ")
    (l, s) = parse_int(s)
    s      = parse_string(s, "|")
    (v, s) = parse_take(s, l)
    s      = parse_string(s, " ")
    (t, s) = parse_double(s)
    if (s[0] == ";"):
        return(data.Data(n, parse_json(v), t), s[1:])
    else:
        raise(ValueError("; was expected"))

def parse_status(s):
    s      = parse_string(s, "status ")
    (l, s) = parse_int(s)
    if (s[0] == ";"):
        return(l, s[1:])
    else:
        raise(ValueError("syntax error"))

def parse_event_legacy(s):
    (name, value) = s.split(": ", 2)
    if (" " in value):
        (lval, tval) = value.split(" ", 2)
        tval = long(tval, 10)
    else:
        lval = value
        tval = long(time.time())
    return(event.Event(name[:255], float(lval), tval))

def parse_select(s):
    m = re.match(r"^SELECT (.+?) FROM (.+?);$", s.strip(), re.I)
    r = {}
    if (m):
        return({ "select": { "proc": m.group(1).strip(),
                             "regex": m.group(2).strip()
                           }
               })
    raise(ValueError("syntax error"))

def parse_delete(s):
    m = re.match(r"^DELETE FROM leela.xmpp(?: WHERE key=(.+?))?;$", s.strip(), re.I)
    r = {}
    if (m):
        tmp = (m.group(1) or "").strip()
        return({ "delete": {"key": tmp}
               })
    raise(ValueError("syntax error"))

def parse_sql(s):
    if (s[0] in "dD"):
        return(parse_delete(s))
    elif (s[0] in "sS"):
        return(parse_select(s))
    raise(ValueError("syntax error"))

def parse_sql_(s):
    try:
        return(parse_sql(s))
    except:
        return({})

def parse_event_(s):
    try:
        return(parse_event(s))
    except:
        return(None, "")

def parse_data_(s):
    try:
        return(parse_data(s))
    except:
        return(None, "")

def parse_timespec(s):
    """
    %Y%m%dT%H%M
    """
    y = int(s[:4], 10)
    m = int(s[4:6], 10)
    d = int(s[6:8], 10)
    h = int(s[9:11], 10)
    M = int(s[11:], 10)
    if (m<1 or m>12 or d<1 or d>31 or h<0 or h>23 or M<0 or M>59):
        raise(ValueError("parse_timespec: syntax error"))
    return((y, m, d, h, M))

def parse_status_(s):
    try:
        return(parse_status(s))
    except:
        return(-1, "")

def parse_json_data1(result, name):
    if (not isinstance(result, dict)):
        raise(ValueError("json must be an object"))
    n = result.get("name", name)
    t = float(result.get("timestamp", time.time()))
    if (len(json.dumps(result["value"])) > config.MAXPACKET):
        raise(ValueError("size is too big [maximum: %d]" % (config.MAXPACKET,)))
    if (n != name):
        raise(ValueError("different names given [%s /= %s]" % (n, name)))
    return(data.Data(n, result["value"], t))

def parse_json_data(s, name=None):
    results = parse_json(s)
    if (isinstance(results, list)):
        return(map(lambda r: parse_json_data1(r, name), results))
    else:
        return([parse_json_data1(results, name)])

def parse_json_metric1(result, name):
    if (not isinstance(result, dict)):
        raise(ValueError("json must be an object"))
    n = result.get("name", name)
    v = float(result["value"])
    m = result["type"]
    t = float(result.get("timestamp", time.time()))
    if (n != name):
        raise(ValueError("different names given [%s /= %s]" % (n, name)))
    if (m == "gauge"):
        return(metric.Gauge(n, v, t))
    elif (m == "absolute"):
        return(metric.Absolute(n, v, t))
    elif (m == "derive"):
        return(metric.Derive(n, v, t))
    elif (m == "counter"):
        return(metric.Counter(n, v, t))
    else:
        raise(ValueError("unkown metric type: %s" % repr(m,)))

def parse_json_metric(s, name=None):
    results = parse_json(s)
    if (isinstance(results, list)):
        return(map(lambda r: parse_json_metric1(r, name), results))
    else:
        return([parse_json_metric1(results, name)])

