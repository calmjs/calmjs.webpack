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
from calmjs.dist import flatten_parents_extras_calmjs
from calmjs.dist import flatten_module_registry_dependencies
from calmjs.dist import flatten_parents_module_registry_dependencies
from calmjs.dist import flatten_module_registry_names

from calmjs.webpack.base import DEFAULT_BOOTSTRAP_EXPORT
from calmjs.webpack.base import DEFAULT_BOOTSTRAP_COMMONJS

logger = logging.getLogger(__name__)
_default = 'all'


def map_none(*a, **kw):
    return {}


def list_none(*a, **kw):
    return []


sourcepath_methods_map = {
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
    # this may be misleading?  Perhaps make a name that makes the usage
    # and export of artifacts sourced from node_modules that are to be
    # included directly, and ensure that if calmjs is used to build it,
    # it be exported as part of the __calmjs__.modules, or also generate
    # a completely separate thing.
    'explicit': get_extras_calmjs,
    # if 'none' is used, the default node_modules lookup behavior will
    # be used to get the module on require to include into the generated
    # artifact.
    'none': map_none,
    # TODO: should define a way to declare explicit externals.
}

external_extras_calmjs_methods = {
    'all': map_none,
    'explicit': flatten_parents_extras_calmjs,
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
        The names of the Python package to generate the module name to
        filesystem path mapping (source path).
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
            Produce an empty mapping.

        All options not on above list defaults to 'all'
    """

    registries = acquire_method(
        calmjs_module_registry_methods, method)(package_names)
    return registries


def _generate_transpile_maps(
        package_names, registry_names, method_map, method_key):
    map_method = acquire_method(method_map, method_key)
    result_map = {}
    for name in registry_names:
        result_map.update(map_method(package_names, registry_name=name))

    return result_map


def generate_transpile_sourcepaths(
        package_names, registries=('calmjs.modules'), method=_default):
    """
    Invoke the module_registry_dependencies family of dist functions,
    with the specified registries, to produce the required the module
    name to filesystem path mapping.

    Arguments:

    package_names
        The names of the Python package to generate the the module name
        to filesystem path mapping for.
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
            Produce an empty mapping.

        Defaults to 'all'.
    """

    return _generate_transpile_maps(
        package_names, registries, sourcepath_methods_map, method)


def generate_transpiled_externals(
        package_names, registries=('calmjs.modules'), method=_default):
    """
    Webpack specific - for every call to generate_transpile_sourcepaths
    with the results assigned to the transpile_sourcepaths of a spec, an
    associated call to this function with the identical arguments should
    be called and the results be updated to the webpack root
    configuration object's external key.

    This is so that webpack will have a correct set of modules names
    that it will look up externally.
    """

    # the raw source map, to turn into the externals
    return {
        key: {
            "root": [DEFAULT_BOOTSTRAP_EXPORT, "modules", key],
            "amd": [DEFAULT_BOOTSTRAP_EXPORT, "modules", key],
            # there will be no equivalent commonjs modules, so we are
            # going to cheat and use global module for emulating this.
            # see the documentation at this constant for usage.
            "commonjs": list(DEFAULT_BOOTSTRAP_COMMONJS) + ["modules", key],
            "commonjs2": list(DEFAULT_BOOTSTRAP_COMMONJS) + ["modules", key],
        }
        for key in _generate_transpile_maps(
            package_names, registries, transpiled_externals_methods_map, method
        )
    }


def _generate_bundle_maps(package_names, working_dir, method_map, method_key):
    map_method = acquire_method(method_map, method_key)
    # the extras keys will be treated as valid Node.js package manager
    # subdirectories.
    valid_pkgmgr_dirs = set(get('calmjs.extras_keys').iter_records())
    extras_calmjs = map_method(package_names)
    bundle_sourcepath = {}

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
            bundle_sourcepath[k] = join(basedir, *(v.split('/')))

    return bundle_sourcepath


def generate_bundle_sourcepaths(
        package_names, working_dir=None, method=_default):
    """
    Acquire the bundled module name to filesystem path mapping through
    the calmjs registry system.

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
    return _generate_bundle_maps(
        package_names, working_dir, extras_calmjs_methods, method)


def generate_bundled_externals(
        package_names, working_dir=None, method=_default):
    """
    Webpack specific - for every call to generate_bundle_sourcepaths
    with the results assigned to the bundle_sourcepaths of a spec, an
    associated call to this function with the identical arguments should
    be called and the results be updated to the webpack root
    configuration object's external key.

    This is so that webpack will have a correct set of modules names
    that it will look up externally for modules that are sourced from
    registered Node.js associated package management systems.
    """

    working_dir = working_dir if working_dir else getcwd()
    # track the list of declared externals.
    declared = _generate_bundle_maps(
        package_names, working_dir, extras_calmjs_methods, method)
    return {
        key: {
            # assume that they are bundle standardly.
            "root": key,
            "amd": key,
            # for these commonjs types, assume that there exists node
            # modules for them; not really supported anyway, just to
            # make future versions of webpack happy.
            "commonjs": key,
            "commonjs2": key,
        }
        for key in _generate_bundle_maps(
            package_names, working_dir, external_extras_calmjs_methods, method
        )
        if key not in declared
    }
