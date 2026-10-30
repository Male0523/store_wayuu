from rest_framework.authentication import SessionAuthentication


class SessionCookieAuthentication(SessionAuthentication):
    """Use a 401 challenge for expired or missing cookie-authenticated sessions."""

    def authenticate_header(self, request):
        return 'Session'
