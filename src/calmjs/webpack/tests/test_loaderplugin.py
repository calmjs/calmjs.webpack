# -*- coding: utf-8 -*-
import unittest
from calmjs.webpack import loaderplugin


class TextLoaderPluginTestCase(unittest.TestCase):
    """
    Upstream technically tested some of these, but doing it specifically
    here for posterity (and also for upstream stability purposes).
    """

    def test_unwrap(self):
        f = loaderplugin.TextPluginHandler(None, 'text').unwrap
        self.assertEqual(f('file.txt'), 'file.txt')
        self.assertEqual(f('text!file.txt'), 'file.txt')
        # since there are no nesting...
        self.assertEqual(f('text!file.txt!strip'), 'file.txt!strip')

    def test_unwrap_unstripped_values(self):
        f = loaderplugin.TextPluginHandler(None, 'text').unwrap
        self.assertEqual(f('/file.txt'), '/file.txt')
        self.assertEqual(f('/text!file.txt'), '/text!file.txt')
        self.assertEqual(f('/text!file.txt!strip'), '/text!file.txt!strip')

    def test_unwrap_empty(self):
        f = loaderplugin.TextPluginHandler(None, 'text').unwrap
        # this should be invalid, but we are forgiving
        self.assertEqual(f(''), '')
        self.assertEqual(f('text!'), '')
