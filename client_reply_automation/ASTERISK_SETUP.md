# Task 3 - Client Reply -> Automatic Call

## Final workflow

1. Python authenticates with Gmail API.
2. The application polls the client's Gmail address for a new message.
3. The latest message ID is stored in `reply_state.json` so the same reply is not called twice.
4. When a new reply is detected, Python checks the current time with `pytz` using `Asia/Kolkata`.
5. If the time is between 09:00 (inclusive) and 18:00 (exclusive), a local TTS WAV file is created.
6. The spoken message starts with:
   `You have received a new reply from your client.`
7. Python copies the WAV into the Asterisk sound directory.
8. Python sends an Asterisk AMI Originate request.
9. Asterisk routes the call through the configured channel/dialplan and plays the WAV.

Outside working hours, the reply is recorded as processed and no call is made.

## First run

Set these environment variables in PowerShell:

```powershell
# Optional: limit detection to this sender. Leave empty to recognize any
# received inbox email that is not sent by the monitored Gmail account.
$env:CLIENT_EMAIL="client@example.com"
$env:MY_PHONE="+91XXXXXXXXXX"
$env:TIMEZONE="Asia/Kolkata"
$env:WORK_START="9"
$env:WORK_END="18"
$env:POLL_SECONDS="30"

$env:ASTERISK_SOUND_DIR="C:\path\shared\asterisk_sounds"
$env:ASTERISK_AMI_HOST="127.0.0.1"
$env:ASTERISK_AMI_PORT="5038"
$env:ASTERISK_AMI_USERNAME="admin"
$env:ASTERISK_AMI_SECRET="change-me"
$env:ASTERISK_CHANNEL="Local/{phone}@from-internal"
```

Then run:

```powershell
python app.py
```

On the first Gmail run, a browser window opens for Google OAuth. After authorization, `token.pickle` is reused. The client is recognized from the received email's `From` header; `CLIENT_EMAIL` only narrows the search when it is set.

## Test without a real phone call

You can leave `ASTERISK_AMI_HOST` unset. The system will still:

- detect the new Gmail reply;
- check working hours;
- generate the local voice file;
- copy the file to `ASTERISK_SOUND_DIR`.

The response/log will say that the audio is ready rather than claiming that a phone call was made.

## Manual one-time check

With the Flask app running, open:

`http://127.0.0.1:5000/check-reply`

This performs one Gmail check instead of waiting for the polling interval.

## Important Asterisk note

`MY_PHONE` is not automatically callable just because it is a mobile number. Asterisk needs a configured SIP/telephony provider or a local test endpoint/dialplan that can route the call. The Python side is responsible for detecting the reply, generating the audio and sending the AMI originate request; Asterisk/provider handles the actual telephony connection.
