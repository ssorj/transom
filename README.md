# Transom

Transom renders website contetn from markdown source files.

[User documentation](http://www.ssorj.net/projects/transom.html)

## Installation

    $ cd transom/
    transom$ make build
    transom$ sudo make install

The default install location is `/usr/local`.  Use the `PREFIX`
argument to change it.

    transom$ sudo make install PREFIX=/some/path

## Development

To setup paths in your development environment, source the `devel.sh`
script from the project directory.

    $ cd transom/
    transom$ source devel.sh

The `devel` make target uses the environment established by `devel.sh`
to install and test your checkout.

    transom$ make devel

## Project layout

    devel.sh              # Sets up your project environment
    Makefile              # Defines the make targets
    bin/                  # Command-line tools
    python/               # Python library code; used by scripts
    scripts/              # Scripts called by Makefile rules
    build/                # The default build location
    install/              # The devel install location

## Make targets

After that most everything is accomplished by running make targets.
These are the important ones:

    transom$ make build   # Builds the code
    transom$ make install # Installs the code
    transom$ make devel   # Cleans, builds, installs, tests
    transom$ make clean   # Removes build/ and install/
