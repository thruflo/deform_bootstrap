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

coerce_to_lowercase = lambda v: v.lower() if hasattr(v, 'lower') else v
strip_whitespace = lambda v: v.strip(' \t\n\r') if hasattr(v, 'strip') else v
remove_multiple_spaces = lambda v: re.sub(' +', ' ', v) if v else v
if_empty_null = lambda v: colander.null if not v else v
dedupe_sequence = lambda v: list(set(v)) if hasattr(v, '__iter__') else v
remove_empty_values = lambda v: filter(bool, v) if hasattr(v, '__iter__') else v

# http://tools.ietf.org/html/rfc2616.html#section-9.1.1
SAFE_METHODS = ('GET', 'HEAD')

@colander.deferred
def deferred_csrf_missing(node, kw):
    """If the request method is GET or HEAD, then make sure the CSRF value
      is always the CSRF token in the session. Otherwise set it to required.
      
      This is equivalent to specifying ``missing=get_csrf_token()`` iff the
      request is safe.
    """
    
    request = kw['request']
    if request.method in SAFE_METHODS:
        return request.session.get_csrf_token()
    return colander.required


@colander.deferred
def deferred_csrf_validator(node, kw):
    """If the request method is not GET or HEAD, then make sure the value
      is the session's CSRF token.
    """
    
    request = kw['request']
    if request.method in SAFE_METHODS:
        return lambda node, value: None 
    
    def _validate(node, value):
        csrf_token = request.session.get_csrf_token()
        if value != csrf_token:
            raise colander.Invalid(node, 'Invalid cross-site scripting token')
    
    return _validate


class CSRFSchema(colander.Schema):
    """Base schema class that provides weblayer compatible CSRF validation."""
    
    _csrf = colander.SchemaNode(
        colander.String(), 
        widget=HiddenWidget(),
        default=deferred_csrf_value,
        validator=deferred_csrf_validator,
        missing=deferred_csrf_missing
    )

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
    

