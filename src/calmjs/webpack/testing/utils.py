# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import codecs
import os
import json
from os import makedirs
from os.path import join

from pkg_resources import get_distribution
from pkg_resources import resource_filename

from calmjs.registry import get as get_registry
from calmjs.testing import utils
from calmjs.npm import get_npm_version


def skip_full_toolchain_test():  # pragma: no cover
    if get_npm_version() is None:
        return (True, 'npm not available')
    if os.environ.get('SKIP_FULL'):
        return (True, 'skipping due to SKIP_FULL environment variable')
    return (False, '')


def create_mock_npm_package(
        working_dir, package_name, entry_point, version='0.0.1'):
    module_root = join(working_dir, 'node_modules', package_name)
    module_cfg = join(module_root, 'package.json')
    module_src = join(module_root, entry_point)

    os.makedirs(module_root)
    with open(module_cfg, 'w') as fd:
        json.dump({
            "name": package_name,
            "version": version,
            "main": entry_point,
        }, fd)

    with open(module_src, 'w') as fd:
        fd.write("(function(){})();")

    return module_src


def cls_setup_webpack_loader_integration_packages(cls):
    # cls.dist_dir created by setup_class_integration_environment
    cls._es_root = join(cls.dist_dir, 'example', 'styledemo')
    # make the testdir also
    makedirs(join(cls._es_root, 'tests'))

    # TODO should move this to a different function
    utils.make_dummy_dist(None, (
        ('entry_points.txt', '\n'.join([
            '[calmjs.registry]',
            cls.registry_name + '.webpackloader = ' +
            'calmjs.webpack.loaderplugin:WebpackModuleLoaderRegistry',

            cls.registry_name + '.tests.webpackloader = ' +
            'calmjs.webpack.loaderplugin:WebpackModuleLoaderRegistry',

        ])),
    ), 'calmjs.webpack.simulated', '420', working_dir=cls.dist_dir)

    index_js = join(cls._es_root, 'index.js')
    with open(index_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'require("example/styledemo/index.css")\n'
            '\n'
            'exports.toast = function(msg) {\n'
            '    console.log("popped some toasted messages");\n'
            '    return msg;\n'
            '};\n'
        )

    # definitely need to also pass this through karma integration tests
    # as the module.rules may conflict, and that ensure the css files do
    # NOT get further rules applied for coverage reporting as that can
    # complicate things.
    test_index_js = join(cls._es_root, 'tests', 'test_index.js')
    with open(test_index_js, 'w') as fd:
        # TODO include a test on application of stylesheet?
        fd.write(
            '"use strict";\n'
            '\n'
            'var styledemo = require("example/styledemo/index");\n'
            'var text = require("example/styledemo/tests/hello.txt");\n'
            '\n'
            'describe("styling test cases", function() {\n'
            '    afterEach(function() {\n'
            '        document.body.innerHTML = ""\n'
            '    });\n'
            '\n'
            '    it("we got toast", function() {\n'
            '        expect(styledemo.toast("toast")).equal("toast");\n'
            '    });\n'
            '\n'
            '    it("text is hello", function() {\n'
            '        expect(text).equal("hello world");\n'
            '    });\n'
            '\n'
            '    it("styles are available", function() {\n'
            '        document.body.innerHTML = \'<div id="root"></div>\';\n'
            '        var element = document.getElementById("root");\n'
            '        element.setAttribute("class", "body");\n'
            '        var style = window.getComputedStyle(element);\n'
            '        expect(style.getPropertyValue(\n'
            '            "background-color")).equal("rgb(204, 204, 204)");\n'
            '        element.setAttribute("class", "div");\n'
            '        var style = window.getComputedStyle(element);\n'
            '        expect(style.getPropertyValue(\n'
            '            "background-color")).equal("rgb(238, 238, 238)");\n'
            '    });\n'
            '});\n'
        )

    index_css = join(cls._es_root, 'index.css')
    with open(index_css, 'w') as fd:
        fd.write(
            "@import url('example/styledemo/extra.css');\n"
            '\n'
            '.body { background: #ccc; }\n'
            '.div { background: #eee; }\n'
        )

    extra_css = join(cls._es_root, 'extra.css')
    with open(extra_css, 'w') as fd:
        fd.write(
            '.table { border: 1px solid #000; }\n'
            '.tr { border: 1px solid #f00; }\n'
        )

    with open(join(cls._es_root, 'tests', 'hello.txt'), 'w') as fd:
        fd.write('hello world')

    # tie everything together with the webpackloader registry
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('package.json', json.dumps({
            'dependencies': {
                'style-loader': '~0.21.0',
                'css-loader': '~0.28.11',
            },
            'devDependencies': {
                'text-loader': '~0.0.1',
            },
        })),
        ('calmjs_module_registry.txt', '\n'.join([
            cls.registry_name,
            # note that this may become optionally specified, perhaps
            # remove it when that time comes.
            # TODO remove when implied subregistries is implemented
            cls.registry_name + '.webpackloader',
        ])),
        # throw in some .tests.webpackloader under the tests too?
        # or also .tests.loader
        ('entry_points.txt', (
            '[{0}]\n'
            'example.styledemo = example.styledemo\n'
            '[{0}.tests]\n'
            'example.styledemo.tests = example.styledemo.tests\n'
            '[{0}.webpackloader]\n'
            'style!css = stylesheets[css]\n'
            '[{0}.tests.webpackloader]\n'
            'text-loader = text[txt]\n'.format(cls.registry_name)
        )),
    ), 'example.styledemo', '1.0', working_dir=cls.dist_dir)

    # re-add dist_dir to working set
    cls.working_set.add_entry(cls.dist_dir)

    utils.instantiate_integration_registries(
        cls.working_set, cls.root_registry,
        cls.registry_name,
        cls.registry_name + '.tests',
        cls.registry_name + '.webpackloader',
        cls.registry_name + '.tests.webpackloader',
    )


def cls_setup_webpack_example_package(cls):

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
            '[calmjs.artifacts]\n'
            'ex.webpack.js = calmjs.webpack.artifact:complete_webpack\n'
            'ex.webpack.min.js = calmjs.webpack.artifact:optimize_webpack\n'
            '[calmjs.artifacts.tests]\n'
            'ex.webpack.js = calmjs.webpack.artifact:test_complete_webpack\n'
            # no separate builder for testing optimize_webpack as there
            # should be no difference.
            'ex.webpack.min.js = calmjs.webpack.artifact:test_complete_webpack'
            '\n'
            '[%s]\n'
            'example.package = example.package\n'
            '[%s.tests]\n'
            'example.package.tests = example.package.tests\n' % (
                cls.registry_name,
                cls.registry_name,
            )
        )),
    ), 'example.package', '1.0', working_dir=cls.dist_dir)

    # create a separate package that contains extra features.

    cls._ep_extras = join(cls.dist_dir, 'example', 'extras')
    makedirs(cls._ep_extras)
    makedirs(join(cls._ep_extras, 'tests'))

    # for testing loading of data provided by a test
    hello_txt = join(cls._ep_extras, 'tests', 'hello.txt')
    with open(hello_txt, 'w') as fd:
        fd.write("hello world")

    # for testing of loader module integration.
    test_hello_txt_js = join(cls._ep_extras, 'tests', 'test_hello.js')
    with open(test_hello_txt_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            '\n'
            'describe("importing test data", function() {\n'
            '    var hello = require("text!example/extras/tests/hello.txt");\n'
            '    it("test text loaded", function() {\n'
            '        expect(hello).equal("hello world");\n'
            '    });\n'
            '\n'
            '    it("all text loaded", function() {\n'
            '        var mod = require("text!example/extras/hello.txt");\n'
            '        expect(hello).equal(mod);\n'
            '    });\n'
            '\n'
            '});\n'
        )

    # for testing dynamic loading
    test_dyna_math_js = join(cls._ep_extras, 'tests', 'test_dyna_math.js')
    with open(test_dyna_math_js, 'w') as fd:
        fd.write(
            '"use strict";\n'
            '\n'
            'var module_name = "example/package/math";\n'
            'var math = require(module_name);\n'
            '\n'
            'describe("trying out dynamic import", function() {\n'
            '    it("addition", function() {\n'
            '        expect(math.add(3, 4)).equal(7);\n'
            '        expect(math.add(5, 6)).equal(11);\n'
            '    });\n'
            '\n'
            '});\n'
        )

    utils.make_dummy_dist(None, (
        ('requires.txt', 'example.package'),
        ('entry_points.txt', (
            '[%s]\n'
            'example.extras = example.extras\n'
            '[%s.tests]\n'
            'example.extras.tests = example.extras.tests\n' % (
                cls.registry_name,
                cls.registry_name,
            )
        )),
    ), 'example.extras', '1.0', working_dir=cls.dist_dir)

    # webpack loaders setup/data

    cls._loaderpkg_root = join(cls.dist_dir, 'example', 'loader')
    makedirs(cls._loaderpkg_root)
    json_data = join(cls._loaderpkg_root, 'raw.json')
    with open(json_data, 'w') as fd:
        fd.write('{"value": "hello"}')

    # create a mock distribution for loaderplugins integration with
    # various webpack loaders
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('calmjs_module_registry.txt', cls.registry_name),
        ('package.json', json.dumps({
            'dependencies': {
                'text-loader': '~0.0.1',
            },
        })),
        ('entry_points.txt', (
            '[%s]\n'
            'example.loader = example.loader\n' % (
                cls.registry_name,
            )
        )),
    ), 'example.loader', '1.0', working_dir=cls.dist_dir)

    # finally, include the entry_point information for calmjs.webpack
    # to ensure correct function of certain default registries.
    utils.make_dummy_dist(None, (
        ('requires.txt', ''),
        ('entry_points.txt', (
            get_distribution('calmjs.webpack').get_metadata('entry_points.txt')
        )),
    ), 'calmjs.webpack', '0.0', working_dir=cls.dist_dir)

    # re-add it again
    cls.working_set.add_entry(cls.dist_dir)

    # Under typical circumstances, we can do this
    # utils.instantiate_integration_registries(
    #     cls.working_set, cls.root_registry,
    #     cls.registry_name,
    #     cls.registry_name + '.tests',
    # )
    # However, we have existing sources that are to be omitted under
    # most typical tests, hence a manual approach is done.

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

    # for extras
    registry.package_module_map['example.extras'] = ['example.extras']
    registry.records['example.extras'] = {
        'text!example/extras/hello.txt': hello_txt,
    }
    test_registry.records['example.extras.tests'] = {
        'example/extras/tests/test_dyna_math': test_dyna_math_js,
        'example/extras/tests/test_hello_txt': test_hello_txt_js,
        'text!example/extras/tests/hello.txt': hello_txt,
    }
    test_registry.package_module_map['example.extras'] = [
        'example.extras.tests']


def generate_example_bundles(cls):
    """
    This helper generates the standard example set of bundles found
    under the examples directory, using the data set up through the
    previous function.

    Arguments:

    cls
        The TestCase object with both setup_class_install_environment
        and setup_class_integration_environment called from the calmjs
        testing utils
    """

    from calmjs.toolchain import Spec
    from calmjs.webpack.toolchain import WebpackToolchain

    build_dir = utils.mkdtemp(cls)
    bundle_dir = utils.mkdtemp(cls)
    webpack = WebpackToolchain(node_path=join(cls._env_root, 'node_modules'))

    # build the initial data in an incremental manner
    transpile_sourcepath = {}
    bundle_sourcepath = {}
    base_spec = dict(
        transpile_sourcepath=transpile_sourcepath,
        bundle_sourcepath=bundle_sourcepath,
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
    keys = [
        'example_package', 'example_package.extras',
        'example_package.min', 'example_package.extras.min',
    ]
    names = {n: join(bundle_dir, n + '.js') for n in keys}
    # for later verification
    examples = resource_filename('calmjs.webpack.testing', 'examples')
    prebuilts = {n: join(examples, n + '.js') for n in keys}

    # first test, build just the example_package.
    transpile_sourcepath.update(cls._example_package_map)

    base_spec['webpack_optimize_minimize'] = False
    base_spec['export_target'] = names['example_package']
    webpack(Spec(**base_spec))

    base_spec['webpack_optimize_minimize'] = True
    base_spec['export_target'] = names['example_package.min']
    webpack(Spec(**base_spec))

    # test again to include the custom sources with names not
    # connected by main, for the dynamic import from within
    transpile_sourcepath.update({
        'example/package/bare': join(cls._ep_root, 'bare.js'),
        'example/package/dynamic': join(cls._ep_root, 'dynamic.js'),
    })
    bundle_sourcepath.update({
        'mockquery': join(cls._nm_root, 'mockquery.js'),
    })

    base_spec['webpack_optimize_minimize'] = False
    base_spec['export_target'] = names['example_package.extras']
    webpack(Spec(**base_spec))

    base_spec['webpack_optimize_minimize'] = True
    base_spec['export_target'] = names['example_package.extras.min']
    webpack(Spec(**base_spec))

    contents = {}
    for key, path in names.items():
        with codecs.open(path, encoding='utf8') as fd:
            contents[key] = fd.read()

    return keys, names, prebuilts, contents
