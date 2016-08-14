# Transom

Transom renders website content from markdown source files.

[User documentation](http://www.ssorj.net/projects/transom.html)

## Installation

    $ cd transom/
    $ make build
    $ make install

The default install location is `$HOME/.local`.  Use the `PREFIX`
argument to change it.

    $ sudo make install PREFIX=/some/path

## Development

To setup paths in your development environment, source the `devel.sh`
script from the project directory.

    $ cd transom/
    $ source devel.sh

The `devel` make target uses the environment established by `devel.sh`
to install and test your checkout.

    $ make devel

## Project layout

    devel.sh              # Sets up your project environment
    Makefile              # Defines the make targets
    bin/                  # Command-line tools
    python/               # Python library code
    scripts/              # Scripts called by Makefile rules
    build/                # The default build location
    install/              # The devel install location

## Make targets

After that most everything is accomplished by running make targets.
These are the important ones:

    $ make build         # Builds the code
    $ make install       # Installs the code
    $ make devel         # Cleans, builds, installs, tests
    $ make clean         # Removes build/ and install/
