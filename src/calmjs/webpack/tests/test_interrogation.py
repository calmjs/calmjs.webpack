# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import codecs
from os.path import join
from pkg_resources import resource_filename

from calmjs.parse.parsers.es5 import parse
from calmjs.parse.asttypes import Object
from calmjs.webpack import interrogation


def read(p):
    with codecs.open(p, encoding='utf8') as fd:
        return fd.read()


_root = resource_filename('calmjs.webpack.testing', 'examples')
_empty = parse(read(join(_root, 'empty_package.js')))
_base = [parse(read(join(_root, f))) for f in (
    'example_package.js',
    'example_package.min.js',
)]
_extras = [parse(read(join(_root, f))) for f in (
    'example_package.extras.js',
    'example_package.extras.min.js',
)]

_typical_names = parse(read(join(_root, 'typical_names.js')))
_unusual_names = parse(read(join(_root, 'unusual_names.js')))


class WebpackTestCase(unittest.TestCase):

    def assertAllEqual(self, result, f, args):
        for a in args:
            self.assertEqual(sorted(result), sorted(f(a)))

    def test_probe_calmjs_webpack_module_names(self):
        self.assertAllEqual([
            'example/package/bad',
            'example/package/main',
            'example/package/math',
        ], interrogation.probe_calmjs_webpack_module_names, _base)

        self.assertAllEqual([
            'example/package/bare',
            'example/package/bad',
            'example/package/dynamic',
            'example/package/main',
            'example/package/math',
            'mockquery',
        ], interrogation.probe_calmjs_webpack_module_names, _extras)

        self.assertEqual([], interrogation.probe_calmjs_webpack_module_names(
            _empty))

    def test_probe_failure(self):
        # simply TypeError is raised
        with self.assertRaises(TypeError):
            interrogation.probe_calmjs_webpack_module_names(parse(read(join(
                _root, 'example_package.js')).replace(
                '__calmjs__', '__not_calmjs__')))

    def test_identifier_extraction_typical(self):
        # There will be cases where the module names provided are rather
        # special, and we need to be sure that we cover at least some of
        # them.
        for o in interrogation.walker.filter(
                _typical_names, lambda node: isinstance(node, Object)):
            self.assertEqual(
                'typical', interrogation.to_identifier(o.properties[0].left))

    def test_identifier_extraction_unusual(self):
        # The very unusual cases...
        answers = [
            '\'"\'',
            '\'\"\'',
            "\'\"\'",
            "\n",
            "\t",
            r'\\ ',
            "\u3042",
            "\u3042",
            "    ",
        ]
        for a, r in zip(answers, (o for o in interrogation.walker.filter(
                _unusual_names, lambda node: isinstance(node, Object)))):
            self.assertEqual(
                a, interrogation.to_identifier(r.properties[0].left))
