# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
from os.path import exists
from os.path import join

from calmjs.loaderplugin import LoaderPluginRegistry
from calmjs.parse.exceptions import ECMASyntaxError
from calmjs.utils import pretty_logging
from calmjs.toolchain import Spec
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.toolchain import LOADERPLUGIN_SOURCEPATH_MAPS
from calmjs.npm import get_npm_version

from calmjs.webpack import toolchain
from calmjs.webpack.base import WEBPACK_RESOLVELOADER_ALIAS
from calmjs.webpack.loaderplugin import AutogenWebpackLoaderPluginRegistry

from calmjs.testing import utils
from calmjs.testing import mocks


def mock_text_loader(working_dir):
    module_root = join(working_dir, 'node_modules', 'text-loader')
    module_cfg = join(module_root, 'package.json')
    module_src = join(module_root, 'text.js')

    # create the dummy text-loader package.json entry, using just the
    # bare required information from the real package.
    os.makedirs(module_root)
    with open(module_cfg, 'w') as fd:
        json.dump({
            "name": "text-loader",
            "version": "0.0.1",
            "main": "index.js",
            "license": "ISC",
        }, fd)

    return module_src


class CheckNameTestCase(unittest.TestCase):

    def test_default(self):
        with pretty_logging(stream=mocks.StringIO()) as s:
            self.assertTrue(toolchain.check_name_declared(
                alias={'some/file.txt': 'some/file.txt'},
                loaders={'text': 'text-loader/index.js'},
                externals={},
                loader_registry=AutogenWebpackLoaderPluginRegistry(
                    'calmjs.webpack.loaderplugins'),
                name='text!some/file.txt',
            ))
        self.assertIn(
            "'text!some/file.txt' resolved to 'some/file.txt'",
            s.getvalue())

    def test_loader_not_declared(self):
        # basically whatever reason it was NOT in the resolveLoaders
        with pretty_logging(stream=mocks.StringIO()) as s:
            self.assertFalse(toolchain.check_name_declared(
                alias={'some/file.txt': 'some/file.txt'},
                loaders={},
                externals={},
                loader_registry=AutogenWebpackLoaderPluginRegistry(
                    'calmjs.webpack.loaderplugins'),
                name='text!some/file.txt',
            ))
        self.assertIn("loader 'text' not found in config", s.getvalue())

    def test_loader_not_declared_in_externals(self):
        # same case as above, but in externals
        with pretty_logging(stream=mocks.StringIO()) as s:
            self.assertTrue(toolchain.check_name_declared(
                alias={'some/file.txt': 'some/file.txt'},
                loaders={},
                externals={'text!some/file.txt'},
                loader_registry=AutogenWebpackLoaderPluginRegistry(
                    'calmjs.webpack.loaderplugins'),
                name='text!some/file.txt',
            ))
        self.assertIn("loader 'text' not found in config", s.getvalue())

    def test_missing_plugin(self):
        with pretty_logging(stream=mocks.StringIO()) as s:
            self.assertFalse(toolchain.check_name_declared(
                alias={'some/file.txt': 'some/file.txt'},
                loaders={'text': 'text-loader/index.js'},
                externals={},
                loader_registry=LoaderPluginRegistry(
                    'missing', _working_set=mocks.WorkingSet({})),
                name='text!some/file.txt',
            ))
        self.assertIn(
            "check_name_declared cannot resolve handler for "
            "'text!some/file.txt'", s.getvalue())

    def test_simply_externals(self):
        # same case as above, but in externals
        self.assertTrue(toolchain.check_name_declared(
            alias={},
            loaders={},
            externals={'text!some/file.txt'},
            loader_registry=LoaderPluginRegistry(
                'missing', _working_set=mocks.WorkingSet({})),
            name='text!some/file.txt',
        ))


class ToolchainBootstrapTestCase(unittest.TestCase):
    """
    Test the bootstrap function
    """

    def test_runtime_name(self):
        # seems redundant, but...
        platform = 'posix'
        self.assertEqual(
            toolchain.get_webpack_runtime_name(platform), 'webpack')
        platform = 'win32'
        self.assertEqual(
            toolchain.get_webpack_runtime_name(platform), 'webpack.cmd')


@unittest.skipIf(get_npm_version() is None, "npm is unavailable")
class ToolchainUnitTestCase(unittest.TestCase):
    """
    Just testing out the toolchain units.
    """

    def test_prepare_failure_manual(self):
        webpack = toolchain.WebpackToolchain()
        spec = Spec(toolchain_bin_path='/no/such/path')
        with self.assertRaises(RuntimeError) as e:
            webpack.prepare(spec)

        self.assertEqual(
            str(e.exception),
            "'/no/such/path' does not exist; cannot be used as '%s' binary" % (
                webpack.webpack_bin
            ),
        )

    def test_prepare_failure_which_fail(self):
        utils.stub_os_environ(self)
        utils.remember_cwd(self)

        # must go to a directory where webpack is guaranteed to not be
        # available through node_modules or the environmental PATH
        os.environ['NODE_PATH'] = ''
        os.environ['PATH'] = ''
        tmpdir = utils.mkdtemp(self)
        os.chdir(tmpdir)

        webpack = toolchain.WebpackToolchain()
        spec = Spec()
        with self.assertRaises(RuntimeError) as e:
            webpack.prepare(spec)

        # not fixed string because platform specific value.
        self.assertEqual(str(e.exception), "unable to locate '%s'" % (
            webpack.webpack_bin
        ))

    def test_prepare_failure_export_target(self):
        tmpdir = utils.mkdtemp(self)
        webpack = toolchain.WebpackToolchain()

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        spec = Spec(build_dir=tmpdir)
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        with self.assertRaises(RuntimeError) as e:
            webpack.prepare(spec)
        self.assertEqual(
            str(e.exception), "'export_target' not found in spec")

        # what can possibly go wrong?
        spec['export_target'] = join(spec[webpack.webpack_bin_key], 'tail')
        with self.assertRaises(RuntimeError) as e:
            webpack.prepare(spec)
        self.assertEqual(
            str(e.exception), "'export_target' will not be writable")

        spec['export_target'] = join(tmpdir, 'config.js')
        with self.assertRaises(RuntimeError) as e:
            webpack.prepare(spec)
        self.assertEqual(
            str(e.exception), "'export_target' must not be same as "
            "'webpack_config_js'")

    def test_assemble_null(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        spec = Spec(
            # this is not written
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={},
            bundled_modpaths={},
            transpiled_targetpaths={},
            bundled_targetpaths={},
            export_module_names=[],
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)
        webpack.assemble(spec)

        # TODO verify contents
        self.assertTrue(exists(join(tmpdir, '__calmjs_bootstrap__.js')))

        self.assertTrue(exists(join(tmpdir, 'config.js')))
        self.assertEqual(spec[CONFIG_JS_FILES], [join(tmpdir, 'config.js')])

        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))

        self.assertEqual(config_js['output'], {
            "path": tmpdir,
            "filename": "bundle.js",
            "libraryTarget": "umd",
            "umdNamedDefine": True,
        })
        self.assertEqual(config_js['resolve']['alias'], {})
        self.assertEqual(
            config_js['entry'], join(tmpdir, '__calmjs_bootstrap__.js'))

    def test_assemble_explicit_entry(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        spec = Spec(
            # this is not written
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': 'example/module'
            },
            bundled_modpaths={},
            transpiled_targetpaths={
                'example/module': 'example/module.js',
            },
            bundled_targetpaths={},
            export_module_names=[],
            webpack_entry_point='example/module',
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)
        with pretty_logging(stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        target = join(tmpdir, 'example', 'module.js')
        self.assertIn(
            "alias 'example/module' points to '%s' but file does not exist" % (
                target),
            s.getvalue(),
        )

        # no bootstrap module with an explicit entry point
        self.assertFalse(exists(join(tmpdir, '__calmjs_bootstrap__.js')))
        self.assertTrue(exists(join(tmpdir, 'config.js')))
        self.assertEqual(spec[CONFIG_JS_FILES], [join(tmpdir, 'config.js')])

        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))

        self.assertEqual(config_js['output'], {
            "path": tmpdir,
            "filename": "bundle.js",
            "libraryTarget": "umd",
            "umdNamedDefine": True,
        })
        module_fn = join(tmpdir, 'example', 'module.js')
        self.assertEqual(config_js['resolve']['alias'], {
            'example/module': module_fn,
        })
        self.assertEqual(config_js['entry'], module_fn)

    def test_prepare_assemble_standard_calmjs_compat(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        # note that all *_targetpaths are relative to the build dir.
        spec = Spec(
            # export_target will not be written.
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': 'example/module'
            },
            bundled_modpaths={
                'bundled_pkg': 'bundled_pkg',
            },
            transpiled_targetpaths={
                'example/module': 'example/module.js',
            },
            bundled_targetpaths={
                'bundled_pkg': 'bundled_pkg.js',
                # note that this is probably meaningless in the context
                # of webpack.
                'bundled_dir': 'bundled_dir',
            },
            export_module_names=[
                'example/module',
                'bundled_dir',
                'bundled_pkg',
            ],
            # to enable the correct function of the calmjs bootstrap and
            # the loader, this must be explicitly configured as such
            webpack_output_library='__calmjs__',
            # also that the externals _must_ be defined exactly as
            # required
            webpack_externals={'__calmjs__': {
                "root": '__calmjs__',
                "amd": '__calmjs__',
                "commonjs": ['global', '__calmjs__'],
                "commonjs2": ['global', '__calmjs__'],
            }},
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)

        # skip the compile step as those entries are manually applied.
        with pretty_logging(stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        target = join(tmpdir, 'example', 'module.js')
        self.assertIn(
            "alias 'example/module' points to '%s' but file does not exist" % (
                target),
            s.getvalue(),
        )

        self.assertTrue(exists(join(tmpdir, 'config.js')))
        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))
        self.assertEqual(config_js, spec['webpack_config'])

        # the bootstrap is generated and is the entry point.
        calmjs_bootstrap_filename = join(tmpdir, '__calmjs_bootstrap__.js')
        self.assertEqual(config_js['entry'], calmjs_bootstrap_filename)
        self.assertTrue(exists(calmjs_bootstrap_filename))
        # note that the webpack.output.library is as configured
        self.assertEqual('__calmjs__', config_js['output']['library'])

        self.assertEqual(config_js['resolve']['alias'], {
            '__calmjs_loader__': join(tmpdir, '__calmjs_loader__.js'),
            'example/module': join(tmpdir, 'example', 'module.js'),
            'bundled_pkg': join(tmpdir, 'bundled_pkg.js'),
            'bundled_dir': join(tmpdir, 'bundled_dir'),
        })

        with open(config_js['resolve']['alias']['__calmjs_loader__']) as fd:
            calmjs_module = fd.read()
            # should probably use the parser for verification
            self.assertIn('require("example/module")', calmjs_module)
            self.assertIn('calmjs_bootstrap.modules', calmjs_module)

    def test_prepare_assemble_calmjs_bootstrap_explicit(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        # note that all *_targetpaths are relative to the build dir.
        spec = Spec(
            # export_target will not be written.
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': 'example/module'
            },
            bundled_modpaths={
                'bundled_pkg': 'bundled_pkg',
            },
            transpiled_targetpaths={
                'example/module': 'example/module.js',
            },
            bundled_targetpaths={
                'bundled_pkg': 'bundled_pkg.js',
                # note that this is probably meaningless in the context
                # of webpack.
                'bundled_dir': 'bundled_dir',
            },
            export_module_names=[
                'example/module',
                'bundled_dir',
                'bundled_pkg',
            ],
            # note that webpack_output_library is defined to use the
            # complete module without the externals being defined, this
            # will trigger an exception
            webpack_output_library='__calmjs__',
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)
        # skip the compile step as those entries are manually applied.

        with pretty_logging(
                logger='calmjs.webpack', stream=mocks.StringIO()) as s:
            with self.assertRaises(ValueError):
                webpack.assemble(spec)

        self.assertIn(
            "webpack.externals does not have '__calmjs__' defined for "
            "the complete calmjs webpack bootstrap module",
            s.getvalue())
        self.assertIn(
            "aborting export to webpack.output.library as '__calmjs__'",
            s.getvalue())

    def test_prepare_assemble_calmjs_export_only(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        # note that all *_targetpaths are relative to the build dir.
        spec = Spec(
            # export_target will not be written.
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': 'example/module'
            },
            bundled_modpaths={
                'bundled_pkg': 'bundled_pkg',
            },
            transpiled_targetpaths={
                'example/module': 'example/module.js',
            },
            bundled_targetpaths={
                'bundled_pkg': 'bundled_pkg.js',
                # note that this is probably meaningless in the context
                # of webpack.
                'bundled_dir': 'bundled_dir',
            },
            export_module_names=[
                'example/module',
                'bundled_dir',
                'bundled_pkg',
            ],
            webpack_output_library='example',
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)
        # skip the compile step as those entries are manually applied.

        with pretty_logging(logger='calmjs', stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        target = join(tmpdir, 'example', 'module.js')
        self.assertIn(
            "alias 'example/module' points to '%s' but file does not exist" % (
                target),
            s.getvalue(),
        )

        # this is the default, as the above spec does not define this.
        self.assertIn(
            "spec webpack_entry_point defined to be '__calmjs__'",
            s.getvalue())
        # when webpack.output.library is not configured as __calmjs__,
        # this warning is triggered due to how the result may not
        # function as expected.
        self.assertIn(
            "webpack.externals does not have '__calmjs__' defined for "
            "the complete calmjs webpack bootstrap module",
            s.getvalue())

        self.assertTrue(exists(join(tmpdir, 'config.js')))
        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))
        self.assertEqual(config_js, spec['webpack_config'])

        with open(config_js['entry']) as fd:
            self.assertIn('require("example/module")', fd.read())

        self.assertEqual(config_js['resolve']['alias'], {
            # note the lack of __calmjs_loader__
            'example/module': join(tmpdir, 'example', 'module.js'),
            'bundled_pkg': join(tmpdir, 'bundled_pkg.js'),
            'bundled_dir': join(tmpdir, 'bundled_dir'),
        })

        # Also verify the generated __calmjs_bootstrap__ js module,
        # with all the require being dumped here instead of the loader
        # which got disabled.
        with open(join(tmpdir, '__calmjs_bootstrap__.js')) as fd:
            calmjs_module = fd.read()
            # should probably use the parser for verification
            self.assertIn(
                '"example/module": require("example/module")',
                calmjs_module
            )
            self.assertNotIn('calmjs_bootstrap.modules', calmjs_module)

    def test_prepare_assemble_webpack_standard(self):
        tmpdir = utils.mkdtemp(self)

        with open(join(tmpdir, 'webpack'), 'w'):
            # mock a webpack executable.
            pass

        # note that all *_targetpaths are relative to the build dir.
        spec = Spec(
            # export_target will not be written.
            export_target=join(tmpdir, 'bundle.js'),
            build_dir=tmpdir,
            transpiled_modpaths={
                'example/module': 'example/module'
            },
            bundled_modpaths={
                'bundled_pkg': 'bundled_pkg',
            },
            transpiled_targetpaths={
                'example/module': 'example/module.js',
            },
            bundled_targetpaths={
                'bundled_pkg': 'bundled_pkg.js',
                # note that this is probably meaningless in the context
                # of webpack.
                'bundled_dir': 'bundled_dir',
            },
            export_module_names=[
                'example/module',
                'bundled_dir',
                'bundled_pkg',
            ],
            # again, the externals be defined exactly as required
            webpack_externals={
                '__calmjs__': {
                    'root': '__calmjs__',
                    'amd': '__calmjs__',
                    'commonjs': ['global', '__calmjs__'],
                    'commonjs2': ['global', '__calmjs__'],
                },
            },
            # however, this is redefined.
            webpack_output_library='example',
        )

        webpack = toolchain.WebpackToolchain()
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')
        webpack.prepare(spec)
        # skip the compile step as those entries are manually applied.

        with pretty_logging(logger='calmjs', stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        self.assertIn(
            "webpack.externals defined '__calmjs__' with value that enables "
            "the calmjs webpack bootstrap module; generating module "
            "with the complete bootstrap template",
            s.getvalue())
        self.assertIn(
            "exporting complete calmjs bootstrap module with "
            "webpack.output.library as 'example' (expected '__calmjs__')",
            s.getvalue())
        target = join(tmpdir, 'example', 'module.js')
        self.assertIn(
            "alias 'example/module' points to '%s' but file does not exist" % (
                target),
            s.getvalue(),
        )

        self.assertTrue(exists(join(tmpdir, 'config.js')))
        with open(join(tmpdir, 'config.js')) as fd:
            # strip off the header and footer
            config = json.loads(''.join(fd.readlines()[5:-6]))
        self.assertEqual(config, spec['webpack_config'])

        # the bootstrap is generated and is the entry point.
        calmjs_bootstrap_filename = join(tmpdir, '__calmjs_bootstrap__.js')
        self.assertEqual(config['entry'], calmjs_bootstrap_filename)
        self.assertTrue(exists(calmjs_bootstrap_filename))
        # note that the webpack.output.library is as configured
        self.assertEqual('example', config['output']['library'])

        self.assertEqual(config['resolve']['alias'], {
            '__calmjs_loader__': join(tmpdir, '__calmjs_loader__.js'),
            'example/module': join(tmpdir, 'example', 'module.js'),
            'bundled_pkg': join(tmpdir, 'bundled_pkg.js'),
            'bundled_dir': join(tmpdir, 'bundled_dir'),
        })

        with open(config['resolve']['alias']['__calmjs_loader__']) as fd:
            calmjs_module = fd.read()
            # should probably use the parser for verification
            self.assertIn('require("example/module")', calmjs_module)
            self.assertIn('calmjs_bootstrap.modules', calmjs_module)

    def test_assemble_alias_check(self):
        # for the assemble related tests.
        tmpdir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        webpack = toolchain.WebpackToolchain()

        export_target = join(build_dir, 'export.js')
        config_js = join(build_dir, 'config.js')

        with open(join(tmpdir, 'webpack'), 'w'):
            pass

        with open(join(build_dir, 'module1.js'), 'w') as fd:
            fd.write(
                "define(['underscore', 'some.pylike.module'], "
                "function(underscore, module) {"
                "});"
            )

        with open(join(build_dir, 'module2.js'), 'w') as fd:
            fd.write(
                "define(['module1', 'underscore'], "
                "function(module1, underscore) {"
                "});"
            )

        with open(join(build_dir, 'module3.js'), 'w') as fd:
            fd.write(
                "'use strict';\n"
                "var $ = require('jquery');\n"
                "var module2 = require('module2');\n"
            )

        spec = Spec(
            build_dir=build_dir,
            export_target=export_target,
            webpack_config_js=config_js,
            transpiled_modpaths={
                'module1': 'module1',
                'module2': 'module2',
                'module3': 'module3',
            },
            # these are not actually transpiled sources, but will fit
            # with the purposes of this test.
            transpiled_targetpaths={
                'module1': 'module1.js',
                'module2': 'module2.js',
                'module3': 'module3.js',
            },
            # the "bundled" names were specified to be omitted.
            bundled_modpaths={},
            bundled_targetpaths={},
            export_module_names=['module1', 'module2', 'module3'],
        )
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')

        with pretty_logging(
                logger='calmjs.webpack', stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        # the main config file
        # check that they all exists
        self.assertTrue(exists(config_js))

        # TODO use parser to parse this.
        with open(config_js) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))

        self.assertIn('WARNING', s.getvalue())
        self.assertIn(
            "source file(s) referenced modules that are not in alias or "
            "externals: "
            "'jquery', 'some.pylike.module', 'underscore'",
            s.getvalue()
        )

        self.assertEqual(config_js['resolve']['alias'], {
            'module1': join(build_dir, 'module1.js'),
            'module2': join(build_dir, 'module2.js'),
            'module3': join(build_dir, 'module3.js'),
        })

    def test_assemble_alias_check_dynamic(self):
        tmpdir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        webpack = toolchain.WebpackToolchain()

        export_target = join(build_dir, 'export.js')
        config_js = join(build_dir, 'config.js')

        with open(join(tmpdir, 'webpack'), 'w'):
            pass

        with open(join(build_dir, 'some.pylike.module.js'), 'w'):
            pass

        with open(join(build_dir, 'jquery.min.js'), 'w'):
            pass

        with open(join(build_dir, 'underscore.min.js'), 'w'):
            pass

        with open(join(build_dir, 'module1.js'), 'w') as fd:
            fd.write(
                "define(['jquery', 'underscore', 'some.pylike.module'], "
                "function(jquery, underscore, module) {"
                "});"
            )

        with open(join(build_dir, 'module2.js'), 'w') as fd:
            fd.write(
                "define(['module1', 'underscore'], "
                "function(module1, underscore) {"
                "});"
            )

        with open(join(build_dir, 'module3.js'), 'w') as fd:
            fd.write(
                "'use strict';\n"
                "var $ = require('jquery');\n"
                "var _ = require('underscore');\n"
                "var module2 = require('module2');\n"
                "var dymamic = require(dynamic);\n"
            )

        spec = Spec(
            build_dir=build_dir,
            export_target=export_target,
            webpack_config_js=config_js,
            transpiled_modpaths={
                'module1': 'module1',
                'module2': 'module2',
                'module3': 'module3',
                'some.pylike.module': 'some.pylike.module',
            },
            # these are not actually transpiled sources, but will fit
            # with the purposes of this test.
            transpiled_targetpaths={
                'module1': 'module1.js',
                'module2': 'module2.js',
                'module3': 'module3.js',
                'some.pylike.module': 'some.pylike.module.js',
            },
            bundled_modpaths={
                'jquery': 'jquery',
                'underscore': 'underscore',
            },
            bundled_targetpaths={
                'jquery': 'jquery.min.js',
                'underscore': 'underscore.min.js',
            },
            export_module_names=['module1', 'module2', 'module3'],
            webpack_entry_point='__calmjs__',
            webpack_output_library='__calmjs__',
            webpack_externals={'__calmjs__': {
                "root": '__calmjs__',
                "amd": '__calmjs__',
                "commonjs": ['global', '__calmjs__'],
                "commonjs2": ['global', '__calmjs__'],
            }},
        )
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')

        with pretty_logging(
                logger='calmjs.webpack', stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

        # the main config file
        # check that they all exists
        self.assertTrue(exists(config_js))

        # TODO use parser to parse this.
        with open(config_js) as fd:
            # strip off the header and footer
            config_js = json.loads(''.join(fd.readlines()[5:-6]))

        self.assertNotIn('WARNING', s.getvalue())

    def test_assemble_alias_malformed_somehow(self):
        tmpdir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        webpack = toolchain.WebpackToolchain()

        export_target = join(build_dir, 'export.js')
        config_js = join(build_dir, 'config.js')

        with open(join(tmpdir, 'webpack'), 'w'):
            pass

        with open(join(build_dir, 'underscore.js'), 'w') as fd:
            # somehow this is malformed.
            fd.write("function() {});")

        with open(join(build_dir, 'module1.js'), 'w') as fd:
            fd.write("define(['underscore'], function(underscore) {});")

        spec = Spec(
            build_dir=build_dir,
            export_target=export_target,
            webpack_config_js=config_js,
            transpiled_modpaths={
                'module1': 'module1',
            },
            transpiled_targetpaths={
                'module1': 'module1.js',
            },
            bundled_modpaths={
                'underscore': 'underscore',
            },
            bundled_targetpaths={
                'underscore': 'underscore.js',
            },
            export_module_names=['module1'],
        )
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')

        with self.assertRaises(ECMASyntaxError):
            webpack.assemble(spec)

        # the main config file wouldn't be created due to the syntax
        # error.
        self.assertFalse(exists(config_js))

    def test_assemble_alias_malformed_check_skipped(self):
        tmpdir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        webpack = toolchain.WebpackToolchain()

        export_target = join(build_dir, 'export.js')
        config_js = join(build_dir, 'config.js')

        with open(join(tmpdir, 'webpack'), 'w'):
            pass

        with open(join(build_dir, 'underscore.js'), 'w') as fd:
            # somehow this is malformed.
            fd.write("function() {});")

        with open(join(build_dir, 'module1.js'), 'w') as fd:
            fd.write("define(['underscore'], function(underscore) {});")

        spec = Spec(
            build_dir=build_dir,
            export_target=export_target,
            webpack_config_js=config_js,
            transpiled_modpaths={
                'module1': 'module1',
            },
            transpiled_targetpaths={
                'module1': 'module1.js',
            },
            bundled_modpaths={
                'underscore': 'underscore',
            },
            bundled_targetpaths={
                'underscore': 'underscore.js',
            },
            export_module_names=['module1'],
            verify_imports=False,
        )
        spec[webpack.webpack_bin_key] = join(tmpdir, 'webpack')

        with pretty_logging(logger='calmjs.webpack', stream=mocks.StringIO()):
            webpack.assemble(spec)

        # the main config file will be created as the same check that
        # caused the failure will no longer be triggered.
        self.assertTrue(exists(config_js))


class ToolchainCompileLoaderTestCase(unittest.TestCase):
    """
    Test the compile_loaderplugin method and other loader related
    integration.
    """

    def setUp(self):
        self.build_dir = utils.mkdtemp(self)
        # mock the webpack executable
        with open(join(self.build_dir, 'webpack'), 'w'):
            pass

    def test_compile_plugin_base(self):
        working_dir = utils.mkdtemp(self)
        mock_text_loader(working_dir)
        src_dir = utils.mkdtemp(self)
        src = join(src_dir, 'mod.js')

        with open(src, 'w') as fd:
            fd.write('hello world')

        # prepare targets
        target1 = 'mod1.txt'
        target2 = join('namespace', 'mod2.txt')
        target3 = join('nested', 'namespace', 'mod3.txt')
        target4 = 'namespace.mod4.txt'

        webpack = toolchain.WebpackToolchain()
        spec = Spec(**{
            'build_dir': self.build_dir,
            'export_target': join(working_dir, 'export.js'),
            webpack.webpack_bin_key: join(self.build_dir, 'webpack'),
            LOADERPLUGIN_SOURCEPATH_MAPS: {
                'text': {}
            },
            'working_dir': working_dir,
        })
        webpack.prepare(spec)

        self.assertIn('text', spec[WEBPACK_RESOLVELOADER_ALIAS])
        self.assertIn('loaderplugin_sourcepath', spec)

        webpack.compile_loaderplugin_entry(spec, (
            'text!mod1.txt', src, target1, 'mod1'))
        webpack.compile_loaderplugin_entry(spec, (
            'text!namespace/mod2.txt', src, target2, 'mod2'))
        webpack.compile_loaderplugin_entry(spec, (
            'text!nested/namespace/mod3.txt', src, target3, 'mod3'))
        webpack.compile_loaderplugin_entry(spec, (
            'text!namespace.mod4.txt', src, target4, 'mod4'))

        self.assertTrue(exists(join(self.build_dir, target1)))
        self.assertTrue(exists(join(self.build_dir, target2)))
        self.assertTrue(exists(join(self.build_dir, target3)))
        self.assertTrue(exists(join(self.build_dir, target4)))

    def test_prepare_compile_assemble_verify_loaders_checked(self):
        working_dir = utils.mkdtemp(self)
        mock_text_loader(working_dir)
        src_dir = utils.mkdtemp(self)

        index_file = join(src_dir, 'index.js')
        with open(index_file, 'w') as fd:
            fd.write('var hello = require("text!hello/world.txt");\n')

        text_file = join(src_dir, 'hello.txt')
        with open(text_file, 'w') as fd:
            fd.write('hello world')

        webpack = toolchain.WebpackToolchain()
        spec = Spec(**{
            'build_dir': self.build_dir,
            'export_target': join(working_dir, 'export.js'),
            webpack.webpack_bin_key: join(self.build_dir, 'webpack'),
            LOADERPLUGIN_SOURCEPATH_MAPS: {
                'text': {
                    'text!hello/world.txt': text_file,
                }
            },
            'transpile_sourcepath': {
                'index': index_file,
            },
            'working_dir': working_dir,
            'verify_imports': True,
        })

        with pretty_logging(stream=mocks.StringIO()) as s:
            webpack.prepare(spec)
            webpack.compile(spec)
            webpack.assemble(spec)

        self.assertTrue(exists(join(self.build_dir, 'hello', 'world.txt')))
        self.assertNotIn(
            "not in modules: %s" % (['text!hello/world.txt'],), s.getvalue())

    def test_prepare_compile_assemble_verify_loaders_not_found(self):
        working_dir = utils.mkdtemp(self)
        mock_text_loader(working_dir)
        src_dir = utils.mkdtemp(self)

        index_file = join(src_dir, 'index.js')
        with open(index_file, 'w') as fd:
            fd.write('var hello = require("text!hello/world.txt");\n')

        webpack = toolchain.WebpackToolchain()
        spec = Spec(**{
            'build_dir': self.build_dir,
            'export_target': join(working_dir, 'export.js'),
            webpack.webpack_bin_key: join(self.build_dir, 'webpack'),
            LOADERPLUGIN_SOURCEPATH_MAPS: {
            },
            'transpile_sourcepath': {
                'index': index_file,
            },
            'working_dir': working_dir,
            'verify_imports': True,
        })

        with pretty_logging(stream=mocks.StringIO()) as s:
            webpack.prepare(spec)
            webpack.compile(spec)
            webpack.assemble(spec)

        self.assertIn(
            "not in modules: %s" % (['text!hello/world.txt'],), s.getvalue())

    def test_prepare_compile_assemble_verify_loaders_external(self):
        working_dir = utils.mkdtemp(self)
        mock_text_loader(working_dir)
        src_dir = utils.mkdtemp(self)

        index_file = join(src_dir, 'index.js')
        with open(index_file, 'w') as fd:
            fd.write('var hello = require("text!hello/world.txt");\n')

        webpack = toolchain.WebpackToolchain()
        spec = Spec(**{
            'build_dir': self.build_dir,
            'export_target': join(working_dir, 'export.js'),
            webpack.webpack_bin_key: join(self.build_dir, 'webpack'),
            LOADERPLUGIN_SOURCEPATH_MAPS: {
            },
            'transpile_sourcepath': {
                'index': index_file,
            },
            'working_dir': working_dir,
            'verify_imports': True,
            'webpack_externals': {
                'text!hello/world.txt': {'amd': [
                    '__calmjs__', 'modules', 'text!hello/world.txt']}
            },
            'calmjs_loaderplugin_registry': LoaderPluginRegistry(
                'dummy', _working_set=mocks.WorkingSet({})),
        })

        with pretty_logging(stream=mocks.StringIO()) as s:
            webpack.prepare(spec)
            webpack.compile(spec)
            webpack.assemble(spec)

        self.assertNotIn(
            "not in modules: %s" % (['text!hello/world.txt'],), s.getvalue())
