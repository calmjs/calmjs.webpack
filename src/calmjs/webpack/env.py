# -*- coding: utf-8 -*-
"""
Helper module for finalizing the environment before calling webpack
"""

import sys
from calmjs.utils import finalize_env

codec = sys.getdefaultencoding()


def recode(v):
    return v if isinstance(v, str) else v.encode(codec)


def webpack_env(node_path):
    env = {
        'NODE_PATH': node_path,
        'FORCE_COLOR': '1',
    }
    return {recode(k): recode(v) for k, v in finalize_env(env).items()}
