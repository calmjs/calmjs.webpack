# -*- coding: utf-8 -*-
import unittest

from calmjs.toolchain import Spec
from calmjs.utils import pretty_logging

from calmjs.webpack.cli import create_spec
from calmjs.webpack.cli import compile_all

from calmjs.testing.mocks import StringIO


class CliTestCase(unittest.TestCase):
    """
    Test mostly basic implementation, most of the core test will be done
    in the toolchain and/or the integration tests.
    """

    def test_create_spec_empty(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([])

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertIn(
            "using calmjs bootstrap; webpack.output.library set to "
            "'__calmjs__'", stream.getvalue()
        )
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.export.js')
        self.assertEqual(spec['calmjs_module_registry_names'], [])
        self.assertIn('webpack_externals', spec)
        self.assertEqual(spec['webpack_output_library'], '__calmjs__')

    def test_create_spec_empty_use_calmjs_bootstrap_disable(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec([], use_calmjs_bootstrap=False)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertIn(
            "not using calmjs bootstrap; webpack.output.library set to "
            "'calmjs.webpack.export'", stream.getvalue()
        )
        self.assertTrue(isinstance(spec, Spec))
        self.assertNotIn('webpack_externals', spec)
        self.assertEqual(
            spec['webpack_output_library'], 'calmjs.webpack.export')

    def test_create_spec_with_calmjs_webpack(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.webpack'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "building source map", log,
        )

    def test_create_spec_with_calmjs_webpack_no_bootstrap(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(['calmjs.webpack'], use_calmjs_bootstrap=False)
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "automatically picked registries ['calmjs.module'] for "
            "building source map", log,
        )
        self.assertEqual(
            spec['webpack_output_library'], 'calmjs.webpack')

    def test_create_spec_with_calmjs_webpack_no_registry(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], source_registry_method='none')
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], [])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "no module registry declarations found using packages "
            "['calmjs.webpack'] using acquisition method 'none'", log
        )

    def test_create_spec_with_calmjs_webpack_manual_source(self):
        with pretty_logging(stream=StringIO()) as stream:
            spec = create_spec(
                ['calmjs.webpack'], source_registries=['calmjs.module.tests'])
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.js')
        self.assertEqual(
            spec['calmjs_module_registry_names'], ['calmjs.module.tests'])
        self.assertEqual(
            spec['source_package_names'], ['calmjs.webpack'])

        log = stream.getvalue()
        self.assertIn(
            "using manually specified registries ['calmjs.module.tests'] for "
            "building source map", log,
        )

    def test_toolchain_empty(self):
        # dict works well enough as a null toolchain
        with pretty_logging(stream=StringIO()) as stream:
            spec = compile_all([], toolchain=dict)

        self.assertNotIn('packages []', stream.getvalue())
        self.assertIn('no packages specified', stream.getvalue())
        self.assertTrue(isinstance(spec, Spec))
        self.assertEqual(spec['export_target'], 'calmjs.webpack.export.js')
