Module layout
=============

This module, ``calmjs.webpack``, also follows the ``calmjs`` module
layout order, but for clarity sake the modules defined here are included
in the descriptions.

interrogation
    Helpers for interrogating a webpack artifact file.

walkers
    Helper walkers for dealing with ECMAScript parse trees from
    ``calmjs.parse``.

base
    Base classes and identifiers.

exc
    Generic exception classes specific for this project.

utils
    Utilities for use here, and also for packages depending on this one.

env
    Environmental setting utilities

loaderplugin
    Integration with the loader plugin system; include the base loader
    plugins and an automatic registry system.

registry
    Currently contain just one registry implementation, which is for
    tracking the loader plugins that are supported.

dev
    Integration with the ``calmjs.dev`` package, for specifying the
    interoperation rules between ``webpack`` with ``karma`` for the
    Calmjs framework.

dist
    Module that interfaces with ``distutils``/``setuptools`` helpers
    provided by ``calmjs``, for assisting with gathering sources for
    bundling, and also helpers for the generation of configuration files
    to be fed into ``webpack``.

toolchain
    Provide the transpilation/artifact generation toolchain that
    integrates with ``webpack``, plus ``Spec`` keys support by this
    package through the ``WebpackToolchain`` class.

cli
    Slightly higher level API on top of ``WebpackToolchain``.

runtime
    Higher level API that also provide the user facing utility that
    provide interface to generate artifacts from the command line.

As a general rule, a module should not inherit from modules listed below
their respective position on the above list.
