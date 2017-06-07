# -*- coding: utf-8 -*-
"""
Helper module for finalizing the environment before calling webpack
"""

import sys
from calmjs.utils import finalize_env

codec = sys.getdefaultencoding()

NODE_MODULES = 'node_modules'


def webpack_env(node_path):
    env = {
        'NODE_PATH': node_path,
        'FORCE_COLOR': '1',
    }
    return finalize_env(env)
