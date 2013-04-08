# -*- coding: utf-8 -*-

"""Upload schemas and widgets, integrating colander with transloadit."""

__all__ = [
    'OptionalTransloaditUploadSchema',
    'TransloaditUploadSchema',
    'TransloaditUploadWidget',
    'transloadit_upload_widget',
]

import logging
logger = logging.getLogger(__name__)

import colander

from deform.widget import TextInputWidget

from .base import OrderableCSRFSchema
from .image import _transloadit_image_widget
from .url import url_preparer
from .url import url_validator

class TransloaditUploadWidget(TextInputWidget):
    """A base widget for transloadit uploads."""
    
    requirements = ()
    should_render_config = False
    strip = False
    template = 'transloadit_upload'


@colander.deferred
def transloadit_upload_widget(node, kw):
    """Override the imahe widget to use the ``TransloaditUploadWidget`` class."""
    
    return _transloadit_image_widget(node, kw, widget_cls=TransloaditUploadWidget)


class TransloaditUploadSchema(colander.Schema):
    """Form fields for an upload."""
    
    url = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator
    )

class OptionalTransloaditUploadSchema(colander.Schema):
    """Form fields for an optional upload."""
    
    missing = {}
    allow_remove = True
    
    url = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator,
        missing=None
    )

