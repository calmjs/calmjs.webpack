# -*- coding: utf-8 -*-
"""
Module that links to the calmjs.dist, for use with WebpackToolchain.
"""

# TODO merge this into upstream.

import logging

from os import getcwd
from os.path import join
from os.path import isdir

from calmjs.registry import get
from calmjs.dist import get_extras_calmjs
from calmjs.dist import get_module_registry_dependencies
from calmjs.dist import get_module_registry_names
from calmjs.dist import flatten_extras_calmjs
from calmjs.dist import flatten_module_registry_dependencies
from calmjs.dist import flatten_module_registry_names

logger = logging.getLogger(__name__)
_default = 'all'


def map_none(*a, **kw):
    return {}


def list_none(*a, **kw):
    return []


source_map_methods_list = {
    'all': flatten_module_registry_dependencies,
    'explicit': get_module_registry_dependencies,
    'none': map_none,
}

calmjs_module_registry_methods = {
    'all': flatten_module_registry_names,
    'explicit': get_module_registry_names,
    'none': list_none,
}

extras_calmjs_methods = {
    'all': flatten_extras_calmjs,
    'explicit': get_extras_calmjs,
    'none': map_none,
}


def acquire_method(methods, key, default=_default):
    return methods.get(key, methods.get(default))


def get_calmjs_module_registry_for(package_names, method=_default):
    """
    Acquire the module registries required for the package_names.

    package_names
        The names of the Python package to generate the source maps for.
    method
        The method to acquire the dependencies for the given module
        across all the registries specified.  Choices are between 'all',
        'explicit' or 'none'.  Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the mappings declared for each of those modules.
        'explicit'
            Same as all, however all will be stubbed out using 'empty:'
            to prevent bundling.  Only the declared sources for the
            specified packages will be untouched.
        'none'
            Produce an empty source map.

        All options not on above list defaults to 'all'
    """

    registries = acquire_method(
        calmjs_module_registry_methods, method)(package_names)
    return registries


def generate_transpile_source_maps(
        package_names, registries=('calmjs.modules'), method=_default):
    """
    Invoke the module_registry_dependencies family of dist functions,
    with the specified registries, to produce the required source maps.

    Arguments:

    package_names
        The names of the Python package to generate the source maps for.
    registries
        The names of the registries to source the packages from.  If
        unspecified, pick the options declared by the provided packages.
    method
        The method to acquire the dependencies for the given module
        across all the registries specified.  Choices are between 'all',
        'explicit' or 'none'.  Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the mappings declared for each of those modules.
        'explicit'
            Same as all, however all will be stubbed out using 'empty:'
            to prevent bundling.  Only the declared sources for the
            specified packages will be untouched.
        'none'
            Produce an empty source map.

        Defaults to 'all'.
    """

    source_map_method = acquire_method(source_map_methods_list, method)
    transpile_source_map = {}

    for registry_name in registries:
        transpile_source_map.update(source_map_method(
            package_names, registry_name=registry_name))

    return transpile_source_map


def generate_bundle_source_maps(
        package_names, working_dir=None, method=_default):
    """
    Acquire the bundle source maps through the calmjs registry system.

    Arguments:

    package_names
        The names of the package to acquire the sources for.
    working_dir
        The working directory.  Defaults to current working directory.
    method
        The method to acquire the bundle sources for the given module.
        Choices are between 'all', 'explicit', 'none', or 'empty'.

        'all'
            Traverse the dependency graph for the specified package and
            acquire the declarations. [default]
        'explicit'
            Only acquire the bundle sources declared for the specified
            package.
        'none'
            Produce an empty source map.

        Defaults to 'all'.
    """

    working_dir = working_dir if working_dir else getcwd()
    acquire_extras_calmjs = acquire_method(extras_calmjs_methods, method)

    # the extras keys will be treated as valid Node.js package manager
    # subdirectories.
    valid_pkgmgr_dirs = set(get('calmjs.extras_keys').iter_records())
    extras_calmjs = acquire_extras_calmjs(package_names)
    bundle_source_map = {}

    for mgr in extras_calmjs:
        if mgr not in valid_pkgmgr_dirs:
            continue
        basedir = join(working_dir, mgr)
        if not isdir(basedir):
            if extras_calmjs[mgr]:
                logger.warning(
                    "acquired extras_calmjs needs from '%s', but working "
                    "directory '%s' does not contain it; bundling may fail.",
                    mgr, working_dir
                )
            continue  # pragma: no cover

        for k, v in extras_calmjs[mgr].items():
            bundle_source_map[k] = join(basedir, *(v.split('/')))

    return bundle_source_map
