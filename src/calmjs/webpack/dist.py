# -*- coding: utf-8 -*-
"""
Module that links to the calmjs.dist, for use with WebpackToolchain.
"""

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
from calmjs.dist import flatten_parents_module_registry_dependencies
from calmjs.dist import flatten_module_registry_names

logger = logging.getLogger(__name__)
_default = 'all'


def map_none(*a, **kw):
    return {}


def list_none(*a, **kw):
    return []


source_map_methods_map = {
    'all': flatten_module_registry_dependencies,
    'explicit': get_module_registry_dependencies,
    'none': map_none,
}

transpiled_externals_methods_map = {
    'all': map_none,
    # Grab the parents.
    'explicit': flatten_parents_module_registry_dependencies,
    # Don't need to flatten all the modules and map it as none, since
    # nothing from the Python system will be produced; also generally
    # not very useful for webpack's case.
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

# TODO figure out a way to poke into node_modules to determine the
# names to stub out for the extras?


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


def _generate_maps(package_names, registry_names, method_map, method_key):
    map_method = acquire_method(method_map, method_key)
    result_map = {}
    for name in registry_names:
        result_map.update(map_method(package_names, registry_name=name))

    return result_map


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

    return _generate_maps(
        package_names, registries, source_map_methods_map, method)


def generate_transpiled_externals(
        package_names, registries=('calmjs.modules'), method=_default):
    """
    Webpack specific; get all the source maps, but instead of returning
    that list of names are modules to be transpiled, assume that they
    are will be provided by an artifact, i.e. declare them as externals.

    This function returns a compatible mapping that should be assigned
    to the externals of the configuration, using the same arguments that
    were passed to the generate_transpile_source_maps function.
    """

    # the raw source map, to turn into the externals
    result_map = _generate_maps(
        package_names, registries, transpiled_externals_methods_map, method)
    return {
        key: {
            "root": ["__calmjs__", "modules", key],
            "amd": ["__calmjs__", "modules", key],
        }
        for key in result_map
    }


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
