# -*- coding: utf-8 -*-

"""Provider markdown widget for textareas with rich content."""

__all__ = [
    'MarkdownWidget',
]

import logging
logger = logging.getLogger(__name__)

import colander
from deform.widget import TextInputWidget

class MarkdownWidget(TextInputWidget):
    """Renders a textarea with the markitup editor in markdown mode."""
    
    def deserialize(self, field, pstruct):
        if pstruct is colander.null:
            return colander.null
        if not pstruct:
            return null
        value = pstruct
        if hasattr(pstruct, 'values'):
            values = pstruct.values()
            if values and len(values):
                value = values[0]
        if self.strip and value:
            value = value.strip()
        return value
    
    
    delayed_load = False
    readonly_template = 'readonly/textarea'
    requirements = ()
    strip = True
    template = 'markdown'


def markdown_preparer(value):
    """Lose the enclosing <p></p> tag and the encoded character returns."""
    
    if not value:
        return value
    value = value.replace('&#13;', '\r\n')
    value = value.replace(u'\n\n', '\n')
    if value.startswith('<p>'):
        value = value[3:]
    if value.endswith('</p>'):
        value = value[:-4]
    return value

