import os
import dotenv

dotenv.load_dotenv()

import json
import base64
from fastapi import FastAPI, WebSocket, HTTPException, WebSocketDisconnect
from twilio.twiml.voice_response import VoiceResponse, Start
from twilio.rest import Client

app = FastAPI()

# Twilio credentials
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")

# Twilio phone number
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

# Publicly accessible URL for the application
NGROK_URL = os.environ.get("NGROK_URL")

# Port to run the server on
PORT = 5002

# Phone number to call
TARGET_PHONE_NUMBER = "+15125651235"

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


@app.get("/")
def read_root():
    """Root endpoint, use to test if the server is running."""
    return {"Hello": "World"}


@app.get("/call")
def initiate_call():
    """Initiate a call to the target phone number."""
    response = VoiceResponse()
    start = Start()
    start.stream(url=f"wss://{NGROK_URL}/media")
    response.append(start)
    response.say("Hello, your call audio is being streamed.")
    twiml_response = str(response)
    print(twiml_response)

    call = client.calls.create(
        to=TARGET_PHONE_NUMBER, from_=TWILIO_PHONE_NUMBER, twiml=twiml_response
    )

    return f"Call initiated with SID: {call.sid}. TwiML: {twiml_response}"


@app.websocket("/media")
async def websocket_endpoint(websocket: WebSocket):
    """Handle incoming WebSocket connections from Twilio."""
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            event = message.get("event")

            if event == "media":
                payload = message["media"]["payload"]
                # print(f"Media message received: {message}")

                # Decoding the media payload
                try:
                    decoded_payload = base64.b64decode(payload)
                    print(f"Received {len(decoded_payload)} bytes of audio data")

                except Exception as decode_error:
                    print(f"Error decoding payload: {decode_error}")
                    continue

            elif event == "start":
                # Handle the start event...
                print("Start event received")

            elif event == "stop":
                # Handle the stop event...
                print("Stop event received")

            elif event == "connected":
                print("Connection event received")

            else:
                print(f"Unknown event: {event}")

    except WebSocketDisconnect as e:
        print(f"WebSocket disconnected with code: {e.code}")
    except Exception as e:
        print(f"Error occurred: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

    finally:
        try:
            await websocket.close()
        except RuntimeError as e:
            if "Unexpected ASGI message 'websocket.close'" in str(e):
                print("WebSocket already closed.")
            else:
                raise


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=PORT)
