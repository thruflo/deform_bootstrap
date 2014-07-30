# -*- coding: utf-8 -*-

"""Provides a ``CacheableWidgetMixin`` which allows you to construct deform
  widgets whose ``values`` are populated dynamically (e.g.: from the db) to
  delay actually making db calls until the form they are part of is actually
  rendered, and to cache their rendered template output using `Alkey`_.
  
  _Alkey: https://github.com/thruflo/alkey
"""

__all__ = [
    'CacheableWidgetMixin',
    'CacheableSingleWidget',
    'CacheableOptGroupWidget',
    'CacheableMultipleSelectGroupsWidget',
    'CacheableTypeaheadInputWidget',
]

import logging
logger = logging.getLogger(__name__)

from .widget import ChosenSingleWidget
from .widget import ChosenOptGroupWidget
from .widget import MultipleSelectGroupsWidget as MSGWidget
from .widget import TypeaheadInputWidget

class CacheableWidgetMixin(object):
    """Provides a cacheable `self.serialize(...)`` method and a
      ``self.get_dynamic_values`` method that:
      
      * starts with ``self._values``
      * calls ``self.get_values()``
      * prepends ``self._append_values``.
      
      Use by i) mixing into a Widget class (that uses a ``values`` property)
      and ii) forcibly overriding the ``values`` property and ``serialize``
      method, e.g.::
      
          >>> from deform.widget import SelectWidget # or whatever
          >>> 
          >>> class CacheableSelectWidget(SelectWidget, CacheableWidgetMixin):
          ...     values = property(CacheableWidgetMixin.get_dynamic_values)
          ...     serialize = CacheableWidgetMixin.serialize
          ...
      
      Then when you're instantiating the widget, pass in a ``get_values``
      callable, instead of a ``values`` list, e.g.::
      
          >>> widget = SomeCacheableWidget(get_values=lambda: ['a'])
          >>> widget.values
          ['a']
      
      You can also provide a static ``_values`` list and a list of values to
      append *after* the values have been got by calling ``get_values``, e.g.::
      
          >>> widget = SomeCacheableWidget(_values='a', get_values=lambda: ['b'],
          ...         _append_values=['c'])
          >>> widget.values
          ['a', 'b', 'c']
      
      The point of all of this being to delay populating the widget's values
      until the widget is serialized. Instead of passing a rendered ``form``
      through to the template, as per the standard ``pyramid_deform.FormView``
      api, we pass through a ``render_form`` function, which delays db query
      execution to within the template scope, which makes them cacheable, i.e.:
      if the template out is cached, next time the cache hits, the db call
      won't be made.
      
      If you would like to actually cache the widget's rendered template (as
      opposed to just allowing the rendered form to be cached without hitting
      the db) you can integrate with `Alkey <https://github.com/thruflo/alkey>`_
      by passing in a ``request`` when instantiating the widget and providing
      a ``cache_key_args`` list as a kwarg.
      
      For example, using colander.deferred with a form that's bind to the
      request as per ``.form.FormView``::
      
          from myapp.model import User
          
          @colander.deferred
          def user_widget(node, kw):
              request = kw['request]
              cache_key_args = ('myapp.user_widget', User)
              get_values = lambda: User.query.order_by(User.name).all()
              return CacheableSingleWidget(request=request, get_values=get_values,
                      cache_key_args=cache_key_args)
          
      What we get here is a single select widget that's populated with values
      from the database and cached with a cache key that will invalidate when
      any change is made to the users table (when a user is inserted, updated
      or deleted) *and* will vary when the user input (the `cstruct` passed
      to the widget's `serialize` method.) changes.
    """
    
    _values = []
    _append_values = []
    
    def get_values(self):
        """Override this method by passing a ``get_values`` kw to the
          widget constructor.
        """
        
        return []
    
    def get_dynamic_values(self):
        """Standard logic to construct the widget values."""
        
        # Start with an empty list.
        values = []
        
        # If a static list of values was provided, use that.
        if self._values:
            values.extend(self._values)
        
        # If a dynamic function to get values was provided, extend the values
        # with its return value.
        get_values = getattr(self, 'get_values', None)
        if callable(get_values):
            values.extend(get_values())
        
        # If a list of values to append was provided, do so.
        if self._append_values:
            values.extend(self._append_values)
        
        # Return the list of values.
        return values
    
    
    def serialize(self, field, cstruct, **kw):
        """We do the default, as per the super class but, iff a ``cache_key_args``
          have been provided, we cache the output using Alkey's
          ``request.cache_key`` method.
        """
        
        # Prepare a function that returns the serialized value.
        default_serialize = super(self.__class__, self).serialize
        serialize = lambda: default_serialize(field, cstruct, **kw)
        
        # If we weren't passed any cache key args, walk away.
        key_args = getattr(self, 'cache_key_args', None)
        if not key_args:
            return serialize()
        
        # Otherwise get the cache key and use it to cache the output.
        request = self.request
        cache_key = request.cache_key(1, self.template, cstruct, *key_args)
        cache_decorator = request.cache_manager.cache(cache_key)
        cached_serialize = cache_decorator(serialize)
        return cached_serialize()
    


class CacheableSingleWidget(ChosenSingleWidget, CacheableWidgetMixin):
    """Extend the ``ChosenSingleWidget`` with a cacheable values property."""
    
    values = property(CacheableWidgetMixin.get_dynamic_values)
    serialize = CacheableWidgetMixin.serialize

class CacheableOptGroupWidget(ChosenOptGroupWidget, CacheableWidgetMixin):
    """Extend the ``ChosenOptGroupWidget`` with a cacheable values property."""
    
    values = property(CacheableWidgetMixin.get_dynamic_values)
    serialize = CacheableWidgetMixin.serialize

class CacheableMultipleSelectGroupsWidget(MSGWidget, CacheableWidgetMixin):
    """Extend the ``MSGWidget`` with a cacheable values property."""
    
    values = property(CacheableWidgetMixin.get_dynamic_values)
    serialize = CacheableWidgetMixin.serialize

class CacheableTypeaheadInputWidget(TypeaheadInputWidget, CacheableWidgetMixin):
    """Extend the ``TypeaheadInputWidget`` with a cacheable values property."""
    
    values = property(CacheableWidgetMixin.get_dynamic_values)
    serialize = CacheableWidgetMixin.serialize

