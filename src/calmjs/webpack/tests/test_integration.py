# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import codecs
import json
import os
import sys
from os.path import exists
from os.path import join
from shutil import copytree
from textwrap import dedent

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.cli import node
from calmjs import runtime
from calmjs.utils import pretty_logging
from calmjs.registry import get as get_registry

from calmjs.parse.parsers.es5 import parse
from calmjs.parse.walkers import ReprWalker

try:
    from calmjs.dev import karma
except ImportError:  # pragma: no cover
    karma = None

from calmjs.webpack import toolchain
from calmjs.webpack import cli
from calmjs.webpack import exc
from calmjs.webpack import interrogation
from calmjs.webpack.base import CALMJS_WEBPACK_LOADERPLUGINS

from calmjs.testing import utils
from calmjs.testing.mocks import StringIO

from calmjs.webpack.testing.utils import cls_setup_webpack_example_package
from calmjs.webpack.testing.utils import generate_example_bundles
from calmjs.webpack.testing.utils import skip_full_toolchain_test


def run_node(src, *requires):
    # cross platform node runner with require paths.
    # escape backslashes in require paths.
    return node(dedent(src) % ('\n'.join('require(%s);' % json.dumps(
        r) for r in requires)))


def run_webpack(script, *artifacts):
    # this is rather webpack specific, and here this emulate the global
    # environment within a browser.

    stream = StringIO()
    stream.write("var window = new (function(require, exports, module) {\n")
    for artifact in artifacts:
        with codecs.open(artifact, encoding='utf8') as fd:
            stream.write(fd.read())
    stream.write("})();\n")
    stream.write(dedent(script))
    return node(stream.getvalue())


def _setup_extra_install(working_dir, packages):
    # used for the integration test for the TestCase classes below, and
    # MUST be used after setup_class_install_environment was called.
    if not os.environ.get('CALMJS_TEST_ENV'):  # pragma: no cover
        driver = Driver(working_dir=working_dir)
        driver.pkg_manager_install(packages, production=False, merge=True)


@unittest.skipIf(*skip_full_toolchain_test())
class ToolchainIntegrationTestCase(unittest.TestCase):
    """
    Test out the full toolchain, involving webpack completely.
    """

    # Ensure that webpack is properly installed through the calmjs
    # framework and specification for this package.  This environment
    # will be reused for the duration for this test.

    @classmethod
    def setUpClass(cls):
        # nosetest will still execute setUpClass, so the test condition
        # will need to be checked here also.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        cls._cwd = os.getcwd()

        utils.setup_class_install_environment(
            cls, Driver, ['calmjs.webpack'], production=False)

        # For the duration of this test, operate in the tmpdir where the
        # node_modules are available.
        os.chdir(cls._env_root)

        # This is done after the above, as the setup of the following
        # integration harness will stub out the root distribution which
        # will break the installation of real tools.
        utils.setup_class_integration_environment(cls)
        # also our test data.
        cls_setup_webpack_example_package(cls)
        # plus the extra packages
        _setup_extra_install(cls._cls_tmpdir, ['example.loader'])

        # since our configuration paths will be at arbitrary locations
        # (i.e. temporary directories), NODE_PATH must be defined.

    @classmethod
    def tearDownClass(cls):
        # Ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
        os.chdir(cls._cwd)
        utils.rmtree(cls._cls_tmpdir)

    def setUp(self):
        # Set up the transpiler using env_path assigned in setUpClass,
        # which installed webpack to ensure the tests will find this.
        cli.default_toolchain.env_path = self._env_path
        self._dt_node_path, cli.default_toolchain.node_path = (
            cli.default_toolchain.node_path, join(
                self._env_root, 'node_modules'))

    def tearDown(self):
        # remove registries that got polluted with test data
        from calmjs.registry import _inst as root_registry
        root_registry.records.pop('calmjs.artifacts', None)
        # As the manipulation is done, should set this back to its
        # default state.
        cli.default_toolchain.env_path = None
        cli.default_toolchain.env_path = self._dt_node_path

    # helper to set up "fake_modules" as a mock to "node_modules"
    def setup_runtime_main_env(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        current_dir = utils.mkdtemp(self)
        target_file = join(current_dir, 'bundle.js')

        # invoke installation of "fake_modules"
        copytree(
            join(self.dist_dir, 'fake_modules'),
            join(current_dir, 'fake_modules'),
        )

        return current_dir, target_file

    def test_webpack_toolchain_barebone(self):
        # this is the most barebone, minimum execution with only just
        # the required spec keys.
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_sourcepath = {
            'hello': join(self._ep_root, 'hello.js'),
        }
        bundle_sourcepath = {}
        export_target = join(bundle_dir, 'example.package.js')

        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            transpile_sourcepath=transpile_sourcepath,
            bundle_sourcepath=bundle_sourcepath,
            export_target=export_target,
            build_dir=build_dir,
        )
        webpack(spec)

        self.assertTrue(exists(export_target))

        # automatically generated bootstrap module
        self.assertTrue(exists(join(build_dir, '__calmjs_bootstrap__.js')))

        # only load the webpack through the standard chain; also check
        # that it assigned nothing (root/window should remain unchanged)
        stdout, stderr = run_webpack(
            'console.log(Object.keys(window).length);', export_target)
        self.assertEqual(stderr, '')
        # the entire webpack should have been executed, result in this.
        self.assertEqual(stdout, 'hello\n0\n')

        # likewise for the standard node/commonjs import, that nothing
        # got exported due to how webpack collapse the generation in the
        # umd template for maximum confusion.
        stdout, stderr = run_node("""
        var artifact = %s;
        console.log(Object.keys(artifact).length);
        """, export_target)
        self.assertEqual(stderr, '')
        # the entire webpack should have been executed, result in this.
        self.assertEqual(stdout, 'hello\n0\n')

    def test_webpack_toolchain_barebone_explicit_entry(self):
        # this is one where an explicit entry point be provided,
        # skipping the automatic module generation
        #
        # the required spec keys.
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_sourcepath = {
            'hello': join(self._ep_root, 'hello.js'),
        }
        bundle_sourcepath = {}
        export_target = join(bundle_dir, 'example.package.js')

        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            transpile_sourcepath=transpile_sourcepath,
            bundle_sourcepath=bundle_sourcepath,
            export_target=export_target,
            build_dir=build_dir,
            webpack_entry_point='hello',
        )
        webpack(spec)

        # bootstrap module should not have been generated
        self.assertFalse(exists(join(build_dir, '__calmjs_bootstrap__.js')))

        # the 'hello' text is simply printed through console.log when
        # the artifact is loaded.
        stdout, stderr = run_webpack('', export_target)
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'hello\n')

    def test_webpack_toolchain_standard_output_library(self):
        # standard execution, with an explicitly defined output library
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_sourcepath = {}
        transpile_sourcepath.update(self._example_package_map)
        bundle_sourcepath = {}
        export_target = join(bundle_dir, 'example.package.js')

        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            transpile_sourcepath=transpile_sourcepath,
            bundle_sourcepath=bundle_sourcepath,
            export_target=export_target,
            build_dir=build_dir,
            webpack_output_library='example.package',
        )
        webpack(spec)

        self.assertTrue(exists(export_target))

        # the library is now placed under that name
        stdout, stderr = run_webpack("""
        var modules = window["example.package"].modules;
        var main = modules["example/package/main"];
        main.main();
        """, export_target)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '2\n4\n')

        # the standard require/commonjs loading should work, as it
        # should not have any externals.
        stdout, stderr = run_node("""
        var artifact = %s
        var main = artifact.modules["example/package/main"];
        main.main();
        """, export_target)
        self.assertEqual(stderr, '')
        # the entire webpack should have been executed, result in this.
        self.assertEqual(stdout, '2\n4\n')

    def test_webpack_toolchain_with_bundled(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        # include the custom sources, that has names not connected by
        # main.
        transpile_sourcepath = {
            'example/package/bare': join(self._ep_root, 'bare.js'),
        }
        bundle_sourcepath = {
            'mockquery': join(self._nm_root, 'mockquery.js'),
        }

        transpile_sourcepath.update(self._example_package_map)
        export_target = join(bundle_dir, 'example.package.js')

        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            transpile_sourcepath=transpile_sourcepath,
            bundle_sourcepath=bundle_sourcepath,
            export_target=export_target,
            build_dir=build_dir,
            webpack_output_library='example',
        )
        webpack(spec)

        self.assertTrue(exists(export_target))

        # verify that the bundle works with node, with the usage of the
        # bundle through the __calmjs__ entry module
        stdout, stderr = run_node("""
        var artifact = %s
        var bare = artifact.modules["example/package/bare"];
        console.log(bare.clean(1));
        """, export_target)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '[ 1 ]\n')

    def test_webpack_toolchain_loaderplugin_text(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        loaderplugin_sourcepath_maps = {
            'text': {
                'text!example/loader/single.json': join(
                    self._loaderpkg_root, 'raw.json'),
                # for nested loading
                'text!text!example/loader/double.json': join(
                    self._loaderpkg_root, 'raw.json'),
            }
        }
        export_target = join(bundle_dir, 'example.loader.js')
        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            transpile_sourcepath={},
            bundle_sourcepath={},
            loaderplugin_sourcepath_maps=loaderplugin_sourcepath_maps,
            export_target=export_target,
            build_dir=build_dir,
            webpack_output_library='example.loader',
        )
        with pretty_logging(stream=StringIO()) as stream:
            webpack(spec)

        self.assertIn(
            "AutogenWebpackLoaderPluginRegistry registry "
            "'calmjs.webpack.loaderplugins' generated loader handler 'text'",
            stream.getvalue(),
        )

        self.assertTrue(exists(export_target))

        # verify that the bundle works with node, with the usage of the
        # bundle through the __calmjs__ entry module
        stdout, stderr = run_node("""
        var artifact = %s
        var raw = artifact.modules["text!example/loader/single.json"];
        console.log(raw);
        console.log(artifact.modules["text!text!example/loader/double.json"]);
        """, export_target)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, (
            '{"value": "hello"}\n'
            # second line is wrapped export of that module
            'module.exports = "{\\"value\\": \\"hello\\"}"\n'
        ))

    def test_webpack_toolchain_loaderplugin_text_static(self):
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        loaderplugin_sourcepath_maps = {
            'text': {
                'text!example/loader/single.json': join(
                    self._loaderpkg_root, 'raw.json'),
                # for nested loading
                'text!text!example/loader/double.json': join(
                    self._loaderpkg_root, 'raw.json'),
            }
        }
        export_target = join(bundle_dir, 'example.loader.js')
        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        registry_name = 'calmjs.webpack.static.loaderplugins'
        spec = Spec(
            transpile_sourcepath={},
            bundle_sourcepath={},
            calmjs_loaderplugin_registry_name=registry_name,
            loaderplugin_sourcepath_maps=loaderplugin_sourcepath_maps,
            export_target=export_target,
            build_dir=build_dir,
            webpack_output_library='example.loader',
        )
        with pretty_logging(stream=StringIO()) as stream:
            webpack(spec)

        self.assertIn(
            "using loaderplugin registry "
            "'calmjs.webpack.static.loaderplugins'", stream.getvalue())

        self.assertTrue(exists(export_target))

        # verify that the bundle works with node, with the usage of the
        # bundle through the __calmjs__ entry module
        stdout, stderr = run_node("""
        var artifact = %s
        var raw = artifact.modules["text!example/loader/single.json"];
        console.log(raw);
        console.log(artifact.modules["text!text!example/loader/double.json"]);
        """, export_target)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, (
            '{"value": "hello"}\n'
            # second line is wrapped export of that module
            'module.exports = "{\\"value\\": \\"hello\\"}"\n'
        ))

    def test_webpack_toolchain_dynamic_with_calmjs_various(self):
        # This is still using the WebpackToolchain directly.
        keys, names, prebuilts, contents = generate_example_bundles(self)

        # verify standard bundles working with with the webpack runner.
        for n in ['example_package', 'example_package.min']:
            stdout, stderr = run_webpack("""
            var calmjs = window.__calmjs__;
            var main = calmjs.require("example/package/main");
            main.main();
            """, names[n])
            self.assertEqual(stderr, '')
            self.assertEqual(stdout, '2\n4\n')

        # verify dynamic imports working with the webpack runner.
        for n in ['example_package.extras', 'example_package.extras.min']:
            stdout, stderr = run_webpack("""
            var calmjs = window.__calmjs__;
            var dynamic = calmjs.require("example/package/dynamic");
            console.log(dynamic.check(1, 2));
            """, names[n])
            self.assertEqual(stderr, '')
            self.assertEqual(stdout, '3\n')

        # ensure that the verbose header is present in standard version
        self.assertIn('webpackUniversalModuleDefinition', contents[
            'example_package'])
        self.assertIn('webpackUniversalModuleDefinition', contents[
            'example_package.extras'])
        # ensure that the verbose header isn't present in the minimized
        # version.
        self.assertNotIn('webpackUniversalModuleDefinition', contents[
            'example_package.min'])
        self.assertNotIn('webpackUniversalModuleDefinition', contents[
            'example_package.extras.min'])

        # Finally, since these artifacts are used directly by the
        # interrogation tests, test that the ones store statically match
        # up with the prebuilt ones stored in examples at the source
        # tree level.
        rv = ReprWalker()
        for key in keys:
            with codecs.open(prebuilts[key], encoding='utf8') as fd:
                prebuilt = rv.walk(parse(fd.read()))
                generated = rv.walk(parse(contents[key]))
                self.assertEqual(prebuilt, generated)

    def test_webpack_toolchain_broken_manual_setup(self):
        # this test with a very manual setup, that has the explicit path
        # to the webpack binary defined, but with the location to the
        # node_modules that contain the webpack package not associated
        # with the toolchain such that webpack cannot locate itself
        # under certain circumstances.
        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        transpile_sourcepath = {
            'hello': join(self._ep_root, 'hello.js'),
        }
        bundle_sourcepath = {}
        export_target = join(bundle_dir, 'example.package.js')

        webpack = toolchain.WebpackToolchain(
            node_path=join(self._env_root, 'node_modules'))
        spec = Spec(
            # set the binary first, manually
            webpack_bin=webpack.which_with_node_modules(),
            transpile_sourcepath=transpile_sourcepath,
            bundle_sourcepath=bundle_sourcepath,
            export_target=export_target,
            build_dir=build_dir,
        )

        # ensure that the conditions for which the failure, i.e. no
        # explicit NODE_PATH and that the working_dir is empty (so that
        # the NODE_PATH will not be generated by the WebpackToolchain).
        webpack.node_path = None
        webpack.working_dir = utils.mkdtemp(self)
        with pretty_logging(stream=StringIO()) as s:
            try:
                webpack(spec)
            except exc.WebpackExitError:  # pragma: no cover
                # This may more may not fail, we don't care.
                pass

        log = s.getvalue()
        # we only care about this warning message.
        self.assertIn(
            "no valid node_modules found - webpack may fail to locate itself",
            log)

    # Tests using the Toolchain with the cli abstraction.

    def test_cli_create_spec(self):
        with pretty_logging(stream=StringIO()):
            spec = cli.create_spec(
                ['site'], source_registries=(self.registry_name,))
        self.assertEqual(
            spec['export_target'], join(self._env_root, 'site.js'))

    def test_cli_compile_all_site(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Finally, install dependencies for site in the new directory
        # normally this might be done:
        #
        #     npm = Driver()
        #     npm.npm_install('site', production=True)
        #
        # However, since we have our set of fake_modules, just install
        # by copying the fake_modules dir from dist_dir into the current
        # directory.

        copytree(
            join(self.dist_dir, 'fake_modules'),
            join(working_dir, 'fake_modules'),
        )

        # Trigger the compile using the module level compile function
        spec = cli.compile_all(
            ['site'], source_registries=(self.registry_name,))
        self.assertEqual(
            spec['export_target'], join(working_dir, 'site.js'))

        # verify that the bundle works with node.  First change back to
        # directory with webpack library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var datepicker = calmjs.require("widget/datepicker");
        console.log(datepicker.DatePickerWidget);
        """, spec['export_target'])

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'widget.datepicker.DatePickerWidget\n')

    def test_cli_compile_all_service(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Trigger the compile using the module level compile function,
        # but without bundling
        spec = cli.compile_all(
            ['service'], source_registries=(self.registry_name,),
            bundlepath_method='none',
        )
        self.assertEqual(
            spec['export_target'], join(working_dir, 'service.js'))

        # verify that the bundle works with node.  First change back to
        # directory with webpack library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have, and the __calmjs__ bootstrap be exported onto window.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var rpclib = calmjs.require("service/rpc/lib");
        console.log(rpclib.Library);
        """, spec['export_target'])

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

    def test_cli_compile_all_service_no_calmjs_bootstrap(self):
        # create a new working directory to install our current site
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # Trigger the compile using the module level compile function,
        # but without bundling
        spec = cli.compile_all(
            ['service'], source_registries=(self.registry_name,),
            bundlepath_method='none',
            # Turn the compatibility off.
            calmjs_compat=False,
        )
        self.assertEqual(
            spec['export_target'], join(working_dir, 'service.js'))

        # For proper verification, change back to the environment root.
        os.chdir(self._env_root)

        # The execution should export all the modules to just that
        # target, with modules simply be available at modules.
        stdout, stderr = run_node("""
        var service = %s
        var rpclib = service.modules["service/rpc/lib"];
        console.log(rpclib.Library);
        """, spec['export_target'])

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

        # The module itself should simply be exported as 'service' when
        # and not __calmjs__ when executed within a browser.
        stdout, stderr = run_webpack("""
        var service = window.service;
        var rpclib = service.modules["service/rpc/lib"];
        console.log(rpclib.Library);
        """, spec['export_target'])

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

    def test_cli_compile_explicit_service(self):
        utils.remember_cwd(self)
        working_dir = utils.mkdtemp(self)
        os.chdir(working_dir)

        # first build the service artifact
        spec = cli.compile_all(
            ['service'], source_registries=(self.registry_name,),
            bundlepath_method='none', sourcepath_method='explicit',
            # leave the bootstrap available, as the testing of explicit
            # chaining is being done.
        )
        service_js = join(working_dir, 'service.js')
        self.assertEqual(spec['export_target'], service_js)

        with codecs.open(service_js, encoding='utf8') as fd:
            service_artifact = fd.read()

        self.assertIn('service/rpc/lib', service_artifact)

        # then build the parent, also using the explicit sourcepath
        # method.
        spec = cli.compile_all(
            ['framework'], source_registries=(self.registry_name,),
            bundlepath_method='none', sourcepath_method='explicit',
        )
        framework_js = join(working_dir, 'framework.js')
        self.assertEqual(spec['export_target'], framework_js)

        # The execution cannot follow the standard require format, as
        # the way webpack use/generate the commonjs/commonjs2 format
        # assumes they always operate on filenames.  To get around this,
        # wrap everything in a closure that stubs out module and exports
        # to simulate an environment similar to a browser; for that a
        # dumb naked AMD definition is used without arguments.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var rpclib = calmjs.require("service/rpc/lib");
        console.log(rpclib.Library);
        """, framework_js, service_js)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, 'service.rpc.lib.Library\n')

    def test_cli_compile_explicit_packages(self):
        # have to set up the fake_modules beforehand for the resolution
        # of bundledpaths to work.
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # This test is to ensure that the __calmjs__.modules can be
        # grown over artifact definitions.
        def generate_artifact(package):
            # for this, only the declared bundles will be explicitly
            # added to each module.
            cli.compile_all(
                [package], source_registries=(self.registry_name,),
                bundlepath_method='explicit', sourcepath_method='explicit',
            )
            return join(current_dir, package + '.js')

        # generate all the artifacts
        artifacts = [generate_artifact(n) for n in (
            'framework', 'widget', 'forms', 'service')]

        # just load the first artifact (framework) and check length
        stdout, stderr = run_webpack("""
        for (key in window.__calmjs__.modules) {
            console.log(key);
        }
        console.log(window.__calmjs__.modules.underscore);
        """, artifacts[0])
        self.assertEqual(stderr, '')
        self.assertEqual(stdout.strip(), '\n'.join([
            'framework/lib', 'jquery', 'underscore',

            # the underscore module from framework uses the -min.js
            # version
            'underscore/underscore-min.js'
        ]))

        # now load a further one (plus widget)...
        stdout, stderr = run_webpack("""
        for (key in window.__calmjs__.modules) {
            console.log(key);
        }
        """, artifacts[0], artifacts[1])
        self.assertEqual(stderr, '')
        self.assertEqual(stdout.strip(), '\n'.join([
            # declared in framework
            'framework/lib', 'jquery', 'underscore',
            # declared in widget
            'widget/core', 'widget/datepicker', 'widget/richedit',
        ]))

        # now load the rest, and see that the underscore module be
        # shadowed from the final service artifact
        stdout, stderr = run_webpack("""
        for (key in window.__calmjs__.modules) {
            console.log(key);
        }
        console.log(window.__calmjs__.modules.underscore);
        """, *artifacts)
        self.assertEqual(stderr, '')
        self.assertEqual(stdout.strip(), '\n'.join([
            # declared in framework
            'framework/lib', 'jquery', 'underscore',
            # declared in widget
            'widget/core', 'widget/datepicker', 'widget/richedit',
            # declared in forms
            'forms/ui',
            # declared in service
            'service/endpoint', 'service/rpc/lib',

            # the underscore module is now shadowed by service, which
            # provides the .js instead of -min.js
            'underscore/underscore.js',
        ]))

        # finally, chain all the artifacts together and see that the
        # defined functionality works.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var service = calmjs.require("service/endpoint");
        var rpclib = calmjs.require("service/rpc/lib");
        console.log(rpclib.Library);
        console.log(service.Endpoint);
        """, *artifacts)

        self.assertEqual(stderr, '')
        self.assertEqual(
            stdout, 'service.rpc.lib.Library\nservice.endpoint.Endpoint\n')

    def test_runtime_cli_help_text(self):
        utils.stub_stdouts(self)
        with self.assertRaises(SystemExit) as e:
            runtime.main(['webpack', '-h'])
        self.assertEqual(e.exception.args[0], 0)
        out = ' '.join(i.strip() for i in sys.stdout.getvalue().splitlines())
        self.assertIn(
            '--export-target <export_target> output filename; '
            'defaults to last ${package_name}.js ', out)
        self.assertIn(
            '--working-dir <working_dir> the working directory; '
            'for this tool it will be used as the base directory for '
            'locating the node_modules for the declared bundled source '
            'files, and as the base directory for export_target and '
            'build_dir paths; ', out)
        self.assertIn('default is current working directory', out)

    def test_runtime_cli_compile_explicit_missing(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        widget_js = join(current_dir, 'widget.js')
        # when explicit bundling is none, with how this package is set
        # up without node_modules, webpack will simply treat the import
        # it cannot locate as an error.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'widget',
                '--bundlepath-method=none',
                '--export-target=' + widget_js,
                '--source-registry=' + self.registry_name,
            ])
        # check we have the error codes.
        self.assertEqual(e.exception.args[0], 1)
        self.assertIn(
            'webpack has encountered a fatal error', sys.stderr.getvalue())
        self.assertIn(
            'terminated with exit code', sys.stderr.getvalue())

    def test_runtime_cli_compile_all_service(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'service', 'site',
                '--export-target=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with webpack library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var lib = calmjs.require("framework/lib");
        console.log(lib.Core);
        var datepicker = calmjs.require("widget/datepicker");
        console.log(datepicker.DatePickerWidget);
        var rpclib = calmjs.require("service/rpc/lib");
        console.log(rpclib.Library);
        var jquery = calmjs.require("jquery");
        console.log(jquery);
        var underscore = calmjs.require("underscore");
        console.log(underscore);
        """, target_file)

        self.assertEqual(stderr, '')
        # note the names of the bundled files
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'service.rpc.lib.Library\n'
            'jquery/dist/jquery.js\n'
            'underscore/underscore.js\n'
        ))

    def test_runtime_cli_compile_all_service_cwd(self):
        current_dir, target_file = self.setup_runtime_main_env()

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'site',
                '--export-target=' + target_file,
                '--working-dir=' + current_dir,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with webpack library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var lib = calmjs.require("framework/lib");
        console.log(lib.Core);
        var datepicker = calmjs.require("widget/datepicker");
        console.log(datepicker.DatePickerWidget);
        var jquery = calmjs.require("jquery");
        console.log(jquery);
        var underscore = calmjs.require("underscore");
        console.log(underscore);
        """, target_file)

        self.assertEqual(stderr, '')
        # note the names of the bundled files
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'jquery/dist/jquery.js\n'
            'underscore/underscore.js\n'
        ))

    def test_runtime_cli_compile_framework_simple_invocation(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # Invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'framework',
                '--export-target=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(target_file))

        # verify that the bundle works with node.  First change back to
        # directory with webpack library installed.
        os.chdir(self._env_root)

        # The execution should then work as expected on the bundle we
        # have.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var lib = calmjs.require("framework/lib");
        console.log(lib.Core);
        """, target_file)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
        ))

    def test_runtime_cli_compile_explicit_site(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'site',
                '--sourcepath-method=explicit',
                '--bundlepath-method=none',
                '--export-target=' + target_file,
                '--source-registry=' + self.registry_name,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with codecs.open(target_file, encoding='utf8') as fd:
            contents = fd.read()

        # since the package has no sources along with bundling disabled,
        # an artifact that contains the two generated modules should be
        # generated.
        self.assertEqual(
            contents[:42], '(function webpackUniversalModuleDefinition')
        # note that this test may be fragile and specific to webpack
        # versions.
        # also that the generated module may vary in length during
        # development.
        # self.assertEqual(len(contents), 3362)

    def test_runtime_cli_compile_explicit_registry_site(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # invoke the thing through the main runtime
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'site',
                '--source-registry-method=explicit',
                '--export-target=' + target_file,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with codecs.open(target_file, encoding='utf8') as fd:
            contents = fd.read()

        # as the registry is NOT declared for that package, it should
        # result in nothing.
        self.assertNotIn('framework/lib', contents)
        self.assertIn(
            'no module registry declarations found using packages',
            sys.stderr.getvalue(),
        )
        self.assertIn("'site'", sys.stderr.getvalue())
        self.assertIn(
            "using acquisition method 'explicit'", sys.stderr.getvalue())

    def test_runtime_cli_bundle_method_standard(self):
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_js = join(current_dir, 'widget_standard.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'widget',
                '--build-dir=' + build_dir,
                '--sourcepath-method=all',
                '--bundlepath-method=all',
                '--export-target=' + widget_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the bundled files are copied
        self.assertTrue(exists(join(build_dir, 'underscore.js')))
        # even jquery.min.js is used, it's copied like this due to how
        # modules are renamed.
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_bundle_method_explicit(self):
        utils.stub_stdouts(self)
        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)
        build_dir = utils.mkdtemp(self)
        widget_js = join(current_dir, 'widget_explicit.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'widget',
                '--build-dir=' + build_dir,
                '--sourcepath-method=all',
                '--bundlepath-method=explicit',
                '--export-target=' + widget_js,
            ])
        self.assertEqual(e.exception.args[0], 0)
        # ensure that the explicitly defined bundled files are copied
        self.assertFalse(exists(join(build_dir, 'underscore.js')))
        self.assertTrue(exists(join(build_dir, 'jquery.js')))

    def test_runtime_cli_compile_explicit_service_framework_widget(self):
        def verify(*artifacts):
            os.chdir(self._env_root)
            return run_webpack("""
            var calmjs = window.__calmjs__;
            var lib = calmjs.require("framework/lib");
            console.log(lib.Core);
            var datepicker = calmjs.require("widget/datepicker");
            console.log(datepicker.DatePickerWidget);
            var jquery = calmjs.require("jquery");
            console.log(jquery);
            var underscore = calmjs.require("underscore");
            console.log(underscore);
            """, *artifacts)

        def runtime_main(args, error_code=0):
            # Invoke the thing through the main runtime
            os.chdir(current_dir)
            with self.assertRaises(SystemExit) as e:
                runtime.main(args)
            self.assertEqual(e.exception.args[0], error_code)

        current_dir, target_file = self.setup_runtime_main_env()
        os.chdir(current_dir)

        # stubbing to check for a _lack_ of error message.
        utils.stub_stdouts(self)

        # invoke the thing through the main runtime
        runtime_main([
            'webpack', 'framework', 'forms', 'service',
            '--sourcepath-method=explicit',
            '--export-target=' + target_file,
            '--source-registry=' + self.registry_name,
        ])
        self.assertTrue(exists(target_file))
        # no complaints about missing 'widget/*' modules
        self.assertEqual('', sys.stderr.getvalue())

        # try running it anyway with widget missing...
        stdout, stderr = verify(target_file)
        # this naturally will not work, so the missing module will be in
        # the error
        self.assertIn('widget', stderr)

        # try again, after building the missing widget bundle.
        widget_js = join(current_dir, 'widget.js')
        runtime_main([
            'webpack', 'widget',
            '--export-target=' + widget_js,
            '--source-registry=' + self.registry_name,
        ])
        # no complaints about missing 'framework/lib'
        self.assertEqual('', sys.stderr.getvalue())

        # the execution should now work if the widget bundle is loaded
        # first, and output should be as expected.
        stdout, stderr = verify(widget_js, target_file)
        self.maxDiff = None
        self.assertEqual(stderr, '')
        # note the names of the bundled files
        self.assertEqual(stdout, (
            'framework.lib.Core\n'
            'widget.datepicker.DatePickerWidget\n'
            'jquery/dist/jquery.min.js\n'  # from widget
            # not underscore-min.js from widget because this was bundled
            # in the artifact
            'underscore/underscore.js\n'
        ))

    def test_runtime_example_package_auto_registry(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        with codecs.open(export_target, encoding='utf8') as fd:
            self.assertIn('webpackUniversalModuleDefinition', fd.read())

        # ensure that it runs, too.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var main = calmjs.require("example/package/main");
        main.main();
        """, export_target)
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '2\n4\n')

    def test_runtime_example_package_disable_calmjs_compat(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package',
                '--export-target=' + export_target,
                '--disable-calmjs-compat',
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        with codecs.open(export_target, encoding='utf8') as fd:
            self.assertIn('webpackUniversalModuleDefinition', fd.read())
            self.assertNotIn('__calmjs_loader__', fd.read())
            self.assertNotIn('__calmjs__', fd.read())

        # this will definitely not work
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var main = calmjs.require("example/package/main");
        main.main();
        """, export_target)
        self.assertNotEqual(stderr, '')
        self.assertNotEqual(stdout, '2\n4\n')

        # however, the typical webpack usage may work like so:
        stdout, stderr = node(dedent("""
        var pkg = require('" + export_target + "');
        pkg['modules']['example/package/main'].main();
        """))
        self.assertNotEqual(stderr, '')
        self.assertNotEqual(stdout, '2\n4\n')

    def test_runtime_example_package_manual_webpack_entry(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package',
                '--export-target=' + export_target,
                '--webpack-entry-point', 'example/package/main',
                '--disable-calmjs-compat',
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        with codecs.open(export_target, encoding='utf8') as fd:
            self.assertIn('webpackUniversalModuleDefinition', fd.read())
            self.assertNotIn('__calmjs_loader__', fd.read())
            self.assertNotIn('__calmjs__', fd.read())

        # similar to above, however there are even less layers, and only
        # the specific module (example/package/main) was included.
        stdout, stderr = node(dedent("""
        var main = require('" + export_target + "');
        main.main();
        """))
        self.assertNotEqual(stderr, '')
        self.assertNotEqual(stdout, '2\n4\n')

    def test_runtime_example_package_manual_webpack_entry_bad(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package',
                '--export-target=' + export_target,
                '--webpack-entry-point', 'example/package/notfound',
                '--disable-calmjs-compat',
            ])
        self.assertNotEqual(e.exception.args[0], 0)
        self.assertFalse(exists(export_target))
        self.assertIn(
            "'example/package/notfound' not found in the source alias map",
            sys.stderr.getvalue(),
        )

    def test_runtime_example_package_minimized(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package', '--optimize-minimize',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)

        with codecs.open(export_target, encoding='utf8') as fd:
            self.assertNotIn('webpackUniversalModuleDefinition', fd.read())

        # ensure that it runs, too.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var main = calmjs.require("example/package/main");
        main.main();
        """, export_target)
        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '2\n4\n')

    def test_runtime_example_package_bad_import(self):
        fault_js = join(self._ep_root, 'fault.js')
        with codecs.open(fault_js, 'w', encoding='utf8') as fd:
            fd.write(
                '"use strict";\n'
                'require("no_such_module");\n'
            )

        record = get_registry(self.registry_name).records['example.package']
        self.addCleanup(record.pop, 'example/package/fault')
        record['example/package/fault'] = fault_js

        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 1)

        self.assertIn(
            "WARNING calmjs.webpack.toolchain source file(s) referenced "
            "modules that are not in alias or externals: 'no_such_module'",
            sys.stderr.getvalue()
        )

    def test_runtime_example_package_bad_import_skip_check(self):
        fault_js = join(self._ep_root, 'fault.js')
        with codecs.open(fault_js, 'w', encoding='utf8') as fd:
            fd.write(
                '"use strict";\n'
                'require("no_such_module");\n'
            )

        record = get_registry(self.registry_name).records['example.package']
        self.addCleanup(record.pop, 'example/package/fault')
        record['example/package/fault'] = fault_js

        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package', '--skip-validate-imports',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 1)
        self.assertNotIn("WARNING", sys.stderr.getvalue())
        # because webpack failed.
        self.assertIn("CRITICAL", sys.stderr.getvalue())

    # for asserting that the generated artifacts with the current or
    # newly instantiated environment also can be correctly interrogated.

    def assertPrebuilts(self, answer, results, f, keys):
        for k in keys:
            self.assertEqual(sorted(answer), sorted(f(parse(results[k]))))

    def test_prebuilts(self):
        keys, names, prebuilts, contents = generate_example_bundles(self)

        self.assertPrebuilts([
            'example/package/bad',
            'example/package/main',
            'example/package/math',
        ], contents, interrogation.probe_calmjs_webpack_module_names, [
            'example_package',
            'example_package.min',
        ])

        self.assertPrebuilts([
            'example/package/bare',
            'example/package/bad',
            'example/package/dynamic',
            'example/package/main',
            'example/package/math',
            'mockquery',
        ], contents, interrogation.probe_calmjs_webpack_module_names, [
            'example_package.extras',
            'example_package.extras.min',
        ])

    def test_calmjs_artifact_package_generation(self):
        utils.stub_stdouts(self)
        registry = get_registry('calmjs.artifacts')
        builders = sorted(
            registry.iter_builders_for('example.package'),
            key=lambda builder: str(builder[0])
        )

        self.assertEqual(2, len(builders))

        with self.assertRaises(SystemExit) as e:
            runtime.main(['artifact', 'build', 'example.package'])

        self.assertEqual(e.exception.args[0], 0)

        for e, t, spec in builders:
            self.assertTrue(exists(spec['export_target']))

        with open(builders[0][2]['export_target']) as fd:
            # ex.webpack.js
            self.assertIn('webpackUniversalModuleDefinition', fd.readline())
            # there are more lines.
            self.assertNotEqual('', fd.readline())

        with open(builders[1][2]['export_target']) as fd:
            # ex.webpack.min.js
            self.assertNotIn('webpackUniversalModuleDefinition', fd.readline())
            # assume no source map?  the entire thing is one line
            self.assertEqual('', fd.readline())


@unittest.skipIf(karma is None, 'calmjs.dev or its karma module not available')
class KarmatoolchainIntegrationTestCase(unittest.TestCase):
    """
    Test out the karma toolchain, involving webpack completely along
    with the karma testing framework as defined by calmjs.dev
    """

    @classmethod
    def setUpClass(cls):
        # nosetest will still execute setUpClass, so the test condition
        # will need to be checked here also.
        if karma is None:  # pragma: no cover
            return

        cls._cwd = os.getcwd()

        # preloading the webpack loaderplugin registry before the full
        # integration harness stubs out the root distribution, disabling
        # the entry point for this registry - do note that it will be
        # better to manually set this up where it is applicable.
        get_registry(CALMJS_WEBPACK_LOADERPLUGINS)

        utils.setup_class_install_environment(
            cls, Driver, ['calmjs.webpack', 'calmjs.dev'], production=False)

        # for the duration of this test, operate in the tmpdir where the
        # node_modules are available.
        os.chdir(cls._env_root)

        # this is done after the above, as the setup of the following
        # integration harness will stub out the root distribution which
        # will break the installation of real tools.
        utils.setup_class_integration_environment(cls)
        # also our test data.
        cls_setup_webpack_example_package(cls)
        # plus the extra packages
        _setup_extra_install(cls._cls_tmpdir, ['example.loader'])

    @classmethod
    def tearDownClass(cls):
        # ditto, as per above.
        if skip_full_toolchain_test()[0]:  # pragma: no cover
            return
        utils.teardown_class_integration_environment(cls)
        os.chdir(cls._cwd)
        utils.rmtree(cls._cls_tmpdir)

    def tearDown(self):
        # remove registries that got polluted with test data
        from calmjs.registry import _inst as root_registry
        root_registry.records.pop('calmjs.artifacts', None)
        root_registry.records.pop('calmjs.artifacts.tests', None)

    def test_karma_test_runner_basic(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'webpack', 'example.package',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

    def test_karma_test_runner_coverage(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', '--coverage',
                'webpack', 'example.package',
                '--export-target=' + export_target,
                '--build-dir=' + build_dir,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        # verify that the coverage was recorded only for packge
        coverage_file = join(self._env_root, 'coverage', 'coverage.json')
        with codecs.open(coverage_file, encoding='utf8') as fd:
            coverage = json.load(fd)
        expected = {
            join(build_dir, 'example', 'package', 'main.js'),
            join(build_dir, 'example', 'package', 'bad.js'),
            join(build_dir, 'example', 'package', 'math.js'),
        }
        self.assertEqual(expected, set(coverage.keys()))

    def test_karma_test_runner_coverage_covertests(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', '--coverage', '--cover-test',
                'webpack', 'example.package',
                '--export-target=' + export_target,
                '--build-dir=' + build_dir,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        # verify that the coverage was recorded for test also.
        coverage_file = join(self._env_root, 'coverage', 'coverage.json')
        with codecs.open(coverage_file, encoding='utf8') as fd:
            coverage = json.load(fd)
        expected = {
            join(build_dir, 'example', 'package', 'main.js'),
            join(build_dir, 'example', 'package', 'bad.js'),
            join(build_dir, 'example', 'package', 'math.js'),
            join(self._ep_root, 'tests', 'test_math.js'),
        }
        self.assertEqual(expected, set(coverage.keys()))

    def test_karma_test_runner_dynamic_import_in_tests(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_extras.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'webpack', 'example.extras',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

    def test_karma_test_runner_dynamic_import_in_tests_coverage(self):
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_extras.js')
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', '--coverage', '--cover-test',
                'webpack', 'example.extras',
                '--export-target=' + export_target,
                '--build-dir=' + build_dir,
            ])
        self.assertEqual(e.exception.args[0], 0)
        self.assertTrue(exists(export_target))

        # verify that the coverage was recorded.
        coverage_file = join(self._env_root, 'coverage', 'coverage.json')
        with codecs.open(coverage_file, encoding='utf8') as fd:
            coverage = json.load(fd)
        expected = {
            join(build_dir, 'example', 'package', 'main.js'),
            join(build_dir, 'example', 'package', 'bad.js'),
            join(build_dir, 'example', 'package', 'math.js'),
            # directly supplied like previous
            join(self._ep_extras, 'tests', 'test_hello.js'),
            # transpiled to build_dir
            join(build_dir, 'example', 'extras', 'tests', 'test_dyna_math.js'),
        }
        self.assertEqual(expected, set(coverage.keys()))

    def test_karma_test_runner_standalone_artifact(self):
        """
        what's the purpose of tests if they can't be executed any time,
        anywhere, against anything?
        """

        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_package.js')
        # first, generate our bundle.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.package', '--export-target',
                export_target])
        self.assertTrue(exists(export_target))

        # leverage the karma run command to run the tests provided by
        # the example.package against the resulting artifact.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'run',
                '--test-with-package', 'example.package',
                # TODO make this argument optional
                '--test-registry', self.registry_name + '.tests',
                '--artifact', export_target,
                # this is critical
                '--toolchain-package', 'calmjs.webpack',
            ])
        # tests should pass against the resultant bundle
        self.assertEqual(e.exception.args[0], 0)

    def test_karma_test_runner_dynamic_import_in_tests_for_artifacts(self):
        # likewise for above, except this time there is a dynamic
        # import
        utils.stub_stdouts(self)
        current_dir = utils.mkdtemp(self)
        export_target = join(current_dir, 'example_extras.js')
        # build the artifact first
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'webpack', 'example.extras',
                '--export-target=' + export_target,
            ])
        self.assertEqual(e.exception.args[0], 0)

        # use karma run to verify that the standalone test works.
        with self.assertRaises(SystemExit) as e:
            runtime.main([
                'karma', 'run',
                '--artifact=' + export_target,
                '-t', 'calmjs.webpack',
                'example.extras',
            ])
        self.assertEqual(e.exception.args[0], 0)

    def test_calmjs_artifact_test_verification(self):
        utils.stub_stdouts(self)
        artifact_path = join(
            self.dist_dir, 'example.package-1.0.egg-info', 'calmjs_artifacts',
            'ex.webpack.js',
        )

        def clean_artifact():
            if exists(artifact_path):
                os.unlink(artifact_path)

        self.addCleanup(clean_artifact)

        with self.assertRaises(SystemExit) as e:
            runtime.main(['artifact', 'karma', 'example.package'])
        # artifacts haven't been built yet?
        self.assertFalse(exists(artifact_path))
        self.assertEqual(e.exception.args[0], 1)

        # so build the artifacts
        with self.assertRaises(SystemExit) as e:
            runtime.main(['artifact', 'build', 'example.package'])
        self.assertEqual(e.exception.args[0], 0)

        # should pass
        with self.assertRaises(SystemExit) as e:
            runtime.main(['artifact', 'karma', 'example.package'])
        self.assertEqual(e.exception.args[0], 0)

        with open(artifact_path, 'w') as fd:
            fd.write('// this should break the test.')

        # should fail again since the artifact is invalid
        with self.assertRaises(SystemExit) as e:
            runtime.main(['artifact', 'karma', 'example.package'])
        self.assertEqual(e.exception.args[0], 1)
