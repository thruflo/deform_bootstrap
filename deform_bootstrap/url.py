# -*- coding: utf-8 -*-

"""Url preparer and validator."""

__all__ = [
    'url_validator',
    'url_preparer',
]

import logging
logger = logging.getLogger(__name__)

import re
import colander
import formencode
from formencode import validators

def url_preparer(value, url_validator=None):
    """Prepare a url value by adding the http schema and encoding idna."""
    
    # Don't faff about with an empty / None value.
    if not value:
        return value
    
    # Compose.
    if url_validator is None:
        url_validator = validators.URL(add_http=True, allow_idna=True)
    
    # Copy of the formencode.Url logic.
    if not url_validator.scheme_re.search(value):
        value = 'http://' + value
    value = url_validator._encode_idna(value)
    
    # Return the prepared value.
    return value


def url_validator(node, value, len_validator=None, url_validator_cls=None):
    """Validate a url value."""
    
    # Don't validate an empty / None value.
    if not value:
        return
    
    # Compose.
    if len_validator is None:
        len_validator = colander.Length(max=255)
    if url_validator_cls is None:
        url_validator_cls = validators.URL
    
    # Validate a string, max length 255.
    len_validator(node, value)
    
    # Validate the url syntax.
    check_exists = getattr(node, 'check_exists', False)
    url_validator = url_validator_cls(require_tld=True, check_exists=check_exists)
    try:
        url_validator.to_python(value)
    except formencode.Invalid as err:
        raise colander.Invalid(node, '%r is not a valid url')

