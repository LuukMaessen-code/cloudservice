# Keycloak Setup for Cloudservice

This guide describes how to set up Keycloak for authentication and JWT protection in the cloudservice project, including configuration for the gateway-client, gateway-admin, and JWT validation for backend services.

---

## 1. Start Keycloak

- Use Docker Compose or your preferred method to start Keycloak.
- Example (from the project):
  ```sh
  docker-compose up keycloak
  ```
- Access Keycloak admin at: http://localhost:8080

---

## 2. Create a Realm

- Log in to the Keycloak admin console.
- Click **Add Realm**.
- Name: `demo-chat` (or your preferred name).

---

## 3. Create Clients

### A. gateway-client (for frontend)
- Go to **Clients** > **Create**.
- Client ID: `gateway-client`
- Client Protocol: `openid-connect`
- Root URL: `http://localhost:3000` (the frontend URL)
- Click **Save**.
- Set **Access Type**: `public`
- Set **Valid Redirect URIs**: `http://localhost:3000/*`
- Set **Web Origins**: `http://localhost:3000`
- Enable **Standard Flow**: ON
- Save changes.

### B. gateway-admin (for backend/admin)
- Go to **Clients** > **Create**.
- Client ID: `gateway-admin`
- Client Protocol: `openid-connect`
- Root URL: `http://localhost:8000` (your backend URL)
- Click **Save**.
- Set **Access Type**: `confidential`
- Set **Valid Redirect URIs**: `http://localhost:8000/*`
- Set **Web Origins**: `http://localhost:8000`
- Enable **Standard Flow**: ON
- Enable **Direct Access Grants**: ON (if using password grant)
- Save changes.
- Go to **Credentials** tab and copy the **Secret** (used by backend).

---

## 4. Create Users

- Go to **Users** > **Add User**.
- Fill in username, email, etc.
- After creating, go to **Credentials** tab and set a password.
- Optionally, enable **User Registration** in **Realm Settings** > **Login**.

---

## 5. Configure Token Settings

- In each client, ensure:
  - **Access Token Signature Algorithm**: `RS256`
  - **Include User Info in ID Token**: ON (optional)
- In **Realm Settings** > **Keys**, public keys are managed automatically.

---

## 6. JWT Validation in Backend Services

- Backend services (e.g., history_service) must validate JWTs from Keycloak.
- Use the following settings in the FastAPI service:
  - **Issuer**: `http://localhost:8080/realms/demo-chat`
  - **Audience**: `gateway-client` or `gateway-admin` (match the client used by the frontend/backend)
  - **Algorithms**: `RS256`
  - **JWKS URL**: `http://localhost:8080/realms/demo-chat/protocol/openid-connect/certs`
- Use `python-jose[cryptography]` to validate tokens.

---

## 7. Example: FastAPI JWT Validation

```python
from jose import jwt, JWTError
import requests

KEYCLOAK_REALM = "demo-chat"
KEYCLOAK_SERVER_URL = "http://localhost:8080"
KEYCLOAK_AUDIENCE = "gateway-client"  # or gateway-admin
KEYCLOAK_ISSUER = f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}"
KEYCLOAK_ALGORITHMS = ["RS256"]

# Fetch public key from Keycloak
resp = requests.get(f"{KEYCLOAK_SERVER_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs")
jwks = resp.json()["keys"]
public_key = jwt.algorithms.RSAAlgorithm.from_jwk(jwks[0])

def verify_token(token: str):
    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=KEYCLOAK_ALGORITHMS,
            audience=KEYCLOAK_AUDIENCE,
            issuer=KEYCLOAK_ISSUER,
        )
        return payload
    except JWTError:
        raise Exception("Invalid token")
```

---

## 8. Troubleshooting

- Ensure client IDs, redirect URIs, and web origins match the frontend/backend URLs.
- If you get 401 errors, check the audience and issuer in your JWT validation code.
- Make sure the Keycloak server is accessible from your backend service.

---

## 9. References
- Keycloak Docs: https://www.keycloak.org/docs/latest/
- FastAPI Keycloak Integration: https://github.com/marcospereirampj/fastapi-keycloak
- python-jose: https://python-jose.readthedocs.io/en/latest/
