# =================================================================
#
# Author: Benjamin Webb <bwebb@lincolninst.edu>
#
# Copyright (c) 2023 Benjamin Webb
#
# Permission is hereby granted, free of charge, to any person
# obtaining a copy of this software and associated documentation
# files (the "Software"), to deal in the Software without
# restriction, including without limitation the rights to use,
# copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following
# conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
# OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
# =================================================================
"""Plugin loader"""

import importlib
from typing import Any

from . import LOGGER

PLUGINS = {
    "CatchmentLookup": "nldi.lookup.catchment.CatchmentLookup",
    "CrawlerSourceLookup": "nldi.lookup.source.CrawlerSourceLookup",
    "FeatureLookup": "nldi.lookup.feature.FeatureLookup",
    "FlowlineLookup": "nldi.lookup.flowline.FlowlineLookup",
    "MainstemLookup": "nldi.lookup.mainstem.MainstemLookup",
    "PygeoapiLookup": "nldi.lookup.pygeoapi.PygeoapiLookup",
}


def load_plugin(plugin_def: dict) -> Any:
    """
    loads plugin by name

    :param plugin_def: plugin definition

    :returns: plugin object
    """

    name = plugin_def["name"]

    LOGGER.debug(f"Plugins: {PLUGINS}")

    if "." not in name and name not in PLUGINS.keys():
        msg = f"Plugin {name} not found"
        LOGGER.exception(msg)
        raise InvalidPluginError(msg)

    if "." in name:  # dotted path
        packagename, classname = name.rsplit(".", 1)
    else:  # core formatter
        packagename, classname = PLUGINS[name].rsplit(".", 1)

    LOGGER.debug(f"package name: {packagename}")
    LOGGER.debug(f"class name: {classname}")

    module = importlib.import_module(packagename)
    class_ = getattr(module, classname)
    plugin = class_(plugin_def)

    return plugin


class InvalidPluginError(Exception):
    """Invalid plugin"""

    pass
