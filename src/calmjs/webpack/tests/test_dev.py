# -*- coding: utf-8 -*-
import unittest
from os.path import join

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

        karma_webpack(spec)
        self.assertEqual(spec['karma_config']['files'], [])

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

        karma_webpack(spec)
        self.assertEqual(spec['karma_config']['files'], [
            '/src/some/package/tests/test_module.js',
        ])

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
