# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest
import codecs
from os.path import join
from pkg_resources import resource_filename

from calmjs.parse import es5
from calmjs.parse.asttypes import Object
from calmjs.webpack import interrogation


def read(p):
    with codecs.open(p, encoding='utf8') as fd:
        return fd.read()


_root = resource_filename('calmjs.webpack.testing', 'examples')
_base = [es5(read(join(_root, f))) for f in (
    'example_package.js',
    'example_package.min.js',
)]
_extras = [es5(read(join(_root, f))) for f in (
    'example_package.extras.js',
    'example_package.extras.min.js',
)]

_typical_names = es5(read(join(_root, 'typical_names.js')))
_unusual_names = es5(read(join(_root, 'unusual_names.js')))


class InterrogationTestCase(unittest.TestCase):

    def assertAllEqual(self, result, f, args):
        for a in args:
            self.assertEqual(sorted(result), sorted(f(a)))

    def test_probe(self):
        self.assertAllEqual([
            'example/package/bad',
            'example/package/main',
            'example/package/math',
        ], interrogation.probe, _base)

        self.assertAllEqual([
            'example/package/bare',
            'example/package/bad',
            'example/package/main',
            'example/package/math',
            'mockquery',
        ], interrogation.probe, _extras)

    def test_identifier_extraction_typical(self):
        # There will be cases where the module names provided are rather
        # special, and we need to be sure that we cover at least some of
        # them.
        for o in interrogation.visitor.generate(
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
        for a, r in zip(answers, (o for o in interrogation.visitor.generate(
                _unusual_names, lambda node: isinstance(node, Object)))):
            self.assertEqual(
                a, interrogation.to_identifier(r.properties[0].left))
