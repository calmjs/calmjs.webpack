# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
from os.path import exists
from os.path import join

from calmjs.utils import pretty_logging
from calmjs.toolchain import Spec
from calmjs.toolchain import CONFIG_JS_FILES
from calmjs.npm import get_npm_version

from calmjs.webpack import toolchain

from calmjs.testing import utils
from calmjs.testing import mocks


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
        spec = Spec(webpack_bin='/no/such/path')
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
        webpack.assemble(spec)

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
        webpack.assemble(spec)

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

        with pretty_logging(
                logger='calmjs.webpack', stream=mocks.StringIO()) as s:
            webpack.assemble(spec)

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

        with pretty_logging(
                logger='calmjs.webpack', stream=mocks.StringIO()) as s:
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
        self.assertEqual('example', config_js['output']['library'])

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
