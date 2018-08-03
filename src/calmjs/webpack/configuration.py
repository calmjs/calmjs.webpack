# -*- coding: utf-8 -*-
"""
Various utility functions
"""

from operator import (
    lt,
    ge,
)

from .base import DEFAULT_WEBPACK_MODE


def apply_webpack_mode(config):
    if 'mode' not in config:
        config['mode'] = DEFAULT_WEBPACK_MODE


def remove_webpack_mode(config):
    config.pop('mode', None)


config_rules = (
    (lt, ((4, 0),), remove_webpack_mode),
    (ge, ((4, 0),), apply_webpack_mode),
)


def clean_config(config, version_str, rules=config_rules):
    version = tuple(int(i) for i in version_str.split('.'))
    for operator, arguments, rule in rules:
        if operator(version, *arguments):
            rule(config)
