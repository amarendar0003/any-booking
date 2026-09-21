"""
Firebase App Check verification for the /api/ surface.

Confirms a request came from a genuine build of the AnyBooking app
(iOS/Android/web) rather than a script hitting the API directly, by
verifying the `X-Firebase-AppCheck` token the Firebase client SDK attaches
to each request (see lib/main.dart).

Enforcement is opt-in: it activates automatically once
FIREBASE_APP_CHECK_PROJECT_NUMBER is set (see settings.py), so local dev
and CI don't need a Firebase project. Until a project is configured, this
middleware is a no-op.

Docs: https://firebase.google.com/docs/app-check/custom-resource-backend
"""
import logging

import jwt
from django.conf import settings
from django.http import JsonResponse

logger = logging.getLogger(__name__)

JWKS_URL = 'https://firebaseappcheck.googleapis.com/v1/jwks'
ISSUER_PREFIX = 'https://firebaseappcheck.googleapis.com/'

_jwks_client = None


def _get_jwks_client():
    global _jwks_client
    if _jwks_client is None:
        # cache_keys avoids fetching Google's JWKS on every request.
        _jwks_client = jwt.PyJWKClient(JWKS_URL, cache_keys=True, lifespan=21600)
    return _jwks_client


def verify_app_check_token(token, project_number):
    """Returns the decoded claims, or raises jwt.PyJWTError if invalid."""
    signing_key = _get_jwks_client().get_signing_key_from_jwt(token)
    return jwt.decode(
        token,
        signing_key.key,
        algorithms=['RS256'],
        audience=f'projects/{project_number}',
        issuer=f'{ISSUER_PREFIX}{project_number}',
    )


class AppCheckMiddleware:
    """Rejects /api/ requests without a valid Firebase App Check token.

    No-op unless settings.APP_CHECK_ENFORCED is True.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if settings.APP_CHECK_ENFORCED and request.path.startswith('/api/'):
            token = request.headers.get('X-Firebase-AppCheck')
            if not token:
                return JsonResponse({'detail': 'Missing App Check token.'}, status=401)
            try:
                verify_app_check_token(token, settings.FIREBASE_APP_CHECK_PROJECT_NUMBER)
            except jwt.PyJWTError as exc:
                logger.warning('Rejected request with invalid App Check token: %s', exc)
                return JsonResponse({'detail': 'Invalid App Check token.'}, status=401)
        return self.get_response(request)
