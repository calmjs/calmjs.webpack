# -*- coding: utf-8 -*-
"""
calmjs webpack cli tools.
"""

import logging
from os.path import join
from os.path import realpath

from calmjs.toolchain import Spec
from calmjs.toolchain import spec_update_sourcepath_filter_loaderplugins

from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import CALMJS_MODULE_REGISTRY_NAMES
from calmjs.toolchain import CALMJS_LOADERPLUGIN_REGISTRY_NAME
from calmjs.toolchain import WORKING_DIR

from calmjs.toolchain import EXPORT_TARGET
from calmjs.toolchain import GENERATE_SOURCE_MAP
from calmjs.toolchain import SOURCE_PACKAGE_NAMES

from calmjs.webpack.base import WEBPACK_SINGLE_TEST_BUNDLE
from calmjs.webpack.base import WEBPACK_ENTRY_POINT
from calmjs.webpack.base import WEBPACK_EXTERNALS
from calmjs.webpack.base import WEBPACK_OUTPUT_LIBRARY
from calmjs.webpack.base import WEBPACK_OPTIMIZE_MINIMIZE
from calmjs.webpack.base import VERIFY_IMPORTS

from calmjs.webpack.base import CALMJS_WEBPACK_LOADERPLUGINS
from calmjs.webpack.base import DEFAULT_BOOTSTRAP_EXPORT
from calmjs.webpack.base import DEFAULT_BOOTSTRAP_EXPORT_CONFIG

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
        calmjs_loaderplugin_registry_name=CALMJS_WEBPACK_LOADERPLUGINS,
        calmjs_compat=True,
        webpack_entry_point=DEFAULT_BOOTSTRAP_EXPORT,
        webpack_output_library=True,
        webpack_optimize_minimize=False,
        verify_imports=True,
        ):
    """
    Produce a spec for the compilation through the WebpackToolchain.

    Arguments:

    package_names
        The name of the Python package to source the dependencies from.

    export_target
        The filename for the output, can be an absolute path to a file.
        Defaults to the last package_name with a '.js' suffix added in
        the working_dir; e.g. if package_names is ['a', 'b'], the
        default export_target will be b.js at working_dir.

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
            option requires 'calmjs_compat' be True or it may not
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
            package.  This option requires 'calmjs_compat' be True or it
            may not function as intended.
        'none'
            Do not specify any bundle files.

        Defaults to 'all'.

    calmjs_compat
        Enable calmjs compatibility settings

        Add the calmjs webpack module bootstrap module.  When enabled,
        this option modifies the configuration so that for root and amd
        mode, a __calmjs__ module is always required and exported, so
        that the explicit option of *path_method of explicit will work
        as intended.

        This also force the webpack.output.library option for the config
        to be set to '__calmjs__' and overrides the webpack_entry_point
        and calmjs_output_library arguments.

        If this is False, the webpack.output.library option will default
        to the last item of package_names, similar to export_target,
        unless overridden.

        Defaults to True.

    webpack_entry_point
        If set manually, the path resolved by the alias will be used as
        the entry_point instead, and the webpack.output.library will
        also be default to this value.  If the alias is not resolved,
        the build will most certainly fail to produce anything of value.

        Defaults to '__calmjs__', which under the default toolchain flow
        it will be the generated __calmjs_bootstrap__ module.  This
        generated module includes every resolved module mapped by the
        path_methods and they will be available as the modules attribute
        in the exported library.

        Requires calmjs_compat to be False in order for this argument to
        take effect.

    webpack_output_library
        If set manually, the output library will be set to this value;
        defaults to True, which sets automatic generation based on
        calmjs_compat and webpack_entry_point arguments; a False or
        None value implies that this is not to be exported as a library.

        Requires calmjs_compat to be False in order for this argument to
        take effect.

    """

    if calmjs_compat and (
            webpack_entry_point != DEFAULT_BOOTSTRAP_EXPORT or
            webpack_output_library is not True):
        logger.warning(
            "webpack_entry_point and/or webpack_output_library is assigned "
            "a different value than their defaults while calmjs_compat is set "
            "to True in function %s.%s; to have those values take effect, "
            "ensure the calmjs_compat argument is set to False ",
            __name__, 'create_spec',
        )

    working_dir = working_dir if working_dir else default_toolchain.join_cwd()

    # Normalize export_target and raw webpack.output.library
    # Note that webpack_output_library is not directly assigned at this
    # moment.
    if export_target is None:
        # Take the final package name for now...
        if package_names:
            computed_output_library = package_names[-1]
        else:
            computed_output_library = 'calmjs.webpack.export'
        export_target = realpath(
            join(working_dir, computed_output_library + '.js'))
        logger.info("'export_target' is now set to '%s'", export_target)
    else:
        computed_output_library = export_target[:-3]

    spec = Spec()

    if source_registries is None:
        source_registries = get_calmjs_module_registry_for(
            package_names, method=source_registry_method)
        if source_registries:
            logger.info(
                "automatically picked registries %r for sourcepaths",
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
            "using manually specified registries %r for sourcepaths",
            source_registries,
        )

    spec[BUILD_DIR] = build_dir
    spec[WORKING_DIR] = working_dir
    spec[CALMJS_MODULE_REGISTRY_NAMES] = source_registries
    spec[EXPORT_TARGET] = export_target
    spec[SOURCE_PACKAGE_NAMES] = package_names
    spec[WEBPACK_OPTIMIZE_MINIMIZE] = webpack_optimize_minimize
    spec[VERIFY_IMPORTS] = verify_imports
    spec[CALMJS_LOADERPLUGIN_REGISTRY_NAME] = calmjs_loaderplugin_registry_name

    spec_update_sourcepath_filter_loaderplugins(
        spec, generate_transpile_sourcepaths(
            package_names=package_names,
            registries=source_registries,
            method=sourcepath_method,
        ), 'transpile_sourcepath',
    )

    spec_update_sourcepath_filter_loaderplugins(
        spec, generate_bundle_sourcepaths(
            package_names=package_names,
            working_dir=working_dir,
            method=bundlepath_method,
        ), 'bundle_sourcepath',
    )

    if calmjs_compat:
        logger.info(
            "using calmjs bootstrap; webpack.output.library set to '%s'",
            DEFAULT_BOOTSTRAP_EXPORT,
        )
        # the output library and entry point is forced.
        spec[WEBPACK_OUTPUT_LIBRARY] = DEFAULT_BOOTSTRAP_EXPORT
        spec[WEBPACK_ENTRY_POINT] = DEFAULT_BOOTSTRAP_EXPORT
        # also specify this as the external to notify the toolchain that
        # the complete passthrough bootstrap module will be required.
        spec[WEBPACK_EXTERNALS] = {
            DEFAULT_BOOTSTRAP_EXPORT: DEFAULT_BOOTSTRAP_EXPORT_CONFIG
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
        # assume the entry point is a sane value
        spec[WEBPACK_ENTRY_POINT] = webpack_entry_point

        # TODO should warn about the *path_methods if they are not set
        # to 'all'.
        # TODO address the webpack.output.libraryTarget option, as
        # currently calmjs_compat mode assumes that it must be "umd".
        if webpack_output_library is True:
            if webpack_entry_point == DEFAULT_BOOTSTRAP_EXPORT:
                spec[WEBPACK_OUTPUT_LIBRARY] = computed_output_library
                logger.info(
                    "calmjs_compat is disabled; webpack.output.library "
                    "automatically set to '%s', derived from input package "
                    "names and export filename as the entry point is defined "
                    "to be the simplified calmjs bootstrap.",
                    spec[WEBPACK_OUTPUT_LIBRARY]
                )
            else:
                # set to entry_point as that is defined.
                spec[WEBPACK_OUTPUT_LIBRARY] = webpack_entry_point
                logger.info(
                    "calmjs_compat is disabled; webpack.output.library "
                    "automatically set to '%s' as this is the explicit "
                    "webpack entry point specified",
                    spec[WEBPACK_OUTPUT_LIBRARY]
                )
        elif not webpack_output_library:
            logger.info(
                "webpack.output.library is disabled; it will be unset.")
        else:
            spec[WEBPACK_OUTPUT_LIBRARY] = webpack_output_library
            logger.info(
                "webpack.output.library is manually set to '%s'",
                spec[WEBPACK_OUTPUT_LIBRARY]
            )

    # XXX for now we force this feature on - will need to determine how
    # and what exactly are the benefits and drawbacks are.
    spec[WEBPACK_SINGLE_TEST_BUNDLE] = True
    # Also force source maps on, given that the regeneration *will*
    # mangle the source.  This will be useful for test coverage
    # reporting through e.g. istanbul.
    spec[GENERATE_SOURCE_MAP] = True

    return spec


def compile_all(
        package_names, export_target=None, working_dir=None, build_dir=None,
        source_registry_method='all', source_registries=None,
        sourcepath_method='all', bundlepath_method='all',
        calmjs_loaderplugin_registry_name=CALMJS_WEBPACK_LOADERPLUGINS,
        calmjs_compat=True,
        webpack_entry_point=DEFAULT_BOOTSTRAP_EXPORT,
        webpack_output_library=True,
        toolchain=default_toolchain,
        webpack_optimize_minimize=False,
        verify_imports=True,
        ):
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
        calmjs_loaderplugin_registry_name=calmjs_loaderplugin_registry_name,
        calmjs_compat=calmjs_compat,
        webpack_entry_point=webpack_entry_point,
        webpack_output_library=webpack_output_library,
        webpack_optimize_minimize=webpack_optimize_minimize,
        verify_imports=verify_imports,
    )
    toolchain(spec)
    return spec
