#!/usr/bin/env python
# coding: utf-8
# SPDX-License-Identifier: CC0
#

"""API Plugin Support"""

from .APIPlugin import APIPlugin
from .BasinPlugin import BasinPlugin
from .CatchmentPlugin import CatchmentPlugin
from .CrawlerSourcePlugin import CrawlerSourcePlugin
from .FeaturePlugin import FeaturePlugin
from .FlowlinePlugin import FlowlinePlugin
from .HydroLocationPlugin import HydroLocationPlugin
from .MainstemPlugin import MainstemPlugin
from .SplitCatchmentPlugin import SplitCatchmentPlugin

__all__ = [
    "APIPlugin",
    "BasinPlugin",
    "CatchmentPlugin",
    "CrawlerSourcePlugin",
    "FeaturePlugin",
    "FlowlinePlugin",
    "HydroLocationPlugin",
    "MainstemPlugin",
    "SplitCatchmentPlugin",
]


# def load_plugin(plugin_name_string: str) -> Any:
#     """
#     loads plugin by name

#     :param plugin_def: plugin definition

#     :returns: plugin object
#     """
#     name = plugin_def["name"]

#     LOGGER.debug(f"Plugins: {PLUGINS}")

#     if "." not in name and name not in PLUGINS.keys():
#         msg = f"Plugin {name} not found"
#         LOGGER.exception(msg)
#         raise InvalidPluginError(msg)

#     if "." in name:  # dotted path
#         packagename, classname = name.rsplit(".", 1)
#     else:  # core formatter
#         packagename, classname = PLUGINS[name].rsplit(".", 1)

#     LOGGER.debug(f"package name: {packagename}")
#     LOGGER.debug(f"class name: {classname}")

#     module = importlib.import_module(packagename)
#     class_ = getattr(module, classname)
#     plugin = class_(plugin_def)

#     return plugin


# class InvalidPluginError(Exception):
#     """Invalid plugin"""

#     pass
