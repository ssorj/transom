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

# AMQP

The Advanced Message Queueing Protocol is at the heart of everything
we do at Qpid. It is an open standard designed to support reliable,
high-performance messaging over the internet. AMQP can be used for any
distributed application and supports common messaging patterns such as
point-to-point, fan-out, publish-subscribe, and request-response.

## AMQP 1.0

The AMQP working group released the 1.0 specification in the final
quarter of 2011. Future evolution of the protocol is now driven by the
member section and technical committees at OASIS.

Qpid offers AMQP 1.0 support in the following components:

<div class="two-column" markdown="1">
 - [AMQP Messenger](@site-url@/components/messenger/index.html)
 - [AMQP Protocol Engine](@site-url@/components/protocol-engine/index.html)
 - [C++ broker](@site-url@/components/cpp-broker/index.html)
 - [Java broker](@site-url@/components/java-broker/index.html)
 - [Qpid JMS](@site-url@/components/qpid-jms/index.html)
 - [Qpid Messaging API](@site-url@/components/messaging-api/index.html)
</div>

## AMQP and your app

We offer a library, [Qpid Proton](proton/index.html), whose explicit
aim is to help you make your application speak AMQP.

## More information

 - [AMQP website](http://www.amqp.org/)
 - [AMQP 1.0 specification](http://docs.oasis-open.org/amqp/core/v1.0/os/amqp-core-overview-v1.0-os.html)
 - [OASIS AMQP technical committee](https://www.oasis-open.org/committees/tc_home.php?wg_abbrev=amqp)
 - [AMQP on Wikipedia](http://en.wikipedia.org/wiki/Advanced_Message_Queuing_Protocol)
