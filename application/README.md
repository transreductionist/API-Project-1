This directory contains the primary logical structure of the application itself.

This application requires several subcomponents:

Resources -- Containing the endpoints and similar, these properly encapsulate requests, feed params to controllers,
and await the response for packaging to the requester.

Controllers -- The highest level of logic within this application, these are called upon by resources to accept
parameters, run highly abstracted logical decisions, and hand off complexities to helpers.

Helpers -- The next lowest level of code, helpers get into the nitty-gritty and difficult-to-read code, utilizing
schemas and models to interact with foreign APIs and native data tables, caches, and the like.

Models -- Herein lies each individual SQLAlchemy descriptor for database tables that serve this project.

Schemas -- Providing extra powers to models such as type checking and required fields checking.
