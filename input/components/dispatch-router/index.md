;;
;; Licensed to the Apache Software Foundation (ASF) under one
;; or more contributor license agreements.  See the NOTICE file
;; distributed with this work for additional information
;; regarding copyright ownership.  The ASF licenses this file
;; to you under the Apache License, Version 2.0 (the
;; "License"); you may not use this file except in compliance
;; with the License.  You may obtain a copy of the License at
;; 
;;   http://www.apache.org/licenses/LICENSE-2.0
;; 
;; Unless required by applicable law or agreed to in writing,
;; software distributed under the License is distributed on an
;; "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
;; KIND, either express or implied.  See the License for the
;; specific language governing permissions and limitations
;; under the License.
;;

# Dispatch Router

A lightweight message router, written in C and built on
[Qpid Proton](@site-url@/proton/index.html), that provides flexible
and scalable interconnect between AMQP endpoints or between endpoints
and brokers.

  || *Platforms* || Linux ||
  || *AMQP versions* || 1.0 ||
  || *Download* || [qpid-dispatch-@current-dispatch-release@.tar.gz](http://www.apache.org/dyn/closer.cgi/qpid/dispatch/@current-dispatch-release@/qpid-dispatch-@current-dispatch-release@.tar.gz) \[[ASC](http://www.apache.org/dist/qpid/dispatch/@current-dispatch-release@/qpid-dispatch-@current-dispatch-release@.tar.gz.asc), [SHA1](http://www.apache.org/dist/qpid/dispatch/@current-dispatch-release@/SHA1SUM)] ||
  || *Source location* ||  <http://svn.apache.org/repos/asf/qpid/dispatch/trunk/> ||
  
## Overview

The Dispatch router is an AMQP router that provides advanced interconnect for AMQP.
It is *not* a broker.  It will never assume ownership of a message.  It will,
however, propagate settlement and disposition across a network such that delivery
guarantees are met.

The router is meant to be deployed in topologies of multiple routers, preferably with
redundant paths.  It uses link-state routing protocols and algorithms (similar to OSPF
or IS-IS from the networking world) to calculate the best path from every point to
every other point and to recover quickly from failures.  It does not need to use
clustering for high availability; rather, it relies on redundant paths to provide
continued connectivity in the face of system or network failure.

A messaging client can make a single AMQP connection into a messaging bus built of
Dispatch routers and, over that connection, exchange messages with one or more message
brokers, and at the same time exchange messages directly with other endpoints without
involving a broker at all.

## Benefits

 - Simplifies connectivity
   - An endpoint can do all of its messaging through a single transport connection
   - Avoid opening holes in firewalls for incoming connections
 - Simplifies reliability
   - Reliability and availability are provided using redundant topology, not server clustering
   - Reliable end-to-end messaging without persistent stores
   - Use a message broker only when you need store-and-forward semantics

## Features

<div class="two-column" markdown="1">

 - Supports arbitrary topology - no restrictions on redundancy
 - Automatic route computation - adjusts quickly to changes in topology
 - Configurable addressing semantics

</div>

## Documentation

- [Current release](@current-dispatch-release-url@/index.html)
- [Past releases](@site-url@/releases/index.html#past-releases) 
- [Work in progress](@site-url@/releases/qpid-dispatch-trunk/index.html)

## Issues

For more information about finding and reporting bugs, see
[Qpid issues](@site-url@/issues.html).

<div class="indent">
  <form id="jira-search-form">
    <input type="hidden" name="jql" value="project = QPID and component = 'Qpid Dispatch' and text ~ '{}' order by updatedDate desc"/>
    <input type="text" name="text"/>
    <button type="submit">Search</button>
  </form>
</div>

<div class="two-column" markdown="1">

 - [Open bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+%3D+%22Bug%22+and+project+%3D+%22DISPATCH%22)
 - [Fixed bugs](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+%3D+%22Bug%22+and+project+%3D+%22DISPATCH%22)
 - [Requested enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+EMPTY+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+project+%3D+%22DISPATCH%22)
 - [Completed enhancements](http://issues.apache.org/jira/issues/?jql=resolution+%3D+%22Fixed%22+and+issuetype+in+%28%22New+Feature%22%2C+%22Improvement%22%29+and+project+%3D+%22DISPATCH%22)
 - [Report a bug](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12315321&issuetype=1&summary=[Enter%20a%20brief%20description]&priority=3)
 - [Request an enhancement](https://issues.apache.org/jira/secure/CreateIssueDetails!init.jspa?pid=12315321&issuetype=4&summary=[Enter%20a%20brief%20description]&priority=3)
 - [Jira summary page](http://issues.apache.org/jira/browse/DISPATCH)

</div>
