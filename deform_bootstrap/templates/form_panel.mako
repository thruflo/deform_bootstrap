
<%
  # Pop the messages from the flash up front, because we added them
  # optimistically, without an after_transaction hook.
  messages = request.session.pop_flash(queue=flash_queue)
%>

<%def name="render_flash(messages)">
  % for message in messages:
    <div class="alert alert-success">
      ${message}
    </div>
  % endfor
</%def>

<%
  render_flash = self.render_flash
  main_tmpl = context.get('main_template')
  if main_tmpl and hasattr(main_tmpl, 'render_flash'):
      render_flash = main_tmpl.render_flash    
%>

% if messages:
  <div class="form-panel-flash-messages">
    ${render_flash(messages)}
  </div>
% endif

<div class="form-panel-form-container">
  ${render_form() | n}
</div>
