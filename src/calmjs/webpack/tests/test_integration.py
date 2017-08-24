# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import json
import os
import sys
from os import makedirs
from os.path import exists
from os.path import join
from shutil import copytree
from textwrap import dedent

from pkg_resources import get_distribution

from calmjs.toolchain import Spec
from calmjs.npm import Driver
from calmjs.npm import get_npm_version
from calmjs.cli import node
from calmjs import runtime
from calmjs.registry import get as get_registry
from calmjs.utils import pretty_logging

from calmjs.webpack import toolchain
from calmjs.webpack import cli

from calmjs.testing import utils
from calmjs.testing.mocks import StringIO


def skip_full_toolchain_test():  # pragma: no cover
    if get_npm_version() is None:
        return (True, 'npm not available')
    if os.environ.get('SKIP_FULL'):
        return (True, 'skipping due to SKIP_FULL environment variable')
    return (False, '')


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
        with open(artifact) as fd:
            stream.write(fd.read())
    stream.write("})();\n")
    stream.write(dedent(script))
    return node(stream.getvalue())


def cls_setup_webpack_example_package(cls):
    from calmjs import dist as calmjs_dist

    # cls.dist_dir created by setup_class_integration_environment
    cls._ep_root = join(cls.dist_dir, 'example', 'package')
    makedirs(cls._ep_root)

    # fake node_modules for transpiled sources
    cls._nm_root = join(cls.dist_dir, 'fake_modules')

    test_root = join(cls._ep_root, 'tests')
    makedirs(test_root)

    math_js = join(cls._ep_root, 'math.js')
    with open(math_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'exports.add = function(x, y) {\n'
            '    return x + y;\n'
            '};\n'
            '\n'
            'exports.mul = function(x, y) {\n'
            '    return x * y;\n'
            '};\n'
        )

    bad_js = join(cls._ep_root, 'bad.js')
    with open(bad_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            '\n'
            '\n'
            'var die = function() {\n'
            '    return notdefinedsymbol;\n'
            '};\n'
            '\n'
            'exports.die = die;\n'
        )

    # TODO derive this (line, col) from the above
    cls._bad_notdefinedsymbol = (6, 12)

    # a dummy "node" module
    mockquery = join(cls._nm_root, 'mockquery.js')
    with open(mockquery, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'exports.mq = function(arg) {\n'
            '    return [arg];\n'
            '};\n'
        )

    # a module that slurps in a transpiled module
    bare_js = join(cls._ep_root, 'bare.js')
    with open(bare_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var $ = require("mockquery").mq;\n'
            'exports.clean = function(arg) {\n'
            '    return $(arg);\n'
            '};\n'
        )

    # a module that simply prints hello
    hello_js = join(cls._ep_root, 'hello.js')
    with open(hello_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'console.log("hello");\n'
        )

    # a module with dynamic require
    dynamic_js = join(cls._ep_root, 'dynamic.js')
    with open(dynamic_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'exports.check = function(arg, arg2) {\n'
            '    var mockquery_name = "mockquery";\n'
            '    var math_name = "example/package/math";\n'
            '    var mq = require(mockquery_name).mq;\n'
            '    var math = require(math_name);\n'
            '    return math.add(mq(arg)[0], mq(arg2)[0]);\n'
            '};\n'
        )

    # a module with dynamic require on the top level which will error.
    top_dynamic_js = join(cls._ep_root, 'top_dynamic.js')
    with open(top_dynamic_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var mockquery_name = "mockquery";\n'
            'var math_name = "math";\n'
            'var mq = require(mockquery_name).mq;\n'
            'var math = require(math_name);\n'
            'exports.check = function(arg, arg2) {\n'
            '    return math.add(mq(arg)[0], mq(arg2)[0]);\n'
            '};\n'
        )

    main_js = join(cls._ep_root, 'main.js')
    with open(main_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var math = require("example/package/math");\n'
            'var bad = require("example/package/bad");\n'
            '\n'
            'var main = function(trigger) {\n'
            '    console.log(math.add(1, 1));\n'
            '    console.log(math.mul(2, 2));\n'
            '    if (trigger === true) {\n'
            '        bad.die();\n'
            '    }\n'
            '};\n'
            '\n'
            'exports.main = main;\n'
        )

    # JavaScript import/module names to filesystem path.
    # Normally, these are supplied through the calmjs setuptools
    # integration framework.
    cls._example_package_map = {
        'example/package/math': math_js,
        'example/package/bad': bad_js,
        'example/package/main': main_js,
    }

    test_math_js = join(cls._ep_root, 'tests', 'test_math.js')
    with open(test_math_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var math = require("example/package/math");\n'
            '\n'
            'describe("basic math functions", function() {\n'
            '    it("addition", function() {\n'
            '        expect(math.add(3, 4)).equal(7);\n'
            '        expect(math.add(5, 6)).equal(11);\n'
            '    });\n'
            '\n'
            '    it("multiplication", function() {\n'
            '        expect(math.mul(3, 4)).equal(12);\n'
            '        expect(math.mul(5, 6)).equal(30);\n'
            '    });\n'
            '});\n'
        )

    # map for our one and only test
    cls._example_package_test_map = {
        'example/package/tests/test_math': test_math_js,
    }

    # also add a proper mock distribution for this.
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('calmjs_module_registry.txt', cls.registry_name),
        ('entry_points.txt', (
            '[%s]\n'
            'example.package = example.package\n'
            '[%s.tests]\n'
            'example.package = example.package.tests\n' % (
                cls.registry_name,
                cls.registry_name,
            )
        )),
    ), 'example.package', '1.0', working_dir=cls.dist_dir)

    # also include the entry_point information for this package
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('entry_points.txt', (
            get_distribution('calmjs.webpack').get_metadata('entry_points.txt')
        )),
    ), 'calmjs.webpack', '0.0', working_dir=cls.dist_dir)

    # re-add it again
    calmjs_dist.default_working_set.add_entry(cls.dist_dir)
    # TODO produce package_module_map

    registry = get_registry(cls.registry_name)
    record = registry.records['example.package'] = {}
    # loader note included
    record.update(cls._example_package_map)
    registry.package_module_map['example.package'] = ['example.package']

    test_registry = get_registry(cls.registry_name + '.tests')
    test_record = test_registry.records['example.package.tests'] = {}
    test_record.update(cls._example_package_test_map)
    test_registry.package_module_map['example.package'] = [
        'example.package.tests']


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

        # XXX TODO make this also the minified version and verify that
        # the extractor can extract the names.

    def test_webpack_toolchain_dynamic_with_calmjs(self):
        # Test that dynamic imports will be transpiled and work through
        # the injected calmjs system

        bundle_dir = utils.mkdtemp(self)
        build_dir = utils.mkdtemp(self)
        # include the custom sources, that has names not connected by
        # main.
        transpile_sourcepath = {
            'example/package/bare': join(self._ep_root, 'bare.js'),
            'example/package/dynamic': join(self._ep_root, 'dynamic.js'),
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
            # must use the explicit settings
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
        webpack(spec)
        self.assertTrue(exists(export_target))

        # verify that the bundle works with with the webpack runner.
        stdout, stderr = run_webpack("""
        var calmjs = window.__calmjs__;
        var dynamic = calmjs.require("example/package/dynamic");
        console.log(dynamic.check(1, 2));
        """, export_target)

        self.assertEqual(stderr, '')
        self.assertEqual(stdout, '3\n')

    def test_cli_create_spec(self):
        with pretty_logging(stream=StringIO()):
            spec = cli.create_spec(
                ['site'], source_registries=(self.registry_name,))
        self.assertEqual(spec['export_target'], 'site.js')

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

        with open(service_js) as fd:
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
            'widget/core', 'widget/richedit', 'widget/datepicker',
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
            'widget/core', 'widget/richedit', 'widget/datepicker',
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
            '--export-target EXPORT_TARGET output filename; '
            'defaults to last ${package_name}.js ', out)
        self.assertIn(
            '--working-dir WORKING_DIR the working directory; '
            'for this tool it will be used as the base directory to '
            'find source files declared for bundling; ', out)
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

        with open(target_file) as fd:
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

        with open(target_file) as fd:
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
