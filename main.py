from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel
import uuid
from google.cloud import dialogflow_v2beta1 as dialogflow
import google.auth
from googleapiclient.discovery import build
from datetime import datetime, timedelta
from google.protobuf.json_format import MessageToDict
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime, timedelta
from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import json

# Initialize Jinja2Templates
templates = Jinja2Templates(directory="templates")

app = FastAPI()

# Define allowed origins (modify as needed)
origins = ["*"]  # Change this to restrict access, e.g., ["https://yourfrontend.com"]

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # List of allowed domains
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods (GET, POST, etc.)
    allow_headers=["*"],  # Allows all headers
)

# Configurations
PROJECT_ID = "dentalchatbot-adc9"
CREDENTIALS_PATH = "dentalchatbot-adc9-b73d40f475f4.json"
CALENDAR_ID = "inyong1995@gmail.com"

class ChatMessage(BaseModel):
    session_id: str
    text: str

def detect_intent(session_id: str, text: str):
    """Sends a message to Dialogflow and returns the response."""
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(PROJECT_ID, session_id)

    text_input = dialogflow.types.TextInput(text=text, language_code="th-TH")
    query_input = dialogflow.types.QueryInput(text=text_input)
    response = session_client.detect_intent(session=session, query_input=query_input)
    
    return response

def create_calendar_event(date, time):
    """Creates an event in Google Calendar."""
    scopes = ["https://www.googleapis.com/auth/calendar"]
    
    # Load service account credentials from the environment variable
    
    service_account_info = json.loads(os.environ['GOOGLE_CREDENTIALS'])
    print("os.environ: ", os.environ['GOOGLE_CREDENTIALS'])
    print("service_account_info: ", service_account_info)
    credentials = service_account.Credentials.from_service_account_info(service_account_info, scopes=scopes)
    
    service = build("calendar", "v3", credentials=credentials)

    end_time = (datetime.fromisoformat(f"{date}T{time}") + timedelta(minutes=30)).isoformat()

    event = {
        "summary": "Dental Appointment",
        "start": {"dateTime": f"{date}T{time}", "timeZone": "Asia/Bangkok"},
        "end": {"dateTime": end_time, "timeZone": "Asia/Bangkok"},
    }

    service.events().insert(calendarId=os.environ['CALENDAR_ID'], body=event).execute()

@app.post("/chat")
async def chat_endpoint(msg: ChatMessage):
    """Handles user messages."""
    response = detect_intent(msg.session_id, msg.text)
    intent_name = response.query_result.intent.display_name
    response_json = MessageToDict(response._pb)
    
    if intent_name == "appointment_booking - custom.date_time":
        parameters = response_json["queryResult"].get("parameters", {})
        if 'date-time' in parameters:
            date_time = parameters['date-time']
        else:
            return {"response": "Missing date or time"}

        date_time_obj = datetime.fromisoformat(date_time)
        date = date_time_obj.date().isoformat()
        time = date_time_obj.time().isoformat()

        create_calendar_event(date, time)
    
    return {"response": response.query_result.fulfillment_text}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request, "title": "My FastAPI Website"})