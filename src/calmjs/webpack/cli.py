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

from calmjs.webpack.base import WEBPACK_EXTERNALS
from calmjs.webpack.base import WEBPACK_OUTPUT_LIBRARY

from calmjs.webpack.base import DEFAULT_BOOTSTRAP_EXPORT

from calmjs.webpack.toolchain import WebpackToolchain

from calmjs.webpack.dist import generate_transpile_sourcepaths
from calmjs.webpack.dist import generate_bundle_sourcepaths
from calmjs.webpack.dist import generate_transpiled_externals
from calmjs.webpack.dist import generate_bundled_externals
from calmjs.webpack.dist import get_calmjs_module_registry_for

default_toolchain = WebpackToolchain()
logger = logging.getLogger(__name__)


def create_spec(
        package_names, export_target=None, working_dir=None, build_dir=None,
        source_registry_method='all', source_registries=None,
        sourcepath_method='all', bundlepath_method='all',
        use_calmjs_bootstrap=True,
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
            Only acquire the sources for the specified package.  This
            option requires 'use_calmjs_bootstrap' be True or it may not
            function as intended.
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
            package.  This option requires 'use_calmjs_bootstrap' be
            True or it may not function as intended.
        'none'
            Do not specify any bundle files.

        Defaults to 'all'.

    use_calmjs_bootstrap
        Add the calmjs webpack module bootstrap module.  When enabled,
        this option modifies the configuration so that for root and amd
        mode, a __calmjs__ module is always required and exported, so
        that the explicit option of *path_method of explicit will work
        as intended.

        This also force the webpack.output.library option for the config
        to be set to '__calmjs__'.

        Defaults to True.

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

    # TODO figure out if/how to deal with explicit webpack.library and
    # the webpack.libraryTarget option, as this conflicts with the
    # use_calmjs_bootstrap option

    if use_calmjs_bootstrap:
        logger.info(
            "using calmjs bootstrap; webpack.output.library set to '%s'",
            DEFAULT_BOOTSTRAP_EXPORT,
        )
        spec[WEBPACK_OUTPUT_LIBRARY] = DEFAULT_BOOTSTRAP_EXPORT
        # also specify this as the external that is needed.
        spec[WEBPACK_EXTERNALS] = {
            DEFAULT_BOOTSTRAP_EXPORT: {
                "root": DEFAULT_BOOTSTRAP_EXPORT,
                "amd": DEFAULT_BOOTSTRAP_EXPORT,
            }
        }
        spec[WEBPACK_EXTERNALS].update(generate_transpiled_externals(
            package_names=package_names,
            registries=source_registries,
            method=sourcepath_method,
        ))
        spec[WEBPACK_EXTERNALS].update(generate_bundled_externals(
            package_names=package_names,
            working_dir=working_dir,
            method=bundlepath_method,
        ))
    else:
        # lazily deriving that from previous value.
        spec[WEBPACK_OUTPUT_LIBRARY] = export_target[:-3]
        logger.info(
            "not using calmjs bootstrap; "
            "webpack.output.library set to '%s'", spec[WEBPACK_OUTPUT_LIBRARY]
        )
        # TODO should warn about the *path_methods if they are not all.

    return spec


def compile_all(
        package_names, export_target=None, working_dir=None, build_dir=None,
        source_registry_method='all', source_registries=None,
        sourcepath_method='all', bundlepath_method='all',
        use_calmjs_bootstrap=True,
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
        use_calmjs_bootstrap=use_calmjs_bootstrap,
    )
    toolchain(spec)
    return spec
