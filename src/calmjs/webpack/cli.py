# -*- coding: utf-8 -*-
"""
calmjs webpack cli tools.
"""

# TODO merge this upstream.

import logging

from calmjs.toolchain import Spec
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import CALMJS_MODULE_REGISTRY_NAMES
from calmjs.toolchain import EXPORT_TARGET
from calmjs.toolchain import SOURCE_PACKAGE_NAMES

from calmjs.webpack.toolchain import WebpackToolchain

from calmjs.webpack.dist import generate_transpile_sourcepaths
from calmjs.webpack.dist import generate_bundle_sourcepaths
from calmjs.webpack.dist import get_calmjs_module_registry_for

default_toolchain = WebpackToolchain()
logger = logging.getLogger(__name__)


def create_spec(
        package_names, export_target=None, working_dir=None, build_dir=None,
        source_registry_method='all', source_registries=None,
        sourcepath_method='all', bundlepath_method='all',
        ):
    """
    Produce a spec for the compilation through the WebpackToolchain.

    Arguments:

    package_names
        The name of the Python package to source the dependencies from.

    export_target
        The filename for the output, can be an absolute path to a file.
        Defaults to the package_name with a '.js' suffix added in the
        working_dir.

    working_dir
        The working directory.  If the package specified any extras
        calmjs requirements (e.g. node_modules), they will be searched
        for from here.  Defaults to current working directory.

    build_dir
        The build directory.  Defaults to a temporary directory that is
        automatically removed when done.

    source_registry_method
        The acqusition method for the list of calmjs module registries
        declared for the provided package names.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the declared calmjs module registries to use.
        'explicit'
            Only use the calmjs module registries declared for specified
            packages.
        'none'
            Do not acquire sources.  Useful for creating bundles of just
            the bundle sources.

        Defaults to 'all'.

    source_registries
        If the provided packages did not specify all registries or have
        declared modules in alternative but not explicitly specified
        calmjs module registries, this option can be used to pass an
        explicit list of calmjs module registries to use.  Typical use
        case is to generate tests.

    sourcepath_method
        The acquisition method for the source module to filesystem path
        mapping for the given packages from the source_registries that
        were specified.

        Choices are between 'all', 'explicit' or 'none'.
        Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package to
            acquire the sources declared for each of those modules.
        'explicit'
            Only acquire the sources for the specified package.
        'none'
            Do not acquire sources.  Useful for creating bundles of just
            the bundle sources.

        Defaults to 'all'.

    bundlepath_method
        The acquisition method for retrieving explicitly defined bundle
        sources from Node.js module sources for the given packages.

        Choices are between 'all', 'explicit' or 'none'.
        Defaults to 'all'.

        'all'
            Traverse the dependency graph for the specified package and
            acquire the declarations.
        'explicit'
            Only acquire the bundle sources declared for the specified
            package.
        'none'
            Do not specify any bundle files.

        Defaults to 'all'.

    """

    working_dir = working_dir if working_dir else default_toolchain.join_cwd()

    if export_target is None:
        # Take the final package name for now...
        if package_names:
            export_target = package_names[-1] + '.js'
        else:
            export_target = 'calmjs.webpack.export.js'

    spec = Spec()

    if source_registries is None:
        source_registries = get_calmjs_module_registry_for(
            package_names, method=source_registry_method)
        if source_registries:
            logger.info(
                "automatically picked registries %r for building source map",
                source_registries,
            )
        elif package_names:
            logger.warning(
                "no module registry declarations found using packages %r "
                "using acquisition method '%s'",
                package_names, source_registry_method,
            )
        else:
            logger.warning('no packages specified for spec construction')
    else:
        logger.info(
            "using manually specified registries %r for building source map",
            source_registries,
        )

    spec[BUILD_DIR] = build_dir
    spec[CALMJS_MODULE_REGISTRY_NAMES] = source_registries
    spec[EXPORT_TARGET] = export_target
    spec[SOURCE_PACKAGE_NAMES] = package_names

    spec['transpile_sourcepath'] = generate_transpile_sourcepaths(
        package_names=package_names,
        registries=source_registries,
        method=sourcepath_method,
    )

    spec['bundle_sourcepath'] = generate_bundle_sourcepaths(
        package_names=package_names,
        working_dir=working_dir,
        method=bundlepath_method,
    )

    return spec


def compile_all(
        package_names, export_target=None, working_dir=None, build_dir=None,
        source_registry_method='all', source_registries=None,
        sourcepath_method='all', bundlepath_method='all',
        toolchain=default_toolchain):
    """
    Invoke the webpack compiler to generate a JavaScript bundle file for
    a given Python package.  The bundle will include all the
    dependencies as specified by it and its parents.

    Arguments:

    toolchain
        The toolchain instance to use.  Default is the instance in this
        module.

    For other arguments, please refer to create_spec as they are passed
    to it.

    Naturally, this package will need all its extras calmjs declarations
    available, plus the availability of webpack, before anything can be
    done.
    """

    spec = create_spec(
        package_names=package_names,
        export_target=export_target,
        working_dir=working_dir,
        build_dir=build_dir,
        source_registry_method=source_registry_method,
        source_registries=source_registries,
        sourcepath_method=sourcepath_method,
        bundlepath_method=bundlepath_method,
    )
    toolchain(spec)
    return spec
