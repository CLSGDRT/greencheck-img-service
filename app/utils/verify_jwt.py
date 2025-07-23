import os
import jwt
from jwt import PyJWKClient

JWKS_URL = os.getenv("USER_SERVICE_JWKS_URL")  # URL du JWKS fourni par user-service
AUDIENCE = os.getenv("JWT_AUDIENCE", "img-service")  # audience attendue (nom du service)

class JWTVerifier:
    def __init__(self, jwks_url=JWKS_URL, audience=AUDIENCE):
        self.jwks_client = PyJWKClient(jwks_url)
        self.audience = audience

    def verify_token(self, auth_header):
        if not auth_header or not auth_header.startswith("Bearer "):
            return None
        token = auth_header.split(" ")[1]

        try:
            signing_key = self.jwks_client.get_signing_key_from_jwt(token)
            data = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256"],
                audience=self.audience
            )
            return data  # dictionnaire des claims du JWT
        except Exception:
            return None
