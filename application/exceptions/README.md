This directory contains the exception classes for handling errors throughout the application. It uses the
@app.errorhandler() decorator in app.py to handle the exceptions.

## exception_braintree.py

These are the Braintree exception handlers. The application (app.py) uses decorators to handle exceptions raised by
the code.

## exception_model.py

These are the Model exception handlers. The application (app.py) uses decorators to handle exceptions raised by
the code.

## exception_query_string.py

These are the exception classes to handle the OpenStack filter (serialize/deserialize) request.args parser.

## exception_ultsys_user.py

These are the exception classes to handle the Ultsys user endpoints: fid, updta, and create.
