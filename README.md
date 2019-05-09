# DONATEapi

1. [Docker](#docker)
2. [Understanding the Docker-Kubernetes Configuration Files](#understanding-the-docker-kubernetes-configuration-files)
3. [The Application Configuration Files](#the-application-configuration-files)
4. [The Yelp Pre-commit Files](#the-yelp-pre-commit-files)
5. [The Requirements Files](#the-requirements-files)
6. [General Guidelines](#general-guidelines)
7. [Trobleshooting and Tests](#troubleshooting-and-tests)
8. [Setting Up JWT for Development](#setting-up-jwt-for-development)
9. [Alternative Command Line Guidelines](#alternative-command-line-guidelines)

## Docker

The application is configured to run inside a docker container, which allows for integration with Kubernetes. This gives us load balancing and on demand resource provisioning. Ensure that Docker is installed on the machine:
- $ docker version

Dropping the hyphens on `--version` gives us a bit more information about the installation. If Docker is not installed use:
- `$ pip install docker`

See [Application Foundations](https://github.com/NumbersUSA/DONATEapi/wiki/Application-Foundations) for links to some useful Docker documents.

## Understanding the Docker-Kubernetes Configuration Files

### The docker-compose.ymal file

The `docker-compose.yml` file contains definitions for the creation of several containers: web, redis, redis worker, cron, and the database. The web, worker, and cron require the same environment variables and the list is rather long. Instead of including shared variables they are imported from the `DONATEapi.configuration.conf.env` file in the `env_file` section for the container. The `env` file is just a list of tagged environment variables (see below).

The environment for the web container includes a variable `ENV` that should be set to either DEV, TEST, or DEFAULT (production). It also has a JWT token with a prefix that needs to be set to either `DEV`, `TEST`, or `DEFAULT` as well.

The build option `dockerfile` can be used to load a custom Docker file, e.g. `Dockerfile.User_name. In fact, this is what we do. It allows customization of the Dockerfile, which is a Git tracked file, without modifying it. It allows us to customize our own environment (see below).

### The Dockerfile

The Dockerfile buils the app. For example, it loads python:3.6-alpine, and the requirement files: `requirements.txt` and `private_requirements.txt`. Here is where `gevent` is insatlled and `gunicorn` run:
- `CMD ["gunicorn","-k","gevent","-b"," 0.0.0.0","-t","120","application.app:donation_app"]`

It is also where `FLASK_APP` and the `PYTHON_PATH` are set. It can also be used to pip install other libraries such as `ipdb`.

### The buildspec.yaml file

This is a DevOps file, and is used to build the instance to AWS.

## The Application Configuration Files

These are the application specific files that are used to build `app.config` in the function:
- DONATEapi.application.app.create_app.

### The config_loader.py file

This is a configuration file loader that can load variables from YAML files as well as tagged environment variables. The environment variables will update YAML values.

### The conf.yml file

The YAML configuration file has configurations for `DEFAULT` (production) as well as `DEV` and `TEST`. The variables are used to set application specific constants, such as the database URI.

### Local exported environment variables

The local environment variables will be used by the application and the `docker-compose.yml` file. These environment variables will update the `conf.yml` values if needed.

### The conf.env file

The `conf.env` is used by the `docker-compose.yml` and should point to the same environment: `DEV`, `TEST`, or `DEFAULT`. The environments in this file will end up taking priority over the local exported environment variables in the `docker-compose.py` file.

## The Yelp Pre-commit Files

### The pre-commit-config.yml

See [Pre-commit Hooks](https://github.com/NumbersUSA/DONATEapi/wiki/Pre-commit-Hooks) for further discussion. The pre-commit configuration sets up the hooks to run against the application. These hooks include: trailing-whitespace, end-of-file-fixer, check-docstring-first,check-json,check-added-large-files,check-yaml, debug-statements, detect-private-key, name-tests-test, requirements-txt-fixer, flake8, forbid-crlf, remove-crlf, forbid-tabs, remove-tabs, reorder-python-imports, and pylint.

#### The pylint-nusa-plugin.py file

PEP8 is the governing documentation for Python style. See the [Python NUSA Style Guide](https://github.com/NumbersUSA/DONATEapi/wiki/PEP-8-Conventions-and-Exeptions) for deviations from this guide.

One such deviation is whitespace around brackets, parentheses, and braces. The NUSA pylint plugin is a custom hook run by pylint to ensure that the NUSA whitespace style is followed.

Ensure that the `PYTHONPATH` is set for the plugin to be found.

## The Requirements Files

### The requirements.txt file

The standard Flask requirements file.

### The private_requirements.txt file

The private requirements file points to Flask common code modules in the NUSA repository. These include NUSA Flask JWT utilities, NUSA web storage utilities, and the NUSA parameter parser & filter constructor.

## General Guidelines
- Coordinate with DevOps to ensure that you use the correct name for the root folder. This is necessary for the Kubernetes build.
- Create the root folder.
- Clone the DONATEapi in the root folder.
- Make sure the `buildspec.yml` and `Dockerfile` were included in the cloning of the repository.
- Add the `docker-compose.yml` file.
- Add the application `conf.yml` and `conf.env` files.
- Add `pre-commit-config.yaml` and `pylint_nusa_plugin.py`.

To run the application use: `docker-compose up --build -d`. This will build all the containers. You can use: `docker-compose ps` to verify that the containers did indeed build. Try a REST call to:

```http://donation-apeters.numbersusa.internal/donation/heartbeat```

Or from the shell ( `docker-compose run web /bin/ash` ) `curl` the endpoint:

```http://donation-apeters.numbersusa.internal
curl -i -H "Accept: application/json" -H "Content-Type: application/json" -X GET http://donation-apeters.numbersusa.internal/donation/heartbeat
```

It should return a 200. You can use `docker logs --follow` to tail all the logs. The web container can be tailed separately like `docker logs --follow web`.

To stop a container use `docker stop <container_name>`, and to bring down the containers `docker-compose down`.

You will find some convenient bash functions ([aliases[) at the end of the [Appendix](https://github.com/NumbersUSA/DONATEapi/wiki/Appendix).

## Troubleshooting and Tests

An example will be useful.

- Run `docker-compose up -d`
- After the process finishes ensure that all containers started correctly.
    - `docker-compose ps`
- Run `docker stop <container_name>` for the web.
    - Open another bash terminal.
    - Run `docker-compose run --use-aliases -p 7777:8000 -e FLASK_APP=application/app.py web /bin/ash`
    - Put in a set trace ( pdb.set_trace() ) in controllers.donate just above submitting to redis.
    - At the shell run the app: `flask run -h 0.0.0.0 -p 8000`
- Run `docker stop <container_name>` for the worker.
    - Open another bash terminal.
    - Run `docker-compose run --use-aliases -p 7778:8000 -e FLASK_APP=application/app.py web /bin/ash`
    - Put in a set trace ( pdb.set_trace() ) in helpers.caging.redis_queue_caging before calling `categorize_donor()`.
    - At the shell run the RQ worker: `flask rq worker --worker-ttl 420`
- Now POST to `/donation/donate' with an appropriate payload. In the first shell the program execution stops at the web breakpoint that was set. Hitting continue (c) will resume execution and the program now stops at the `set_trace()` in caging. Hitting continue again finishes the online sale.

To run scripts/tests it is a bit different. You do not have to stop the web container.
- Enter: `docker-compose run web /bin/ash`
- This gets you to a shell prompt.
    - Run: `python -c "import scripts.manage_donate_endpoints;scripts.manage_donate_endpoints.paypal_etl()"`
    - Run: `python -m unittest discover -v`

## Setting Up JWT for Development

Ensure that the switch for bypassing JWT authorization is removed from the configuration environment file `conf.env`.

- Generate private key: `openssl genrsa -des3 -out private.pem 2048`.
- Generate its public key: `openssl rsa -in private.pem -outform PEM -pubout -out public.pem`.
- Get the unencrpyted private key: `openssl rsa -in private.pem -out private_unencrypted.pem -outform PEM`.
- Copy the private and public key to the token generator at `jwt.io`.
- Consider whether you need to add an entry to the Agent table.

The schema for our data looks like:

```
{
  "user_claims": {
    "drupal_uid": 1234,
    "ultsys_id": 5678,
    "name": "apeters",
    "roles": [
      "read",
      "superadmin",
      "admin",
      "basic_user"
    ]
  },
  "jti": "93d556e9-a459-47da-96d0-7287b61d1235",
  "exp": 99999999999,
  "fresh": false,
  "iat": 1540495862,
  "type": "access",
  "nbf": 1540495862,
  "identity": "apeters@numbersusa.com"
}
```

The token has 3 parts: algorithm, data, and signature. In the header of a protected endpoint (Administrative) ensure that this authorization token is included:

```
Authorization: Bearer eyJhbGciOi.eyJ1c2VyX2NsYWltcyI6eyJkcnVwYWxfdWlkIjo.VdVuUIzvclvZIUEoKzGjxp
```

Now, make sure that the public key is in docker-compose file in the web section under the `environment` entries. Notice that the notation switches a bit so a multi-line entry can be conveniently constructed. The key is indented.
```
    environment:
        ENV: DEV
        VIRTUAL_HOST: donation-apeters.numbersusa.internal
        NETWORK_ACCESS: tech_only
        DEV_JWT_PUBLIC_KEY: |-
          -----BEGIN PUBLIC KEY-----
          MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA3TS3Ks/zrCwm8GIL/Yts
          TQIDAQAB
          -----END PUBLIC KEY-----
```

Also remember to set the JWT in the `helpers.mock_jwt_functions.py` in the tests.

## Alternative Command Line Guidelines

```
> git clone https://github.com/NumbersUSA/DONATEapi.git
> virtualenv --python=python3 venv
> source venv/bin/activate
> pip install -r requirements.txt
> pip install -e git+ssh://git@github.com/NumbersUSA/nusa_filter_parser.git#egg=nusa-filter-parser
> pip install -e git+ssh://git@github.com/NumbersUSA/nusa_web_storage.git#egg=nusa-web_storage
```

### Redis Queue

Caging requires a Redis server, and in particular a donation (online/administrative) uses caging. The redis-server needs to be running and can be started on the command line if required. Start a worker if you want to see logging messages from the queue. The redis-server URL is set in the application configuration variables by specifying `app.config[ 'RQ_REDIS_URL' ]` ( see the `template_conf.yml` ). The `redis_queue.init_app( app )` takes care of the connection.

```
> redis-server --port 6379
> flask rq worker --worker-ttl 420
```

### Manage Cron Jobs

Status updates for Braintree transactions are managed by a scheduled cron job. Here are some commands to help manage
cron jobs and an example job to run the updater every 5 minutes and send information to a log file.

- Check to see if service is running: `> pidof cron`
- Start or restart the service: `> sudo service cron restart`
- View crontab (Chron Table) entries: `> crontab -l`
- Edit entries use: `> crontab -e`

Here is an example crontab entry to run manage_status_updates() every 5 minutes with output to the file cron.log:

```
*/5 * * * * cd /home/apeters/git/DONATE_updater && /home/apeters/git/DONATE_updater/venv/bin/python3 -c "import jobs.braintree;jobs.braintree.manage_status_updates()" >> /home/apeters/git/DONATE_updater/cron.log 2>&1
```

### Running the App

```
> python -m flask run
```

### Making Commits

The Wiki has more information on using Yelp's pre-commit hooks:

- [pre-commit](https://github.com/NumbersUSA/DONATEapi/wiki/Pre-commit-Hooks)

Begin by installing pre-commit hooks, and then run them manually using the second command. There are other ways of
setting up pre-commit hooks this is probably the simplest, and quickest.

```
> pip install pre-commit
> pre-commit run --all-files
```

A configuration file is required to specify what hooks will be run. The file is called `.pre-commit-config.yaml` and
needs to be in the project directory. It also expects a custom hook to be available in `pylint_nusa_plugin.py`.
Examples for both of these files can be found at:

- [.pre-commit-config.yaml](https://github.com/NumbersUSA/DONATEapi/wiki/Pre-commit-Hooks#the-pre-commit-configuration-file)
- [pylint_nusa_plugin.py](https://github.com/NumbersUSA/DONATEapi/wiki/Pre-commit-Hooks#the-custom-hooks)

# Production Requirements

- The API must create donation records.
  - Must support online donations.
  - Must support hand-entered donations (checks, cars, etc).
- The API must support creation of new users.
  - In the case where a new user looks like an existing one, it is sent to caging first.
- The API must support administrative actions.
  - This needs to support reallocating donations between NERF, Action, Support.
      - This includes updating exisiting subscriptions.
  - Must support partial or full refunds.
  - Must support recording bounced checks.

# General Layout of the Application

A few example files have been included to give the layout some depth.

```
|-- DOANATEapi
    |-- application
        |-- controllers
            |-- __init__.py
            |-- transaction.py
        |-- exceptions
            |-- __init__.py
            |-- exception_braintree.py
        |-- helpers
            |-- __init__.py
            |-- braintree_api.py
        |-- interprocess
            |-- __init__.py
        |-- models
            |-- __init__.py
            |-- transaction.py
        |-- resources
            |-- __init__.py
            |-- transaction.py
        |-- schemas
            |-- __init__.py
            |-- transaction.py
        |-- __init__.py
        |-- app.py
        |-- flask_essentials.py
    |-- configuration
        |-- __init__.py
        |-- template_conf.yml
        |-- config_loader.py
    |-- jobs
        |-- __init__.py
        |-- braintree.py
    |-- scripts
        |-- __init__.py
        |-- update_transaction_status.py
    |-- tests
        |-- helpers
            |-- __init__.py
            |-- braintree_mock_objects.py
        |-- resources
            |-- __init__.py
            |-- gear_wheel.png
        |-- __init__.py
        |-- test_braintree_online_donate.py
        |-- test_donate_models.py
    |-- README.md
    |-- requirements.txt
```

# API Endpoints

- /donation/agents, ( methods = [ GET ] )
- /donation/braintree/get-token, ( methods = [ GET ] )
- /donation/cage/, ( methods = [ POST ] )
- /donation/cage/\<string:ultsys_user_id\>, ( methods = [ PUT ] )
- /donation/donors/\<string:donor_type\>, ( methods = [ GET ] )
- /donation/campaigns/active/\<int:zero_or_one\>, ( methods = [ GET ] )
- /donation/campaigns/default/\<int:zero_or_one\>, ( methods = [ GET ] )
- /donation/campaigns/\<int:campaign_id\>, ( methods = [ GET ] )
- /donation/campaigns, ( methods = [ PUT, POST ] )
- /donation/campaigns/\<int:campaign_id\>/amounts, ( methods = [ GET ] )
- /donation/donate, ( methods = [ POST ] )
- /donation/enumeration/\<string:model\>/\<string:attribute\>, ( methods = [ GET ] )
- /donation/gifts, ( methods = [ GET ] )
- /donation/gifts/uuid_prefix/\<string:searchable_id_prefix\>, ( methods = [ GET ] )
- /donation/gift/user/\<int:user_id\>, ( methods = [ GET ] )
- /donation/gifts/date, ( methods = [ POST ] )
- /donation/gifts/given-to, ( methods = [ POST ] )
- /donation/gift/\<string:searchable_id\>/notes, ( methods = [ GET ] )
- /donation/gifts/\<int:searchable_id\>/transactions, ( methods = [ GET ] )
- /donation/gift/transaction, ( methods = [ POST ] )
- /donation/gifts/transactions, ( methods = [ GET, POST ] )
- /donation/heartbeat, ( methods = [ GET ] )
- /donation/gifts/user, ( methods = [ GET, POST ] )
- /donation/reallocate, ( methods = [ POST ] )
- /donation/record-bounced-check, ( methods = [ POST ] )
- /donation/refund, ( methods = [ POST ] )
- /donation/reprocess-queued-donors, ( methods = [ GET, POST ] )
- /donation/s3/csv/download, ( methods = [ GET ] )
- /donation/s3/csv/files, ( methods = [ GET ] )
- /donation/s3/campaign/\<int:campaign_id\>/file-path, ( methods = [ GET ] )
- /donation/transactions, ( methods = [ GET, POST ] )
- /donation/transaction/\<int:transaction_id\>, ( methods = [ GET ] )
- /donation/transactions/gross-gift-amount, ( methods = [ POST ] )
- /donation/transactions/csv, ( methods = [ GET ] )
- /donation/user, ( methods = [ GET, PUT, POST ] )
- /donation/void, ( methods = [ POST ] )
- /donation/webhook/braintree/subscription, ( methods = [ POST ] )
- /donation/gifts-not-yet-thanks, ( methods = [ GET, POST ] )

## Public API

- /donation/donate, ( methods = [ POST ] )

## Administrative API

- /donation/agents, ( methods = [ GET ] )
- /donation/braintree/get-token, ( methods = [ GET ] )
- /donation/cage/, ( methods = [ POST ] )
- /donation/cage/\<string:ultsys_user_id\>, ( methods = [ PUT ] )
- /donation/donors/\<string:donor_type\>, ( methods = [ GET ] )
- /donation/campaigns/active/\<int:zero_or_one\>, ( methods = [ GET ] )
- /donation/campaigns/default/\<int:zero_or_one\>, ( methods = [ GET ] )
- /donation/campaigns/\<int:campaign_id\>, ( methods = [ GET ] )
- /donation/campaigns, ( methods = [ PUT, POST ] )
- /donation/campaigns/\<int:campaign_id\>/amounts, ( methods = [ GET ] )
- /donation/enumeration/\<string:model\>/\<string:attribute\>, ( methods = [ GET ] )
- /donation/gifts, ( methods = [ GET ] )
- /donation/gifts/uuid_prefix/\<string:searchable_id_prefix\>, ( methods = [ GET ] )
- /donation/gift/user/\<int:user_id\>, ( methods = [ GET ] )
- /donation/gifts/date, ( methods = [ POST ] )
- /donation/gifts/given-to, ( methods = [ POST ] )
- /donation/gift/\<string:searchable_id\>/notes, ( methods = [ GET ] )
- /donation/gifts/\<int:searchable_id\>/transactions, ( methods = [ GET ] )
- /donation/gift/transaction, ( methods = [ POST ] )
- /donation/gifts/transactions, ( methods = [ GET, POST ] )
- /donation/heartbeat, ( methods = [ GET ] )
- /donation/gifts/user, ( methods = [ GET, POST ] )
- /donation/reallocate, ( methods = [ POST ] )
- /donation/record-bounced-check, ( methods = [ POST ] )
- /donation/refund, ( methods = [ POST ] )
- /donation/reprocess-queued-donors, ( methods = [ GET, POST ] )
- /donation/s3/csv/download, ( methods = [ GET ] )
- /donation/s3/csv/files, ( methods = [ GET ] )
- /donation/s3/campaign/\<int:campaign_id\>/file-path, ( methods = [ GET ] )
- /donation/transactions, ( methods = [ GET, POST ] )
- /donation/transaction/\<int:transaction_id\>, ( methods = [ GET ] )
- /donation/transactions/gross-gift-amount, ( methods = [ POST ] )
- /donation/transactions/csv, ( methods = [ GET ] )
- /donation/user, ( methods = [ GET, PUT, POST ] )
- /donation/void, ( methods = [ POST ] )
- /donation/webhook/braintree/subscription, ( methods = [ POST ] )
- /donation/gifts-not-yet-thanks, ( methods = [ GET, POST ] )

# Known Flaws and Solutions
