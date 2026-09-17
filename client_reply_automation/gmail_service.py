import os
import pickle
from email.utils import parsedate_to_datetime

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def get_gmail_service():
    creds = None
    token_path = os.getenv("GMAIL_TOKEN_FILE", "token.pickle")
    credentials_path = os.getenv("GMAIL_CREDENTIALS_FILE", "credentials.json")

    if os.path.exists(token_path):
        with open(token_path, "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(token_path, "wb") as token:
            pickle.dump(creds, token)

    return build("gmail", "v1", credentials=creds)


def _header(headers, name):
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value", "")
    return ""


def get_latest_client_reply(service, client_email):
    """Return the newest received message, optionally limited to one sender."""
    query = "in:anywhere -from:me"
    if client_email:
        query += f" from:{client_email}"
    result = service.users().messages().list(
        userId="me",
        q=query,
        maxResults=20,
    ).execute()
    messages = result.get("messages", [])
    if not messages:
        return None

    candidates = [
        service.users().messages().get(userId="me", id=item["id"], format="full").execute()
        for item in messages
    ]
    message = max(candidates, key=lambda item: int(item.get("internalDate", "0")))
    headers = message.get("payload", {}).get("headers", [])
    body = _extract_text(message.get("payload", {}))

    internal_ms = int(message.get("internalDate", "0"))
    return {
        "id": message["id"],
        "thread_id": message.get("threadId", ""),
        "from": _header(headers, "From"),
        "subject": _header(headers, "Subject"),
        "date": _header(headers, "Date"),
        "body": body,
        "internal_date": internal_ms,
    }


def _extract_text(payload):
    import base64

    mime_type = payload.get("mimeType", "")
    data = payload.get("body", {}).get("data")
    if data and mime_type == "text/plain":
        return base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")

    for part in payload.get("parts", []) or []:
        text = _extract_text(part)
        if text:
            return text

    if data:
        try:
            return base64.urlsafe_b64decode(data + "===").decode("utf-8", errors="replace")
        except Exception:
            return ""
    return ""
