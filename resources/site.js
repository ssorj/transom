/*
 *
 * Licensed to the Apache Software Foundation (ASF) under one
 * or more contributor license agreements.  See the NOTICE file
 * distributed with this work for additional information
 * regarding copyright ownership.  The ASF licenses this file
 * to you under the Apache License, Version 2.0 (the
 * "License"); you may not use this file except in compliance
 * with the License.  You may obtain a copy of the License at
 * 
 *   http://www.apache.org/licenses/LICENSE-2.0
 * 
 * Unless required by applicable law or agreed to in writing,
 * software distributed under the License is distributed on an
 * "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
 * KIND, either express or implied.  See the License for the
 * specific language governing permissions and limitations
 * under the License.
 *
 */

"use strict";

var _loggingEnabled = true;

function _log(message) {
    if (!_loggingEnabled) {
        return;
    }

    console.log(message);
}

function _updatePathNavigation() {
    var elem = document.getElementById("-path-navigation");

    if (!elem) {
        return;
    }

    _log("Updating path navigation");

    var child = elem.firstChild;
    var count = 0;

    while (child) {
        if (child.nodeType === 1) {
            count++;
        }

        child = child.nextSibling;
    }

    if (count >= 2) {
        elem.style.display = "inherit";
    }
}

//_updatePathNavigation();
