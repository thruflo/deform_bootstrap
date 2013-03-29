# -*- coding: utf-8 -*-

"""Base colander schema classes."""

__all__ = [
    'CSRFSchema',
    'OrderableCSRFSchema',
    'coerce_to_lowercase',
    'dedupe_sequence', 
    'if_empty_null',
    'remove_empty_values',
    'remove_multiple_spaces',
    'strip_whitespace',
]

import logging
logger = logging.getLogger(__name__)

import re
import colander

from deform.widget import HiddenWidget

from pyramid_deform import deferred_csrf_value
from pyramid_deform import deferred_csrf_validator

coerce_to_lowercase = lambda v: v.lower() if hasattr(v, 'lower') else v
strip_whitespace = lambda v: v.strip(' \t\n\r') if hasattr(v, 'strip') else v
remove_multiple_spaces = lambda v: re.sub(' +', ' ', v) if v else v
if_empty_null = lambda v: colander.null if not v else v
dedupe_sequence = lambda v: list(set(v)) if hasattr(v, '__iter__') else v
remove_empty_values = lambda v: filter(bool, v) if hasattr(v, '__iter__') else v

class CSRFSchema(colander.Schema):
    """Base schema class that provides weblayer compatible CSRF validation."""
    
    _csrf = colander.SchemaNode(colander.String(), widget=HiddenWidget(),
            default=deferred_csrf_value, validator=deferred_csrf_validator)

class OrderableCSRFSchema(CSRFSchema):
    """Correct field order by name."""
    
    # e.g.: ``{'description': -1}``, ``{'name': 0}``.
    field_order = {}
    
    def __new__(cls, *args, **kwargs):
        """Allows children to be re-ordered when a new instance of the class
          is made.
          
          See http://permalink.gmane.org/gmane.comp.web.pylons.general/18428
        """
        
        obj = CSRFSchema.__new__(cls, *args, **kwargs)
        children_to_move = []
        for index, child in enumerate(obj.children):
            if child.name in cls.field_order:
                node = obj.children.pop(index)
                children_to_move.append((node, cls.field_order[child.name]))
        for node, index in children_to_move:
            if index is -1:
                obj.children.append(node)
            else:
                obj.children.insert(index, node)
        return obj
    

