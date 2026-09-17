import re


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def summarize_enquiry(name: str, message: str) -> str:
    cleaned_message = _clean(message)
    if len(cleaned_message) > 180:
        cleaned_message = f"{cleaned_message[:177].rstrip()}..."
    return f"Enquiry from {name.strip()}: {cleaned_message}"


def summarize_reply(sender: str, message: str) -> str:
    cleaned_message = _clean(message)
    if len(cleaned_message) > 180:
        cleaned_message = f"{cleaned_message[:177].rstrip()}..."
    sender_name = sender.split("<")[0].strip().strip('"') or "your client"
    # The task's required alert is kept at the beginning of every call.
    if cleaned_message:
        return f"You have received a new reply from your client. Reply from {sender_name}: {cleaned_message}"
    return "You have received a new reply from your client."
