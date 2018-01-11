# -*- coding: utf-8 -*-
"""
Integration with various tools proided by the calmjs.dev package
"""

from __future__ import unicode_literals

import codecs
import json
import logging
from os import makedirs
from os.path import basename
from os.path import dirname
from os.path import join
from os.path import exists
from os.path import normpath

from calmjs.exc import ToolchainAbort
from calmjs.toolchain import ARTIFACT_PATHS
from calmjs.toolchain import BUILD_DIR
from calmjs.toolchain import TEST_MODULE_PATHS_MAP
from calmjs.toolchain import spec_update_sourcepath_filter_loaderplugins
from calmjs.toolchain import spec_update_loaderplugin_registry
from calmjs.toolchain import toolchain_spec_prepare_loaderplugins
from calmjs.toolchain import CALMJS_LOADERPLUGIN_REGISTRY
from calmjs.toolchain import process_compile_entries
from calmjs.toolchain import dict_setget_dict

try:
    from calmjs.dev import karma
    from calmjs.dev.karma import BEFORE_KARMA
    from calmjs.dev.toolchain import TEST_FILENAME_PREFIX
    from calmjs.dev.toolchain import TEST_FILENAME_PREFIX_DEFAULT
    from calmjs.dev.toolchain import TEST_COVERED_TEST_PATHS
    from calmjs.dev.toolchain import TEST_COVERED_BUILD_DIR_PATHS
except ImportError:  # pragma: no cover
    # Package not available; None is the advice blackhole
    BEFORE_KARMA = None
    karma = None

from calmjs.parse.parsers.es5 import parse
from calmjs.parse import asttypes
from calmjs.parse import io
from calmjs.interrogate import yield_module_imports_nodes

from calmjs.webpack.base import WEBPACK_CONFIG
from calmjs.webpack.base import WEBPACK_RESOLVELOADER_ALIAS
from calmjs.webpack.base import WEBPACK_SINGLE_TEST_BUNDLE
from calmjs.webpack.base import DEFAULT_CALMJS_EXPORT_NAME
from calmjs.webpack.interrogation import probe_calmjs_webpack_module_names
from calmjs.webpack.manipulation import convert_dynamic_require_unparser

logger = logging.getLogger(__name__)

TEST_LOADER_MODNAMES = 'test_loader_modnames'
TEST_MODNAMES = 'test_modnames'


def webpack_advice(spec, extras=None):
    # As webpack has specific integration requirements with karma,
    # a test runner the calmjs.dev package provides, advise that
    # runner that before its execution, special handling needs to be
    # done to correct the generated configuration file.
    spec.advise(BEFORE_KARMA, karma_webpack, spec)


def _generate_combined_test_module(toolchain, spec):
    """
    Generate a combined test module can potentially save time.
    """

    # TEST_MODULE_PATHS_MAP
    test_file = join(spec[BUILD_DIR], '__calmjs_tests__.js')
    aliases = spec[WEBPACK_CONFIG]['resolve']['alias'] if spec.get(
        WEBPACK_CONFIG) else {}
    with codecs.open(test_file, 'w', encoding='utf8') as fd:
        # ensure that the calmjs bootstrap is loaded first, if it is
        # defined so that the dynamic imports are made available.
        if DEFAULT_CALMJS_EXPORT_NAME in aliases:
            fd.write("require('%s');\n" % DEFAULT_CALMJS_EXPORT_NAME)

        # provide the loader keys first
        fd.writelines(
            "require(%s);\n" % json.dumps(module)
            for module in spec.get(TEST_LOADER_MODNAMES, ())
        )

        # then include the tests.
        fd.writelines(
            "require(%s);\n" % json.dumps(module)
            for module in spec.get(TEST_MODNAMES, ())
        )

    spec[karma.KARMA_CONFIG]['preprocessors'][test_file] = ['webpack']

    return [test_file]


def _finalize_test_path(toolchain, spec, modname, path):
    """
    Process the path as a test file and bring it to a finalized location
    if necessary.

    Current condition for the relocation is usage of dynamic imports
    within the provided ES5 source file.
    """

    if not exists(path):
        # nothing to do.
        return path

    with codecs.open(path, encoding='utf8') as fd:
        try:
            tree = io.read(parse, fd)
            imports = yield_module_imports_nodes(tree)
        except Exception:
            # can't do anything.
            return path

    # if there are not any nodes that are not strings
    if not any(
            node for node in imports if not isinstance(node, asttypes.String)):
        return path

    # generate the new target using the toolchain instance.
    rel_target = toolchain.modname_source_to_target(
        spec, modname, path)
    target = join(spec[BUILD_DIR], normpath(rel_target))
    target_map = target + '.map'
    makedirs(dirname(target))

    with codecs.open(target, 'w', encoding='utf8') as ss:
        with codecs.open(target_map, 'w', encoding='utf8') as sm:
            io.write(convert_dynamic_require_unparser(), tree, ss, sm)

    return target


def _process_loaders_paths(toolchain, spec, loaders_paths_map):
    fake_spec = {
        CALMJS_LOADERPLUGIN_REGISTRY: spec.get(CALMJS_LOADERPLUGIN_REGISTRY),
        WEBPACK_RESOLVELOADER_ALIAS: {},
    }
    spec_update_sourcepath_filter_loaderplugins(
        fake_spec, loaders_paths_map, 'default')
    toolchain_spec_prepare_loaderplugins(
        toolchain, fake_spec, 'testloaders', WEBPACK_RESOLVELOADER_ALIAS)
    # borrow the private entry generator by the toolchain.
    entries = toolchain._gen_modname_source_target_modpath(
        spec, fake_spec['testloaders_sourcepath'])
    # manually trigger the compile entries using the loaderplugin rules.
    modpaths, targetpaths, export_module_names = process_compile_entries(
        toolchain.compile_loaderplugin_entry, spec, entries)
    # the targets will be injected into the alias.
    config = spec[karma.KARMA_CONFIG]

    webpack_conf = config['webpack']
    # directly update these as aliases.
    resolve = dict_setget_dict(webpack_conf, 'resolve')
    resolve_alias = dict_setget_dict(resolve, 'alias')

    for modname, p in targetpaths.items():
        # add the finalized modname as alaises.
        resolve_alias[modname] = join(spec[BUILD_DIR], normpath(p))
        # also remove it from the test module paths map as these are not
        # tests.
        spec[TEST_MODULE_PATHS_MAP].pop(modname, None)

    # since the registry should be the same, assume the results are
    # as expected; so just do a simple merge.
    resolve_loader = dict_setget_dict(webpack_conf, 'resolveLoader')
    resolve_loader_alias = dict_setget_dict(resolve_loader, 'alias')
    resolve_loader_alias.update(fake_spec[WEBPACK_RESOLVELOADER_ALIAS])

    # grab all the raw modpath keys and store them for the module
    # generation process later.
    spec[TEST_LOADER_MODNAMES] = set(modpaths)


def _process_test_files(toolchain, spec):
    # return values
    test_files = set()
    loaders_paths_map = {}

    test_prefix = spec.get(TEST_FILENAME_PREFIX, TEST_FILENAME_PREFIX_DEFAULT)
    config = spec[karma.KARMA_CONFIG]
    preprocessors = config['preprocessors']
    alias = config['webpack']['resolve']['alias']
    spec[TEST_MODNAMES] = test_modnames = set()

    # Process tests separately; include them iff the filename starts
    # with test, otherwise they are just provided as dependency modules.
    for modname, path in spec.get(TEST_MODULE_PATHS_MAP, {}).items():
        if '!' in modname:
            # defer the handling to later
            loaders_paths_map[modname] = path
            continue

        if not path.endswith('.js'):
            # completely omit any non JavaScript files.
            alias[modname] = path
            logger.debug(
                "only aliasing modpath '%s' to target '%s' as target does not "
                "end with '.js'", modname, path,
            )
            continue

        # as the provided js file can contain dynamic imports, verify
        # that it does not.
        final_path = _finalize_test_path(toolchain, spec, modname, path)
        alias[modname] = final_path

        # also apply the webpack preprocessor to the test.
        preprocessors[final_path] = ['webpack'] + preprocessors.pop(path, [])

        # only inject
        if basename(final_path).startswith(test_prefix):
            test_modnames.add(modname)
            test_files.add(final_path)

        if path in spec.get(TEST_COVERED_TEST_PATHS, {}):
            spec[TEST_COVERED_TEST_PATHS].discard(path)
            spec[TEST_COVERED_TEST_PATHS].add(final_path)

    return test_files, loaders_paths_map


def _generate_test_files(toolchain, spec):
    test_files, loaders_paths_map = _process_test_files(toolchain, spec)
    _process_loaders_paths(toolchain, spec, loaders_paths_map)

    if spec.get(WEBPACK_SINGLE_TEST_BUNDLE, True):
        return _generate_combined_test_module(toolchain, spec)
    else:
        logger.warning("using 'WEBPACK_SINGLE_TEST_BUNDLE' is unsupported")

    return test_files


def _generate_coverage_loader(toolchain, spec):
    # apply the loader to all paths to be covered that require the
    # webpack specific loader, as the originals will _not_ be used.
    include = []
    loader = {
        "loader": "sourcemap-istanbul-instrumenter-loader",
        "include": include,
    }

    for covered_path in spec.get(TEST_COVERED_TEST_PATHS, []):
        # these should already be absolutes, apply directly.
        include.append(covered_path)

    for covered_path in spec.get(TEST_COVERED_BUILD_DIR_PATHS, []):
        # these will need to be joined with build_dir, as they are
        # relative.
        include.append(join(spec[BUILD_DIR], normpath(covered_path)))

    if include:
        return loader


def _apply_coverage(toolchain, spec):
    loader = _generate_coverage_loader(toolchain, spec)
    if not loader:
        return
    config = spec[karma.KARMA_CONFIG]
    module = config['webpack']['module'] = config['webpack'].get('module', {})
    loaders = module['loaders'] = module.get('loaders', [])
    loaders.append(loader)


def karma_webpack(spec, toolchain=None):
    """
    An advice for the karma runtime before execution of karma that is
    needed so that the generated artifiact will work  under karma;
    needed when WebpackToolchain was used for artifact generation.

    This advice should be registered to BEFORE_KARMA by the
    WebpackToolchain.

    This will modify the related items in spec for the generation of the
    karma.conf.js to so that the tests will be correctly executed in
    conjunction with the generated webpack artifact through karma.
    """

    # Importing this here as these modules may not be available, so to
    # avoid potential issues, import them within the scope of this
    # function; this function should never be called if the calmjs.dev
    # python package is not available for import (and the setup should
    # not add this advice to the toolchain).

    if toolchain is None:
        # obeying import rules.
        from calmjs.webpack.cli import default_toolchain as toolchain

    try:
        from calmjs.dev import karma
    except ImportError:
        logger.error(
            "package 'calmjs.dev' not available; cannot apply webpack "
            "specific information without karma being available."
        )
        return

    required_keys = [karma.KARMA_CONFIG, BUILD_DIR]
    for key in required_keys:
        if key not in spec:
            logger.error(
                "'%s' not provided by spec; aborting configuration for karma "
                "test runner", key
            )
            raise ToolchainAbort("spec missing key '%s'" % key)

    config = spec.get(karma.KARMA_CONFIG)
    config['preprocessors'] = config.get('preprocessors', {})

    # XXX note that the current way that calmjs.dev only deal with the
    # JSON chunk, and not any actual executable scripts which which
    # includes actual object types - will likely need that be fixed.
    # For now, simply just do this.
    if WEBPACK_CONFIG in spec:
        webpack_config = {
            # filter out the entry as karma-webpack should be taking
            # caring of that.
            k: v for k, v in spec.get(WEBPACK_CONFIG).items() if k != 'entry'
        }
        config['webpack'] = webpack_config
    else:
        # ensure that the loader plugin registry is assigned.
        spec_update_loaderplugin_registry(
            spec, toolchain.loaderplugin_registry)
        # with the assumption that the __calmjs_loader__ is available at
        # that specific location - as standard standalone webpack has no
        # visible external interfaces like this.
        externals = {"__calmjs_loader__": {"root": ["__calmjs__"]}}
        for p in spec.get(ARTIFACT_PATHS, ()):
            logger.debug('processing artifact file %r', p)
            with codecs.open(p, encoding='utf8') as fd:
                try:
                    for module_name in probe_calmjs_webpack_module_names(
                            parse(fd.read())):
                        externals[module_name] = {
                            "root": ["__calmjs__", "modules", module_name]
                        }
                except TypeError:
                    logger.warning(
                        "unable to extract calmjs related exports from "
                        "provided artifact file '%s'; it does not appear to "
                        "be generated using calmjs.webpack with the "
                        "compatible export features enabled", p
                    )

        # generate a barebone webpack config that only contain the tests
        # along with the extracted externals.
        config['webpack'] = {
            "output": {
                "filename": "dummy.webpack.js",
                "library": "__calmjs_karma__",
                "libraryTarget": "umd",
                "path": spec[BUILD_DIR],
            },
            "externals": externals,
            "resolve": {
                "alias": {},
            },
        }

    test_files = _generate_test_files(toolchain, spec)
    _apply_coverage(toolchain, spec)

    # purge all files
    files = config['files'] = []
    # included the artifacts first
    # then provide the test files.
    files.extend(sorted(test_files))
