# -*- coding: utf-8 -*-
import unittest
from os.path import dirname
from os.path import join
from os import makedirs
from textwrap import dedent

try:
    import builtins
except ImportError:  # pragma: no cover
    # python 2
    import __builtin__ as builtins

try:
    from calmjs.dev import karma
except ImportError:  # pragma: no cover
    karma = None

from calmjs.exc import ToolchainAbort
from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging
from calmjs.webpack import dev
from calmjs.webpack.dev import karma_webpack

from calmjs.testing.mocks import StringIO
from calmjs.testing.utils import mkdtemp
from calmjs.testing.utils import stub_item_attr_value


class KarmaAbsentTestCase(unittest.TestCase):
    """
    Test the injection of webpack specific advices into the karma
    test runner setup runtime.
    """

    def test_no_calmjs_dev(self):
        __import__ = builtins.__import__

        def import_(name, *a, **kw):
            if name == 'calmjs.dev':
                raise ImportError("No module named 'calmjs.dev'")
            return __import__(name, *a, **kw)

        stub_item_attr_value(self, builtins, '__import__', import_)
        spec = Spec()

        # just to cover the fake import above
        from calmjs.toolchain import Spec as Spec_
        self.assertIs(Spec, Spec_)

        with pretty_logging(stream=StringIO()) as s:
            karma_webpack(spec)

        self.assertNotIn('karma_config', spec)
        self.assertIn(
            "package 'calmjs.dev' not available; cannot apply webpack",
            s.getvalue(),
        )


@unittest.skipIf(karma is None, 'calmjs.dev or its karma module not available')
class KarmaTestcase(unittest.TestCase):

    def test_coverage_generation_empty(self):
        self.assertIsNone(dev._generate_coverage_loader(None, Spec()))

    def test_coverage_generation_targets(self):
        spec = Spec(test_covered_test_paths=[
            'some/test/file',
            'some/other/file',
        ])
        loader = dev._generate_coverage_loader(None, spec)
        self.assertEqual({
            "loader": "sourcemap-istanbul-instrumenter-loader",
            "include": ['some/test/file', 'some/other/file'],
        }, loader)

    def test_coverage_generation_build_dir(self):
        spec = Spec(
            build_dir=mkdtemp(self),
            test_covered_build_dir_paths=['afile.js'],
        )
        loader = dev._generate_coverage_loader(None, spec)
        self.assertTrue(loader['include'][0].startswith(spec['build_dir']))
        self.assertTrue(loader['include'][0].endswith('afile.js'))

    def test_coverage_generation_all(self):
        spec = Spec(
            build_dir=mkdtemp(self),
            test_covered_build_dir_paths=['afile.js'],
            test_covered_test_paths=['some/test/file'],
        )
        loader = dev._generate_coverage_loader(None, spec)
        self.assertEqual({
            "loader": "sourcemap-istanbul-instrumenter-loader",
            "include": ['some/test/file', join(spec['build_dir'], 'afile.js')],
        }, loader)

    def test_apply_coverage_required_missing(self):
        spec = Spec(
            build_dir=mkdtemp(self),
            test_covered_build_dir_paths=['afile.js'],
            test_covered_test_paths=['some/test/file'],
        )
        with self.assertRaises(KeyError):
            dev._apply_coverage(None, spec)

    def test_apply_coverage_standard(self):
        spec = Spec(
            karma_config={
                'webpack': {},
            },
            build_dir=mkdtemp(self),
            test_covered_build_dir_paths=['afile.js'],
            test_covered_test_paths=['some/test/file'],
        )
        dev._apply_coverage(None, spec)

        self.assertEqual({
            "module": {"loaders": [{
                "loader": "sourcemap-istanbul-instrumenter-loader",
                "include": [
                    'some/test/file', join(spec['build_dir'], 'afile.js')
                ],
            }]},
        }, spec['karma_config']['webpack'])

    def test_apply_coverage_join(self):
        spec = Spec(
            karma_config={
                'webpack': {
                    'module': {
                        'rules': [],
                        'loaders': [
                            {'loader': 'demo-loader'}
                        ],
                    },
                },
            },
            build_dir=mkdtemp(self),
            test_covered_build_dir_paths=['afile.js'],
            test_covered_test_paths=['some/test/file'],
        )
        dev._apply_coverage(None, spec)

        self.assertEqual({
            "module": {'rules': [], "loaders": [{'loader': 'demo-loader'}, {
                "loader": "sourcemap-istanbul-instrumenter-loader",
                "include": [
                    'some/test/file', join(spec['build_dir'], 'afile.js')
                ],
            }]},
        }, spec['karma_config']['webpack'])

    def test_finalize_test_path_static(self):
        src_targetpath = join(mkdtemp(self), 'some', 'src', 'test_file.js')
        src_modpath = 'some/src/test_file'
        spec = Spec(build_dir=mkdtemp(self))
        src = dedent("""
        var ordinary = 'file';
        var module = require('a/std/string');
        """)

        makedirs(dirname(src_targetpath))
        with open(src_targetpath, 'w') as fd:
            fd.write(src)

        from calmjs.webpack.cli import default_toolchain as toolchain
        self.assertEqual(
            src_targetpath,
            dev._finalize_test_path(
                toolchain, spec, src_modpath, src_targetpath),
        )

    def test_finalize_test_path_dynamic(self):
        src_targetpath = join(mkdtemp(self), 'some', 'src', 'test_file.js')
        src_modpath = 'some/src/test_file'
        spec = Spec(build_dir=mkdtemp(self))
        src = dedent("""
        var ordinary = 'file';
        var dyn = require(dynamic);
        var module = require('a/std/string');
        """)

        makedirs(dirname(src_targetpath))
        with open(src_targetpath, 'w') as fd:
            fd.write(src)

        from calmjs.webpack.cli import default_toolchain as toolchain
        self.assertEqual(
            join(spec['build_dir'], *src_modpath.split('/')) + '.js',
            dev._finalize_test_path(
                toolchain, spec, src_modpath, src_targetpath),
        )

    def test_finalize_test_path_malformed(self):
        src_targetpath = join(mkdtemp(self), 'some', 'src', 'test_file.js')
        src_modpath = 'some/src/test_file'
        spec = Spec(build_dir=mkdtemp(self))
        src = dedent("""
        var malformed = 'file';
        var dyn = require(malformed);
        var module = require(
        """)

        makedirs(dirname(src_targetpath))
        with open(src_targetpath, 'w') as fd:
            fd.write(src)

        from calmjs.webpack.cli import default_toolchain as toolchain
        self.assertEqual(
            src_targetpath,
            dev._finalize_test_path(
                toolchain, spec, src_modpath, src_targetpath),
        )

    def test_process_test_files_empty(self):
        from calmjs.webpack.cli import default_toolchain as toolchain
        # the bare minimum spec
        spec = Spec(
            build_dir=mkdtemp(self),
            karma_config={
                'webpack': {
                    'resolve': {
                        'alias': {},
                    },
                },
                'preprocessors': {
                },
            }
        )
        test_files, loaderspath = dev._process_test_files(toolchain, spec)
        self.assertEqual(set(), test_files)
        self.assertEqual({}, loaderspath)

    def test_process_test_files_assorted(self):
        from calmjs.webpack.cli import default_toolchain as toolchain
        # the bare minimum spec
        spec = Spec(
            build_dir=mkdtemp(self),
            test_module_paths_map={
                # the values are normally absolute paths.
                'example/tests/test_main': 'test_main.js',
                'example/tests/data.json': 'data.json',
                'text!example/tests/data.txt': 'data.txt',
            },
            karma_config={
                'webpack': {
                    'resolve': {
                        'alias': {},
                    },
                },
                'preprocessors': {
                },
            }
        )

        with pretty_logging(stream=StringIO()) as s:
            test_files, loaderspath = dev._process_test_files(toolchain, spec)

        self.assertEqual({'test_main.js'}, test_files)
        self.assertEqual(
            {'text!example/tests/data.txt': 'data.txt'}, loaderspath)
        self.assertIn(
            "only aliasing modpath 'example/tests/data.json' to target "
            "'data.json'", s.getvalue())

    def test_karma_setup_empty(self):
        spec = Spec()
        with pretty_logging(stream=StringIO()) as s:
            with self.assertRaises(ToolchainAbort):
                karma_webpack(spec)

        self.assertNotIn('karma_config', spec)
        self.assertIn("'karma_config' not provided by spec", s.getvalue())

    def test_karma_setup_basic_file(self):
        karma_config = karma.build_base_config()
        # this should be purged.
        karma_config['files'] = ['example/package/lib.js']
        spec = Spec(
            karma_config=karma_config,
            build_dir=mkdtemp(self),
        )

        with pretty_logging(stream=StringIO()) as s:
            karma_webpack(spec)

        self.assertEqual(spec['karma_config']['files'], [
            join(spec['build_dir'], '__calmjs_tests__.js')])
        self.assertNotIn('unsupported', s.getvalue())

    def test_karma_setup_basic_test_separate(self):
        karma_config = karma.build_base_config()
        spec = Spec(
            karma_config=karma_config,
            build_dir=mkdtemp(self),
            test_module_paths_map={
                'some/package/tests/test_module':
                    '/src/some/package/tests/test_module.js'
            },
            webpack_single_test_bundle=False,
        )

        with pretty_logging(stream=StringIO()) as s:
            karma_webpack(spec)

        self.assertEqual(spec['karma_config']['files'], [
            '/src/some/package/tests/test_module.js',
        ])
        self.assertIn('unsupported', s.getvalue())

    def test_karma_setup_basic_test_single(self):
        karma_config = karma.build_base_config()
        build_dir = mkdtemp(self)
        spec = Spec(
            karma_config=karma_config,
            build_dir=build_dir,
            test_module_paths_map={
                'some/package/tests/test_module':
                    '/src/some/package/tests/test_module.js'
            },
            webpack_single_test_bundle=True,
        )

        karma_webpack(spec)

        unified_module = join(build_dir, '__calmjs_tests__.js')
        self.assertEqual(spec['karma_config']['files'], [unified_module])
        self.assertEqual(karma_config['webpack']['resolve']['alias'][
            'some/package/tests/test_module'
        ], '/src/some/package/tests/test_module.js')

        with open(unified_module) as fd:
            self.assertIn('some/package/tests/test_module', fd.read())

    def test_karma_setup_not_webpack_artifact(self):
        karma_config = karma.build_base_config()
        src_dir = mkdtemp(self)
        fake_artifact = join(src_dir, 'fake_artifact.js')

        with open(fake_artifact, 'w') as fd:
            fd.write('(function(root, factory) { factory() })')
            fd.write('(this, function() {});')

        build_dir = mkdtemp(self)
        spec = Spec(
            karma_config=karma_config,
            build_dir=build_dir,
            test_module_paths_map={
                'some/package/tests/test_module':
                    '/src/some/package/tests/test_module.js'
            },
            artifact_paths=[fake_artifact],
        )

        with pretty_logging(stream=StringIO()) as s:
            karma_webpack(spec)

        log = s.getvalue()
        self.assertIn("unable to extract calmjs related exports from", log)
        self.assertIn(fake_artifact, log)
