// Licensed to the Apache Software Foundation (ASF) under one
// or more contributor license agreements.  See the NOTICE file
// distributed with this work for additional information
// regarding copyright ownership.  The ASF licenses this file
// to you under the Apache License, Version 2.0 (the
// "License"); you may not use this file except in compliance
// with the License.  You may obtain a copy of the License at
//
//   http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing,
// software distributed under the License is distributed on an
// "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
// KIND, either express or implied.  See the License for the
// specific language governing permissions and limitations
// under the License.

const $ = document.querySelector.bind(document);
const $$ = document.querySelectorAll.bind(document);

Element.prototype.$ = function () {
    return this.querySelector.apply(this, arguments);
};

Element.prototype.$$ = function () {
    return this.querySelectorAll.apply(this, arguments);
};

window.addEventListener("load", () => {
    const tocNav = $("nav.transom-page-toc");

    if (!tocNav || !tocNav.$("a")) {
        return;
    }

    const updateHeadingSelection = () => {
        const currHash = window.location.hash;

        for (const elem of tocNav.$$(".selected")) {
            elem.classList.remove("selected");
        }

        if (currHash) {
            for (const link of tocNav.$$("a")) {
                const linkHash = new URL(link.href).hash;

                if (linkHash === currHash) {
                    link.classList.add("selected");
                    break;
                }
            }

            $(currHash).parentElement.parentElement.classList.add("selected");
        } else {
            // Select the top heading by default
            tocNav.$("a").classList.add("selected");
        }
    }

    updateHeadingSelection();

    window.addEventListener("hashchange", updateHeadingSelection);
});
