import pandas as pd
from urllib.parse import urlparse, parse_qs
import uuid
from fastapi import FastAPI, HTTPException, Depends, Request
from google.oauth2.credentials import Credentials
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow,Flow
from google.auth.transport.requests import Request
import os
import pickle
import gspread
import secrets
import hashlib
import re
from database import Database



# Function to generate authkey
def generate_authkey():
    return secrets.token_urlsafe(16)  # Generates a random URL-safe token

# Function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def generate_id():
    try:
        return uuid.uuid4().hex[:5]
    except Exception as e:
        return 0


def is_valid_email(email):
    """
    Validate the email address using regular expressions.

    :param email: Email address to validate
    :return: True if the email address is valid, otherwise False
    """
    regex = r'^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$'
    if re.match(regex, email):
        return True
    else:
        return False



SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# here enter the id of your google sheet
SAMPLE_SPREADSHEET_ID_input = '1ShbFMzRUuIJY8amTA58UuEHwsc3UmAnd_LzduBwcBhE'
SAMPLE_RANGE_NAME = 'A1:AA1000'

def upload_csv(data_url):
    print(data_url)
    Document_id = extract_document_id(url=data_url)
    sheet_url =data_url
    print(sheet_url)
    if not sheet_url:
        raise HTTPException(status_code=400, detail="Sheet URL is required")
    csv_url = sheet_url
    print(csv_url)
    global values_input, service
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "google_auth.json", SCOPES
            )
            creds = flow.run_local_server(port=5000)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    client = gspread.authorize(creds)
    spreadsheet = client.open_by_url(url=csv_url)
    worksheet = spreadsheet.get_worksheet(0)
    records_data = worksheet.get_all_records()
    records_df = pd.DataFrame.from_dict(records_data)
    df=records_df
    values_input = []
    if not values_input:
        print('No data found.')
    try:
        return df
    except Exception as e:
        print("error",e)




def extract_document_id(url):
    """
    Extracts the document ID from a Google Docs or Google Sheets URL.

    :param url: The URL of the Google document or sheet.
    :return: The document ID as a string or None if not found.
    """
    try:
        # Parse the URL
        parsed_url = urlparse(url)
        # Ensure the URL is from Google Docs or Sheets
        if "docs.google.com" not in parsed_url.netloc:
            return None
        # Split the path and look for the document ID
        path_parts = parsed_url.path.split('/')
        if 'd' in path_parts:
            doc_index = path_parts.index('d') + 1
            if doc_index < len(path_parts):
                return path_parts[doc_index]
        return None
    except Exception as e:
        print(f"Error extracting document ID: {e}")
        return None

def parse_google_sheet_url(sheet_url: str) -> str:
    if "edit" in sheet_url:
        csv_url = sheet_url.replace("/edit", "/export?format=csv")
    else:
        csv_url = sheet_url + "/export?format=csv"
    return csv_url


def check_email_availability(user_email):
    # In-memory database to store user data and chats
    Database_obj = Database()
    Database_obj.get_db()
    Database_obj.create_database()
    query = "SELECT user_id FROM user_records WHERE user_email = ?"
    values = (user_email,)
    user_id = Database_obj.query_data(query, values)
    Database_obj.close_connection()
    if(user_id is None or len(user_id)<1):
        return True
    return False

# Function to sign up a new user
def signup(email, username, password):
    # In-memory database to store user data and chats
    Database_obj = Database()
    Database_obj.get_db()
    Database_obj.create_database()
    authkey = generate_authkey()
    hashed_password = hash_password(password)
    user_id = generate_id()
    insertion_query = "INSERT INTO user_records (user_id, user_email, user_name, user_password_hash, user_authkey) VALUES (?, ?, ?, ?, ?)"
    insertion_values = (user_id, email, username, hashed_password, authkey,)
    Database_obj.execute_query(query=insertion_query,values=insertion_values)
    Database_obj.close_connection()
    return authkey, user_id