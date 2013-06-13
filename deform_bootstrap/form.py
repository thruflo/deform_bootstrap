# -*- coding: utf-8 -*-

"""A refactor of the ``pyramid_deform.FormView``."""

import logging
logger = logging.getLogger(__name__)

from deform.exception import ValidationFailure
from deform.form import Form

class FormView(object):
    """Base class for views rendering and validating deform forms."""
    
    # `Colander` schema instance to be used to create the form instance.
    schema = None
    
    # Override to provide default data to populate form values.
    default_appstruct = None
    
    # Tuple of buttons or strings to pass to the form instance.
    buttons = (u'save',)
    
    # Two-tuple of options to pass as kwargs when instantiating the form.
    form_options = (('method', 'POST'),)
    
    # Validate the form on which methods?
    validate_methods = ('POST',)
    
    # Which request property to read the form data from, e.g.: 'POST' or
    # 'params'. Defaults to ``getattr(request, request.method)``.
    request_data_property = None
    
    # Tuple of actions to ignore.
    ignore_actions = (u'cancel',)
    
    # Tuple of top level children to ignore when returning form sections.
    ignore_sections = (u'_csrf', 'transloadit')
    
    # Use ajax?
    use_ajax = False
    ajax_options = '{}'
    
    # Class object of the type of form to be created.
    form_class = Form
    
    # Should the view pre-render the form, or leave it for the template to
    # call (and this make the markup rendering cacheable). Subclasses should
    # set this value to ``False`` to render the form manually / cacheably.
    should_render_form = True
    
    # Name, e.g.: render in a reusable template. Override on a sub class
    # by subclass basis.
    @property
    def form_name(self):
        """Default to using the request.context's name or class name. Fallback
          on using the form class name.
        """
        
        # Unpack
        request = self.request
        context = request.context
        
        # Prepare
        first_btn = len(self.buttons) and self.buttons[0]
        btn_is_create = first_btn and first_btn.lower() == u'create'
        action = u'Create new' if btn_is_create else u'Edit'
        name = self.__class__.__name__
        
        # Try to use the ``request.context``.
        if context:
            name = getattr(context, 'name', context.__name__)
        
        # Return concatenated, e.g. `Edit Foo`.
        return u'{0} {1}'.format(action, name)
    
    
    # Hooks.
    def prepare(self, form):
        """Override to process the ``form`` instance prior to rendering."""
        
        return form
    
    def success(self, appstruct):
        """Handle successfully parsed and validated user input."""
        
        return None
    
    def failure(self, error):
        """Handle a validation error."""
        
        self.request.response.status_int = 400
        return None
    
    def complete(self, template_vars):
        """Finish handling the request, e.g.: providing addition vars to pass
          to the template no matter whether the request was a success or not.
          
          The ``template_vars`` arg has (at least) ``form``, ``appstruct``
          and ``error`` keys.
        """
        
        return template_vars
    
    def top_level_sections(self, form):
        """Return a list of ``(name, title)`` for each top level form child."""
        
        sections = []
        for item in form.children:
            name = item.name
            title = item.title if item.title else name.title()
            if item.name in self.ignore_sections:
                continue
            sections.append((name, title))
        return sections
    
    def should_return(self, value):
        """Should we return ``value`` without using the complete machinery?"""
        
        return self.request.is_response(value)
    
    
    # Boilerplate.
    def validate(self, should_render=True, **kw):
        """Instantiates the form and, if necessary, validate it to return
          ``form, appstruct, error`` from the current request.
        """
        
        # Bind the schema and instantiate the form.
        schema = self.schema.bind(request=self.request, **kw)
        form = self.form_class(schema, buttons=self.buttons,
                use_ajax=self.use_ajax, ajax_options=self.ajax_options,
                **dict(self.form_options))
        
        # Provide a hook to augment / patch the form before rendering.
        form = self.prepare(form)
        
        # Determine whether we need to validate the request.
        should_validate = self.request.method in self.validate_methods
        if should_validate:
            # Get a handle on the request data.
            if self.request_data_property:
                data_property = self.request_data_property
            else:
                data_property = self.request.method
            request_data = getattr(self.request, data_property, {})
            # See if we should ignore this action.
            for action in self.ignore_actions:
                if action in request_data:
                    should_validate = False
                    break
        
        # Prepare the return values.
        error = None
        appstruct = None
        
        # Actually validate the request.
        if should_validate:
            params = request_data.items()
            try:
                appstruct = form.validate(params)
            except ValidationFailure as e:
                error = e
            else:
                if appstruct is None:
                    appstruct = {}
        
        # Log if in debug mode.
        logger.debug(('FormView.validate', error, appstruct))
        if error:
            if error.field and error.field.name:
                logger.debug(error.field.name)
            if error.error:
                logger.debug(error.error.asdict())
        
        # Return a tuple.
        return form, error, appstruct
    
    def __call__(self):
        """Default to just rendering the form."""
        
        # If necessary, validate the request.  If ``error is not None`` then
        # request validation failed, if ``appstruct is not None`` it was
        # successful. If both are None then the form view just needs to be
        # rendered.
        form, error, appstruct = self.validate()
        
        # First pass to the appropriate hook. These should either return a
        # response (e.g.: an HTTPFound or Response instance) or a dict to
        # mix into the template vars to pass to the complete method.
        response = None
        if error is not None:
            response = self.failure(error)
        elif appstruct is not None:
            response = self.success(appstruct)
        
        # If the success or failure method returned a response, return that.
        if self.should_return(response):
            return response
        
        # Render the form, in preparation for building a dictionary of
        # variables to pass to the template.
        if error:
            render_form = error.render
        else: # If we didn't need to validate, use the default appstruct.
            if appstruct is None:
                appstruct = self.default_appstruct
            args = (appstruct,) if appstruct else ()
            render_form = lambda: form.render(*args)
        rendered_form = render_form() if self.should_render_form else None
        
        # Instantiate the template variables. Note we keep to the convention of
        # passing in the rendered form as ``form`` and provide the original
        # form instance as ``form_instance``.
        template_vars = {
            'appstruct': appstruct,
            'error': error,
            'form_instance': form,
            'form_name': self.form_name,
            'form_sections': self.top_level_sections(form),
            'render_form': render_form,
            'form': rendered_form
        }
        
        # If the response was not None, assume it was an iterable to update
        # the template_vars with.
        if response:
            template_vars.update(response)
        
        # Pass to the complete hook and return the response.
        return self.complete(template_vars)
    
    def __init__(self, request):
        """Instantiate with the current ``request``."""
        
        self.request = request
    


class JSONFormView(FormView):
    """Special case FormView that skips the form template rendering in favour
      of returning JSON data.
    """
    
    def failure(self, validation_failure):
        """Return the error as a dict."""
        
        self.request.response.status_int = 400
        return validation_failure.error.asdict()
    
    def __call__(self):
        """Cut out the template rendering makarky."""
        
        form, error, appstruct = self.validate()
        
        data = None
        if error is not None:
            data = self.failure(error)
        if appstruct is not None:
            data = self.success(appstruct)
        return data if data is not None else {}
    

