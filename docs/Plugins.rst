Plugins
*******

The API Plugins create implemenations of various services offered by the API. The idea
here is that a service (typically some sort of lookup) would be implemented in the plugin,
and the collection of all such plugins would form the collection of services available
via the API.

All plugins are subclassed from ``APIPlugin``:

.. autoclass:: nldi.api.plugins.APIPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.CrawlerSourcePlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.FeaturePlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.FlowlinePlugin
    :members:
    :undoc-members:
    :exclude-members: __init__


-----------------

.. autoclass:: nldi.api.plugins.CatchmentPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.BasinPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.MainstemPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.HydroLocationPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.SplitCatchmentPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__

-----------------

.. autoclass:: nldi.api.plugins.PyGeoAPIPlugin
    :members:
    :undoc-members:
    :exclude-members: __init__
