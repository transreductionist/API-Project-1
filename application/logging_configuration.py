"""The logging configuration for the application."""


def get_logging_configuration( wsgi_level, gunicorn_level, gunicorn=False ):
    """"Return a dictionary to build the logging configuration."""

    logging_configuration = {
        'version': 1,
        'formatters': {
            'default': { 'format': '%(levelname)-5s [%(filename)s:%(funcName)s:%(lineno)d] %(message)s' }
        },
        'handlers': {
            'wsgi': { 'class': 'logging.StreamHandler', 'stream': 'ext://sys.stdout', 'formatter': 'default' }
        },
        'loggers': {
            'wsgi': { 'level': wsgi_level, 'propagate': 'no', 'handlers': ['wsgi'] }
        },
        'root': {
            'level': wsgi_level,
            'handlers': [ 'wsgi' ]
        }
    }
    if gunicorn:
        logging_configuration[ 'handlers' ][ 'gunicorn.error' ] = {
            'class': 'logging.FileHandler', 'filename': 'errors.log', 'formatter': 'default'
        }
        logging_configuration[ 'loggers' ][ 'gunicorn.error' ] = {
            'level': gunicorn_level, 'propagate': 'no', 'handlers': [ 'gunicorn.error' ]
        }
        logging_configuration[ 'root' ][ 'handlers' ].append( 'gunicorn.error' )

    return logging_configuration
