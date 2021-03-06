"""Flask extension for rapid GitHub app development"""
import hmac
import logging

# from sanic import , _app_ctx_stack
from sanic.exceptions import abort
from sanic.response import text
from github3 import GitHub, GitHubEnterprise


LOG = logging.getLogger(__name__)


class GitHubApp(object):
    """The GitHubApp object provides the central interface for interacting GitHub hooks
    and creating GitHub app clients.

    GitHubApp object allows using the "on" decorator to make GitHub hooks to functions
    and provides authenticated github3.py clients for interacting with the GitHub API.

    Keyword Arguments:
        app {Flask object} -- App instance - created with Flask(__name__) (default: {None})
    """
    def __init__(self, app=None):
        self._hook_mappings = {}
        if app is not None:
            self.init_app(app)
        self._installation_clients = {}

    def init_app(self, app):
        """Initializes GitHubApp app by setting configuration variables.

        The GitHubApp instance is given the following configuration variables by calling on Flask's configuration:

        `GITHUBAPP_ID`:

            GitHub app ID as an int (required).
            Default: None

        `GITHUBAPP_KEY`:

            Private key used to sign access token requests as bytes or utf-8 encoded string (required).
            Default: None

        `GITHUBAPP_SECRET`:

            Secret used to secure webhooks as bytes or utf-8 encoded string (required).
            Default: None

        `GITHUBAPP_URL`:

            URL of GitHub API (used for GitHub Enterprise) as a string.
            Default: None

        `GITHUBAPP_ROUTE`:

            Path used for GitHub hook requests as a string.
            Default: '/'
        """
        self._app = app
        required_settings = ['GITHUBAPP_ID', 'GITHUBAPP_KEY', 'GITHUBAPP_SECRET']
        for setting in required_settings:
            if not app.config.get(setting):
                raise RuntimeError("Flask-GitHubApp requires the '%s' config var to be set" % setting)

        app.add_route(uri=app.config.get('GITHUBAPP_ROUTE', '/'),
                         handler=self._flask_view_func,
                         methods=['POST'])

    @property
    def id(self):
        return self._app.config['GITHUBAPP_ID']

    @property
    def key(self):
        key = self._app.config['GITHUBAPP_KEY']
        if hasattr(key, 'encode'):
            key = key.encode('utf-8')
        return key

    @property
    def secret(self):
        secret = self._app.config['GITHUBAPP_SECRET']
        if hasattr(secret, 'encode'):
            secret = secret.encode('utf-8')
        return secret

    @property
    def _api_url(self):
        return self._app.config['GITHUBAPP_URL']

    @property
    def client(self):
        """Unauthenticated GitHub client"""
        if self._app.config.get('GITHUBAPP_URL'):
            return GitHubEnterprise(self._app.config['GITHUBAPP_URL'])
        return GitHub()

    @property
    def payload(self, request):
        """GitHub hook payload"""
        if request and request.json and 'installation' in request.json:
            return request.json

        raise RuntimeError('Payload is only available in the context of a GitHub hook request')

    def installation_client(self, installation_id):
        """GitHub client authenticated as GitHub app installation"""
        client = self.client
        client.login_as_app_installation(self.key,
                                         self.id,
                                         installation_id)
        return client

    def app_client(self):
        """GitHub client authenticated as GitHub app"""
        client = self.client
        client.login_as_app(self.key,
                            self.id)
        return client

    @property
    def installation_token(self):
        return self.installation_client.session.auth.token

    def on(self, event_action):
        """Decorator routes a GitHub hook to the wrapped function.

        Functions decorated as a hook recipient are registered as the function for the given GitHub event.

        @github_app.on('issues.opened')
        def cruel_closer():
            owner = github_app.payload['repository']['owner']['login']
            repo = github_app.payload['repository']['name']
            num = github_app.payload['issue']['id']
            issue = github_app.installation_client.issue(owner, repo, num)
            issue.create_comment('Could not replicate.')
            issue.close()

        Arguments:
            event_action {str} -- Name of the event and optional action (separated by a period), e.g. 'issues.opened' or
                'pull_request'
        """
        def decorator(f):
            if event_action not in self._hook_mappings:
                self._hook_mappings[event_action] = [f]
            else:
                self._hook_mappings[event_action].append(f)

            # make sure the function can still be called normally (e.g. if a user wants to pass in their
            # own Context for whatever reason).
            return f

        return decorator

    def _flask_view_func(self, request):
        functions_to_call = []
        event = request.headers['X-GitHub-Event']
        action = request.json.get('action')

        self._verify_webhook(request)

        if event in self._hook_mappings:
            functions_to_call += self._hook_mappings[event]

        if action:
            event_action = '.'.join([event, action])
            if event_action in self._hook_mappings:
                functions_to_call += self._hook_mappings[event_action]

        if functions_to_call:
            for function in functions_to_call:
                function(request)
        return text("OK", 200)

    def _verify_webhook(self, request):
        signature = request.headers['X-Hub-Signature'].split('=')[1]

        mac = hmac.new(self.secret, msg=request.body, digestmod='sha1')

        if not hmac.compare_digest(mac.hexdigest(), signature):
            LOG.warning('GitHub hook signature verification failed.')
            abort(400)
