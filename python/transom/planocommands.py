#
# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
#

from plano import *
from transom import TransomCommand

class _Site:
    def __init__(self):
        self.config_dir = "config"
        self.input_dir = "input"
        self.output_dir = "output"

site = _Site()

_force_arg = CommandArgument("force", help="Render all input files, including unmodified ones")
_verbose_arg = CommandArgument("verbose", help="Print detailed logging to the console")

@command(args=(_force_arg, _verbose_arg))
def render(force=False, verbose=False):
    """
    Render site output
    """

    with project_env():
        args = ["render", site.config_dir, site.input_dir, site.output_dir]

        if force:
            args.append("--force")

        if verbose:
            args.append("--verbose")

        TransomCommand().main(args)

# https://stackoverflow.com/questions/22475849/node-js-what-is-enospc-error-and-how-to-solve
# $ echo fs.inotify.max_user_watches=524288 | sudo tee -a /etc/sysctl.conf && sudo sysctl -p
@command(args=(CommandArgument("port", help="Serve on PORT"), _force_arg, _verbose_arg))
def serve(port=8080, force=False, verbose=False):
    """
    Serve the site and rerender when input files change
    """

    with project_env():
        args = ["serve", "--port", str(port), site.config_dir, site.input_dir, site.output_dir]

        if force:
            args.append("--force")

        if verbose:
            args.append("--verbose")

        TransomCommand().main(args)

@command(args=(_verbose_arg,))
def check_links(verbose=False):
    """
    Check for broken links
    """

    render()

    args = ["check-links", site.config_dir, site.input_dir, site.output_dir]

    if verbose:
        args.append("--verbose")

    with project_env():
        TransomCommand().main(args)

@command(args=(_verbose_arg,))
def check_files(verbose=False):
    """
    Check for missing or extra files
    """

    render()

    args = ["check-files", site.config_dir, site.input_dir, site.output_dir]

    if verbose:
        args.append("--verbose")

    with project_env():
        TransomCommand().main(args)

@command
def clean():
    remove(find(".", "__pycache__"))

class project_env(working_env):
    def __init__(self):
        super(project_env, self).__init__(PYTHONPATH="python")
