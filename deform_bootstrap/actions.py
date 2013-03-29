# -*- coding: utf-8 -*-

"""Provide a widget which renders a block of form actions, i.e.::
  
      save_widget = FormActionsWidget('save')
  
"""

__all__ = [
    'FormActionsWidget',
]

import logging
logger = logging.getLogger(__name__)

import colander

from deform.form import Button
from deform.widget import Widget

class FormActionsWidget(Widget):
    """Render a block of form actions -- useful to, e.g.: insert a save button
      at multiple points in a form.
    """
    
    btn_cls = Button
    category = 'structural'
    template = 'form_actions'
    
    def __init__(self, *buttons):
        """Convert strings to button instances."""
        
        instances = []
        for item in buttons:
            if not isinstance(item, self.btn_cls):
                item = self.btn_cls(item)
            instances.append(item)
        self.buttons = instances
    
    def serialize(self, field, cstruct, **kw):
        if cstruct in (colander.null, None):
            cstruct = ''
        values = self.get_template_values(field, cstruct, kw)
        values['buttons'] = self.buttons
        return field.renderer(self.template, **values)
    
    def deserialize(self, field, pstruct):
        return colander.null
    
