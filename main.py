import json
from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from google.oauth2.credentials import Credentials
from analyser_utils import extract_document_id
import pandas as pd
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow,Flow
from google.auth.transport.requests import Request
import os
import pickle
import gspread
from smart_engine import Smart_Engine
from analyser_utils import upload_csv, check_email_availability, signup
from database import Database
from slack import Slack


app = FastAPI(title="Excel Statistics",redoc_url=None)
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

slack_obj = Slack()

# In-memory database to store user data and chats
Database_obj = Database()
Database_obj.get_db()
Database_obj.create_database()
Database_obj.close_connection()
df = None
smart_engine = None
userId = None

@app.get("/")
async def read_root():
    return {"message": "Analysis - Analyse any Excel"}

@app.get("/SignUp")
async def sign_up(email, password, user_name):
    if(check_email_availability(user_email=email)):
        auth_key, user_id = signup(email=email,password=password,username=user_name)
        try:
            slack_obj.send_message(message=f"<!channel> user sign up - {email}")
        except:
            print("Slack error")
        return {"User_ID": user_id,"Auth_Key": auth_key}
    else:
        raise HTTPException(status_code=400, detail=str("Email already registered."))


@app.get("/login")
async def user_login(user_id, auth_key):
    global smart_engine, userId
    if(authenticate(user_id=user_id,auth_key=auth_key)):
        userId = user_id
        smart_engine = Smart_Engine(user_id=user_id)
        try:
            slack_obj.send_message(message=f"<!channel> user login - {userId}")
        except Exception as e:
            print("Slack error",e)
        return {"message": "Login successful."}
    return {"message": "Invalid Credentials."}


@app.post("/upload_csv")
async def upload_csv_endpoint(data_url):
    global df, smart_engine, userId
    if(userId is None):
        raise HTTPException(status_code=400, detail=str("Please login."))
    try:
        try:
            df = upload_csv(data_url=data_url)
        except:
            raise HTTPException(status_code=400, detail=str("Please check google sheet-link, grant necessary permissions."))
        smart_engine.set_dataframe(data_frame=df)
        try:
            slack_obj.send_message(message=f"<!channel> data_upload - {data_url}")
        except:
            print("Slack error")
        return {"message": "Upload successful."}
    except Exception as e:
        print("error",e)
        raise HTTPException(status_code=400, detail=str("Please login and upload google sheet-link"))


@app.get("/query_data/")
async def query_data_endpoint(query):
    global df, smart_engine, userId
    if(userId is None):
        raise HTTPException(status_code=400, detail=str("Please login."))
    try:
        results = smart_engine.Gemini_request(query=query)
        results_dict = results.to_dict(orient='records')
        try:
            slack_obj.send_message(message=f"<!channel> query:{query}\nResponse: {results_dict}")
        except Exception as e:
            print("Slack error",e)
        return JSONResponse(content=results_dict)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


def authenticate(user_id, auth_key):
    # In-memory database to store user data and chats
    Database_obj = Database()
    Database_obj.get_db()
    Database_obj.create_database()
    query = "SELECT user_id FROM user_records WHERE user_id = ? AND user_authkey = ?"
    values = (user_id, auth_key)
    user_id = Database_obj.query_data(query, values, )
    Database_obj.close_connection()
    try:
        user_id = user_id[0]["user_id"]
        return True
    except Exception as e:
        return False


