"""
scripts/tiktok_auth.py
Run this ONCE locally to get your TikTok access + refresh tokens.
Starts a local server on port 8080 to catch the OAuth callback.

Usage:
  python scripts/tiktok_auth.py

Then add the printed tokens to your GitHub repo secrets.
"""

import os
import json
import secrets
import webbrowser
import urllib.parse
from http.server import HTTPServer, BaseHTTPRequestHandler
import requests

CLIENT_KEY    = os.environ["TIKTOK_CLIENT_KEY"]
CLIENT_SECRET = os.environ["TIKTOK_CLIENT_SECRET"]
REDIRECT_URI  = "http://localhost:8080/callback"
SCOPES        = "video.upload,video.publish,user.info.basic"

AUTH_URL      = "https://www.tiktok.com/v2/auth/authorize/"
TOKEN_URL     = "https://open.tiktokapis.com/v2/oauth/token/"

auth_code     = None
state_token   = secrets.token_urlsafe(16)


class CallbackHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        global auth_code
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)

        if "code" in params:
            auth_code = params["code"][0]
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"<h1>Auth complete! You can close this tab.</h1>")
        else:
            self.send_response(400)
            self.end_headers()
            self.wfile.write(b"<h1>Auth failed. Check terminal.</h1>")

    def log_message(self, *args):
        pass  # suppress server logs


def main():
    auth_params = {
        "client_key":     CLIENT_KEY,
        "scope":          SCOPES,
        "response_type":  "code",
        "redirect_uri":   REDIRECT_URI,
        "state":          state_token,
    }
    url = AUTH_URL + "?" + urllib.parse.urlencode(auth_params)

    print("\n══════════════════════════════════════════")
    print("  General V — TikTok OAuth Setup")
    print("══════════════════════════════════════════")
    print(f"\nOpening TikTok auth in your browser...")
    print(f"If it doesn't open, visit:\n  {url}\n")
    webbrowser.open(url)

    print("Waiting for callback on http://localhost:8080/callback ...")
    server = HTTPServer(("localhost", 8080), CallbackHandler)
    server.handle_request()  # handles one request then stops

    if not auth_code:
        print("ERROR: No auth code received.")
        return

    print(f"\nAuth code received. Exchanging for tokens...")

    token_resp = requests.post(TOKEN_URL, data={
        "client_key":     CLIENT_KEY,
        "client_secret":  CLIENT_SECRET,
        "code":           auth_code,
        "grant_type":     "authorization_code",
        "redirect_uri":   REDIRECT_URI,
    })
    token_resp.raise_for_status()
    token_data = token_resp.json()

    access_token  = token_data["access_token"]
    refresh_token = token_data["refresh_token"]
    expires_in    = token_data.get("expires_in", 86400)

    print("\n══════════════════════════════════════════")
    print("  SUCCESS — Add these to GitHub Secrets:")
    print("══════════════════════════════════════════")
    print(f"\nTIKTOK_ACCESS_TOKEN:\n  {access_token}")
    print(f"\nTIKTOK_REFRESH_TOKEN:\n  {refresh_token}")
    print(f"\nToken expires in: {expires_in // 3600}h")
    print("\nRefresh tokens last 365 days.")
    print("The pipeline auto-refreshes the access token each run.\n")

    # Save to local .env.tiktok for reference
    with open(".env.tiktok", "w") as f:
        f.write(f"TIKTOK_ACCESS_TOKEN={access_token}\n")
        f.write(f"TIKTOK_REFRESH_TOKEN={refresh_token}\n")
    print("Also saved to .env.tiktok (DO NOT commit this file)")


if __name__ == "__main__":
    main()
