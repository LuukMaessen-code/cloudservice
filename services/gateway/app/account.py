import os
import requests
from fastapi import HTTPException

def delete_account_logic(user, keycloak, history_api_url=None):
    username = getattr(user, "preferred_username", None) or getattr(user, "username", None)
    if not username:
        raise HTTPException(status_code=400, detail="Username not found in token")

    keycloak_url = keycloak.server_url
    realm = os.getenv("KEYCLOAK_REALM", "demo-chat")
    admin_realm = os.getenv("KEYCLOAK_ADMIN_REALM", realm)
    token_url = f"{keycloak_url}/realms/{admin_realm}/protocol/openid-connect/token"
    data = {
        "grant_type": "client_credentials",
        "client_id": os.getenv("KEYCLOAK_ADMIN_CLIENT_ID", "cloudservice-admin"),
        "client_secret": os.getenv("KEYCLOAK_ADMIN_CLIENT_SECRET", "KeQEW46uGbyRd7Jn8WH2BHPbBrWvOQaM"),
    }
    resp = requests.post(token_url, data=data)
    resp.raise_for_status()
    admin_token = resp.json()["access_token"]

    users_url = f"{keycloak_url}/admin/realms/{realm}/users"
    headers = {"Authorization": f"Bearer {admin_token}"}
    params = {"username": username}
    resp = requests.get(users_url, headers=headers, params=params)
    resp.raise_for_status()
    users = resp.json()
    if not users:
        raise HTTPException(status_code=404, detail="User not found in Keycloak")
    user_id = users[0]["id"]

    del_url = f"{keycloak_url}/admin/realms/{realm}/users/{user_id}"
    resp = requests.delete(del_url, headers=headers)
    if resp.status_code not in (204, 200):
        raise HTTPException(status_code=500, detail="Failed to delete user from Keycloak")

    history_url = history_api_url or os.getenv("HISTORY_API_URL", "http://history:9000")
    try:
        h_url = f"{history_url}/history/user/messages"
        h_headers = {"Authorization": f"Bearer {getattr(user, 'access_token', '')}"}
        requests.delete(h_url, headers=h_headers)
    except Exception:
        pass

    return {"status": "account and messages deleted"}
