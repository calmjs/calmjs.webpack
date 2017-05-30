# -*- coding: utf-8 -*-
"""
Exceptions specific for this module.
"""


class WebpackRuntimeError(RuntimeError):
    """webpack runtime error"""


class WebpackExitError(RuntimeError):
    """webpack exit error, for trapping exit code"""

    def __init__(self, exit_code, binary='webpack', *a):
        self.exit_code = exit_code
        if not a:
            a = ('%s terminated with exit code %d' % (binary, exit_code),)
        super(WebpackExitError, self).__init__(*a)
