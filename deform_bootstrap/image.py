# -*- coding: utf-8 -*-

"""Image schemas and widgets, integrating colander with transloadit."""

__all__ = [
    'BaseTransloaditSchema',
    'TransloaditImageSchema',
    'OptionalTransloaditImageSchema',
    'TransloaditImageWidget',
    'transloadit_image_widget',
    'transloadit_image_preparer',
]

import logging
logger = logging.getLogger(__name__)

from collections import defaultdict
from datetime import datetime
from datetime import timedelta

import hmac
import hashlib
import json

import colander

from deform.widget import HiddenWidget
from deform.widget import TextInputWidget
from pyramid_weblayer.hsts import ensure_secure_url

from deform_bootstrap.base import OrderableCSRFSchema
from .url import url_preparer
from .url import url_validator

def get_signed_config(request, template_id_key):
    """Shared logic to generate and hash transloadit config."""
    
    # Unpack the request.
    settings = request.registry.settings
    auth_key = settings.get('transloadit.auth_key')
    auth_secret = settings.get('transloadit.auth_secret')
    template_id = settings.get('transloadit.{0}'.format(template_id_key))
    
    # Generate the config.
    expires_dt = datetime.now() + timedelta(days=1)
    expires_str = expires_dt.strftime('%Y/%m/%d %H:%M:%S')
    config = {
        'auth': {'key': auth_key, 'expires': expires_str},
        'template_id': template_id,
        'redirect_url': request.path
    }
    config_str = json.dumps(config)
    
    # Sign it.
    signature = hmac.new(auth_secret, config_str, hashlib.sha1).hexdigest()
    
    # And return
    return config_str, signature

def parse_transloadit_data(data_str, secure_url=None):
    """Coerces a transloadit result JSON data string to a dict keyed
      by field name and secures any urls::
      
          >>> data = {
          ...   'results': {
          ...     'small': [
          ...       {'url': 'http://a.com/small', 'field': 'a'},
          ...       {'url': 'http://a.com/small2', 'field': 'a'},
          ...       {'url': 'http://b.com/small', 'field': 'b'}
          ...     ],
          ...     'medium': [
          ...       {'url': 'http://a.com/medium', 'field': 'a'},
          ...       {'url': 'http://a.com/medium2', 'field': 'a'},
          ...       {'url': 'http://b.com/medium', 'field': 'b'}
          ...     ],
          ...     ':original': [
          ...       {'url': 'http://a.com/original', 'field': 'a'},
          ...       {'url': 'http://a.com/original2', 'field': 'a'},
          ...       {'url': 'http://b.com/original', 'field': 'b'}
          ...     ]
          ...   }
          ... }
          ... 
          >>> data_str = json.dumps(data)
          >>> data = parse_transloadit_data(data_str)
          >>> data.keys()
          [u'a', u'b']
          >>> len(data[u'a']), len(data[u'b'])
          (2, 1)
          >>> data[u'a'][1].keys()
          [u'small', u'medium', u'original']
          >>> data[u'a'][1].values()
          [u'https://a.com/small2', u'https://a.com/medium2', u'https://a.com/original2']
      
    """
    
    # Compose.
    if secure_url is None:
        secure_url = ensure_secure_url
    
    # Ignore null values.
    if not data_str:
        return {}
    
    # Parse the json.
    try:
        data = json.loads(data_str)
    except Exception as err:
        logger.warn(err, exc_info=True)
        return {}
    
    # The order of the items in the results dicts is not reliable, i.e.: in the
    # ``small`` dict, it may be [img1, img2] whereas in the ``large`` dict, it
    # may be ``[img2, img1]``. Thus, we need to use the ``original_id`` key of
    # the result data to work out the order. This is available as ``id`` on the
    # upload and ``origial_id`` on the result item. So, we first build a lookup
    # dict of ``original_id: index`` by field name, to be used below.
    counters = defaultdict(int)
    index_lookup = defaultdict(dict)
    uploads = data.get('uploads')
    for item in uploads:
        field = item.get('field')
        original_id = item.get('id')
        index_lookup[field][original_id] = counters[field]
        counters[field] += 1
    
    # Prepare the ``return_value[field]`` with a list of placeholder values,
    # so that data as we go along at any index, without having tp have already
    # inserted a real value at the previous indexes.
    return_value = defaultdict(lambda: [{} for item in range(len(uploads))])
    
    # Now loop through the results to build the return value.
    results = data.get('results')
    if results:
        try:
            # The ``key`` is the encoded file size & image instance column name,
            # e.g.: ``small`` or ``large``.
            for key in results:
                # The ``items`` are a list of dicts with ``url`` and ``field`` keys,
                items = results.get(key)
                # Support `:name` keys, mapping them to `name`. This allows us to
                # store the `:original` image *and* include multiple encoding steps
                # in the same transloadit template, effectively routing different fields
                # to different settings, whilst mapping them all back to the same
                # `small`, `medium`, `large` schema field names. If this makes no sense,
                # see the overview config section in `./etc/transloadit.json`.
                # Note this implementation is recursive, so names like `small`, `:small`,
                # `::small` and `:::small` all resolve to `small`. Obviously when using
                # this as a route-different-fields-to-different-settings trick, you need
                # to make sure that for any given image, only one of these will run, i.e.:
                # that you get back either `small` or `:small`. Again, see the overview
                # example.
                while key.startswith(':'):
                    key = key[1:]
                # Look through the items, 
                for item in items:
                    # The ``field`` is the name of the form input, e.g.: ``logo_image``.
                    field = item.get('field')
                    # The ``url`` is to the encoded image src.
                    url = item.get('url')
                    # Use the ``original_id`` to get the target return value item.
                    original_id = item.get('original_id')
                    target_index = index_lookup[field][original_id]
                    try:
                        target = return_value[field][target_index]
                    except IndexError:
                        target = {}
                        return_value[field].insert(target_index, target)
                    # Set the target's value for this key, e.g.:
                    # ``target['small'] == 'https://...'``.
                    target[key] = secure_url(url)
                    # Write / overwrite the return value item, e.g.:
                    # ``return_value['logo_image'] == target``'.
                    return_value[field][target_index] = target
        except Exception as err:
            logger.warn(err, exc_info=True)
    return dict(return_value)


class TransloaditImageWidget(TextInputWidget):
    """A base widget for transloadit images."""
    requirements = ()
    should_render_config = False
    strip = False
    template = 'transloadit_image'
    thumbnail_class = 'upload-image'

class TransloaditConfigWidget(HiddenWidget):
    """A base widget for transloadit images."""
    requirements = ()
    should_render_config = True
    strip = False
    template = 'transloadit_config'


def _transloadit_image_widget(node, kw, get_config=None, widget_cls=None):
    """Configure the schema node with ``template_id_key`` to get
      the template if to use from your ini settings, e.g.::
      
          >>> node = SchemaNode(template_id_key='my_template_key')
      
      Will get the template id in::
      
          transloadit.my_template_key = ...
      
      Defaults to ``transloadit.template_id``.
    """
    
    # Compose.
    if get_config is None:
        get_config = get_signed_config
    if widget_cls is None:
        widget_cls = TransloaditImageWidget
    
    # Unpack.
    request = kw['request']
    template_id_key = getattr(node, 'template_id_key', 'template_id')
    should_render_config = getattr(node, 'should_render_config', False)
    allow_remove = getattr(node, 'allow_remove', False)
    category = getattr(node, 'category', None)
    
    # Get signed config.
    config_str, signature = get_signed_config(request, template_id_key)
    
    # Return the widget.
    return widget_cls(config_str=config_str, signature=signature,
            allow_remove=allow_remove, category=category,
            should_render_config=should_render_config)

transloadit_image_widget = colander.deferred(_transloadit_image_widget)

def _transloadit_config_widget(node, kw, get_config=None, widget_cls=None):
    """As with ``transloadit_image_widget`` but a ``TransloaditConfigWidget``."""
    
    # Compose.
    if get_config is None:
        get_config = get_signed_config
    if widget_cls is None:
        widget_cls = TransloaditConfigWidget
    
    # Unpack.
    request = kw['request']
    template_id_key = getattr(node, 'template_id_key', 'template_id')
    should_render_config = getattr(node, 'should_render_config', True)
    category = getattr(node, 'category', None)
    
    # Get signed config.
    config_str, signature = get_signed_config(request, template_id_key)
    
    # Return the widget.
    return widget_cls(config_str=config_str, signature=signature,
            should_render_config=should_render_config, category=category)

transloadit_config_widget = colander.deferred(_transloadit_config_widget)

@colander.deferred
def deferred_template_id_key(node, kw):
    return getattr(node, 'template_id_key', 'template_id')


class BaseTransloaditSchema(OrderableCSRFSchema):
    """Base schema for forms that contain transloadit image fields.
      
      Inherit from it and provide a mapping and settings key, e.g.::
      
          >>> class MyImageUploadSchema(BaseTransloaditSchema):
          ...     transloadit_mapping = {'images.images': ['image']}
          ...     template_id_key = 'gallery_template'
          ... 
      
      This class will look in your settings for a template id at
      ``transloadit.gallery_template`` and will populate ``images.images.0``,
      ``images.images.1`` etc.
      
      If you're using a single or specific images, use e.g.:
      ``transloadit_mapping = {'logo': 'logo'}``, i.e.: use a string rather
      than a list.
    """
    
    # E.g.: ``{'logo': 'logo'}`` or ``{'images.images': ['image']}``.
    transloadit_mapping = NotImplemented
    template_id_key = None
    
    # Render the transloadit config.
    transloadit = colander.SchemaNode(
        colander.String(),
        widget=transloadit_config_widget,
        missing=None
    )
    
    def deserialize(self, cstruct, parse_data=None):
        """Unpack the transloadit data into the right fields."""
        
        # Compose.
        if parse_data is None:
            parse_data = parse_transloadit_data
        
        # Ignore if no data.
        if not cstruct:
            return cstruct
        
        # Get the transload it data and parse it into the right fields.
        data_str = cstruct.pop('transloadit', None)
        if data_str:
            data = parse_data(data_str)
            for cstruct_key, config in self.transloadit_mapping.items():
                # If we've specified a direct path to a single image, e.g.:
                # ``{'logo': 'logo'}`` then just get and set the value.
                if isinstance(config, basestring):
                    data_key = config
                    data_item = data.get(data_key)
                    if data_item is not None:
                        value = data_item[0]
                        self.set_value(cstruct, cstruct_key, value)
                else: # If we've been given a path that specifies a mapping item
                    # within a sequence, e.g.: using syntax like
                    # ``{'images.*.foo': ['image']`` then update the
                    # ``foo`` key of each item in the current images list with
                    # the image items.
                    data_key = config[0]
                    data_items = data.get(data_key)
                    if data_items is None:
                        data_items = []
                    if '.*.' in cstruct_key:
                        cstruct_key, cstruct_item_key = cstruct_key.split('.*.')
                        cstruct_items = self.get_value(cstruct, cstruct_key)
                        # Now! The thing here is that the existing values may
                        # be populated: in which case we don't need to patch in
                        # the transloadit data. Or they're not, in which case
                        # we do. So, we do a manual loop, incrementing the counter
                        # when we find a cstruct item that has a null value.
                        i = 0
                        for cstruct_item in cstruct_items:
                            if cstruct_item[cstruct_item_key]:
                                continue
                            cstruct_item[cstruct_item_key] = data_items[i]
                            i += 1
                        self.set_value(cstruct, cstruct_key, cstruct_items)
                    else: # We've been given a direct path to a sequence of
                        # images, e.g.: ``{'images.images': ['image']}``, so
                        # overwrite the values at that key.
                        self.set_value(cstruct, cstruct_key, data_items)
        
        return super(BaseTransloaditSchema, self).deserialize(cstruct)
    
    def __init__(self, *args, **kwargs):
        """Patch the ``template_id_key`` of the ``transloadit`` child node."""
        
        target = self['transloadit']
        if self.template_id_key:
            target.template_id_key = self.template_id_key
        
        super(BaseTransloaditSchema, self).__init__(*args, **kwargs)
    

class TransloaditImageSchema(colander.Schema):
    """Form fields for an image with small, medium, large and original varients."""
    
    small = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator
    )
    medium = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator
    )
    large = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator
    )
    original = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator
    )

class OptionalTransloaditImageSchema(colander.Schema):
    """Form fields for an optional image with small, medium, large and
      original varients.
    """
    
    missing = {}
    allow_remove = True
    
    small = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator,
        missing=None
    )
    medium = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator,
        missing=None
    )
    large = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator,
        missing=None
    )
    original = colander.SchemaNode(
        colander.String(),
        preparer=url_preparer,
        validator=url_validator,
        missing=None
    )

