# -*- coding: utf-8 -*-
from __future__ import unicode_literals

import unittest

from calmjs.webpack import configuration


class CleanConfigTestCase(unittest.TestCase):

    def test_version_2(self):
        config = {}
        configuration.clean_config(config, '2.6.1')
        self.assertEqual({}, config)
        config = {'mode': 'none'}
        configuration.clean_config(config, '2.6.1')
        self.assertEqual({}, config)

    def test_version_4(self):
        config = {'mode': 'none'}
        configuration.clean_config(config, '4.0.1')
        self.assertEqual({'mode': 'none'}, config)
        config = {}
        configuration.clean_config(config, '4.0.1')
        self.assertEqual({'mode': 'none'}, config)
