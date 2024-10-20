TemplateNotFound
jinja2.exceptions.TemplateNotFound: index.html

Traceback (most recent call last)
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 1498, in __call__
return self.wsgi_app(environ, start_response)
File "/home/ia/.local/lib/python3.8/site-packages/flask_socketio/__init__.py", line 43, in __call__
return super(_SocketIOMiddleware, self).__call__(environ,
File "/home/ia/.local/lib/python3.8/site-packages/engineio/middleware.py", line 74, in __call__
return self.wsgi_app(environ, start_response)
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 1476, in wsgi_app
response = self.handle_exception(e)
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 1473, in wsgi_app
response = self.full_dispatch_request()
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 882, in full_dispatch_request
rv = self.handle_user_exception(e)
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 880, in full_dispatch_request
rv = self.dispatch_request()
File "/home/ia/.local/lib/python3.8/site-packages/flask/app.py", line 865, in dispatch_request
return self.ensure_sync(self.view_functions[rule.endpoint])(**view_args)  # type: ignore[no-any-return]
File "/home/ia/Documents/meus apps/screenshare2-test/app.py", line 61, in index
return render_template("index.html")
File "/home/ia/.local/lib/python3.8/site-packages/flask/templating.py", line 149, in render_template
template = app.jinja_env.get_or_select_template(template_name_or_list)
File "/home/ia/.local/lib/python3.8/site-packages/jinja2/environment.py", line 1084, in get_or_select_template
return self.get_template(template_name_or_list, parent, globals)
File "/home/ia/.local/lib/python3.8/site-packages/jinja2/environment.py", line 1013, in get_template
return self._load_template(name, globals)
File "/home/ia/.local/lib/python3.8/site-packages/jinja2/environment.py", line 972, in _load_template
template = self.loader.load(self, name, self.make_globals(globals))
File "/home/ia/.local/lib/python3.8/site-packages/jinja2/loaders.py", line 126, in load
source, filename, uptodate = self.get_source(environment, name)
File "/home/ia/.local/lib/python3.8/site-packages/flask/templating.py", line 65, in get_source
return self._get_source_fast(environment, template)
File "/home/ia/.local/lib/python3.8/site-packages/flask/templating.py", line 99, in _get_source_fast
raise TemplateNotFound(template)
jinja2.exceptions.TemplateNotFound: index.html
The debugger caught an exception in your WSGI application. You can now look at the traceback which led to the error.
To switch between the interactive traceback and the plaintext one, you can click on the "Traceback" headline. From the text traceback you can also create a paste of it. For code execution mouse-over the frame you want to debug and click on the console icon on the right side.

You can execute arbitrary Python code in the stack frames and there are some extra helpers available for introspection:

dump() shows all variables in the frame
dump(obj) dumps all that's known about the object
Brought to you by DON'T PANIC, your friendly Werkzeug powered traceback interpreter.
import React from 'react';

function Dashboard() {
  return (
    <div>
      <h1>Dashboard</h1>
    </div>
  );
}

export default Dashboard;