# -*- coding: utf-8 -*-

"""Provide a widget which renders a named panel. This is useful for
  inserting "normal" (i.e.: non-deform-chameleon) stuff into forms.
"""

__all__ = [
    'PanelWidget',
]

import logging
logger = logging.getLogger(__name__)

import colander
from deform.widget import Widget

class PanelWidget(Widget):
    """A widget that serialises to a rendered panel."""
    
    category = 'structural'
    
    def __init__(self, name, *args, **kwargs):
        self.panel_name = name
        self.panel_args = args
        self.panel_kwargs = kwargs
    
    def __call__(self, node, kw):
        """Get ``request.layout_manager`` from the ``kw`` and return ``self``."""
        
        # Store the layout manager from the request.
        self.layout = kw['request'].layout_manager
        
        # Return this widget.
        return self
    
    def serialize(self, field, cstruct, **kw):
        """Render the panel.  If the pabel doesn't exist, then return an
          empty string.
        """
        
        rendered_panel = self.layout.render_panel(self.panel_name,
                *self.panel_args, **self.panel_kwargs)
        if rendered_panel is None:
            return u''
        return rendered_panel
    
    def deserialize(self, field, pstruct):
        """Don't deserialise anything."""
        
        return colander.null
    

