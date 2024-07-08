import streamlit as st
import pandas as pd
import sqlite3
from smart_engine import Smart_Engine
from analyser_utils import upload_csv, generate_authkey, hash_password, generate_id, extract_document_id, is_valid_email
from database import Database
from io import StringIO
from slack import Slack

slack_obj = Slack()
# In-memory database to store user data and chats
Database_obj = Database()
Database_obj.get_db()
Database_obj.create_database()

class Frontend:
    """
            A class representing all data query execution and operations.
    """
    def __init__(self, user_id):
        """
        Initializes the Database object.
        """
        self.user_id = user_id
        self.data_frame = None
        self.LLM_agent = None
        self.Smart_Engine = None


    def check_email_availability(self, user_email):
        query = "SELECT user_id FROM user_records WHERE user_email = ?"
        values = (user_email,)
        user_id = Database_obj.query_data(query, values)
        if(user_id is None or len(user_id)<1):
            return True
        return False

    # Function to sign up a new user
    def signup(self, email, username, password):
        authkey = generate_authkey()
        hashed_password = hash_password(password)
        user_id = generate_id()
        insertion_query = "INSERT INTO user_records (user_id, user_email, user_name, user_password_hash, user_authkey) VALUES (?, ?, ?, ?, ?)"
        insertion_values = (user_id, email, username, hashed_password, authkey,)
        Database_obj.execute_query(query=insertion_query,values=insertion_values)
        return authkey, user_id

    def authenticate(self,user_email, password):
        password = hash_password(password=password)
        query = "SELECT user_id FROM user_records WHERE user_email = ? AND user_password_hash = ?"
        values = (user_email, password)
        user_id = Database_obj.query_data(query, values,)
        try:
            user_id = user_id[0]["user_id"]
            st.session_state['user_id'] = user_id
            return True
        except Exception as e:
            return False

    def store_sheet(self, user_id, sheet_url, sheet_id):
        query = "INSERT INTO user_sheets (user_id, sheet_link, sheet_id) VALUES (?, ?, ?)"
        values = (user_id, sheet_url, sheet_id,)
        Database_obj.execute_query(query,values)
        return True

    def get_user_sheets(self,user_id):
        query = "SELECT sheet_link FROM user_sheets WHERE user_id = ?"
        values = (user_id,)
        sheet_urls = Database_obj.query_data(query,values,)
        return sheet_urls

    def store_chat(self,user_id, sheet_url, query, response, response_type):
        insertion_query = "INSERT INTO user_chats (user_id,sheet_link, query, response, response_type) VALUES (?, ?, ?, ?, ?)"
        values= (user_id,sheet_url, query, response,response_type,)
        rows = Database_obj.execute_query(insertion_query, values)
        return rows

    def get_user_chats(self,user_id, sheet_url):
        query= "SELECT query, response, response_type FROM user_chats WHERE user_id = ? AND sheet_link= ? ORDER BY created_at DESC"
        values = (user_id,sheet_url,)
        chats = Database_obj.query_data(query,values)
        return chats

    # Page navigation
    if 'page' not in st.session_state:
        st.session_state['page'] = 'login'

    def navigate_to(self,page):
        st.session_state['page'] = page
        st.rerun()

    def sign_up_page(self):
        st.title("Sign Up")
        # Signup form fields
        email = st.text_input("Email")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        confirm_password = st.text_input("Confirm Password", type="password")
        if st.button("Sign Up"):
            if email and username and password and confirm_password:
                if(is_valid_email(email=email)):
                    if password == confirm_password:
                        try:
                            if(self.check_email_availability(user_email=email)):
                                # Display loading status
                                with st.status("Signing-Up... Please wait."):
                                    authkey, user_id = Frontend_class.signup(email, username, password)
                                st.success(f"Signup successful! Your authkey is: {authkey}")
                                st.info(f"Your user ID is: {user_id}")
                                #st.write(f"Signup successful! Your authkey is: {authkey}")
                                #st.write(f"Your user ID is: {user_id}")
                                st.session_state['email'] = email
                                data = {
                                    "User ID" : [user_id],
                                    "Auth Key" : [authkey]
                                }
                                user_creds= pd.DataFrame(data)
                                styled_df = self.style_dataframe(user_creds)
                                st.dataframe(styled_df)
                                st.write("Please download/store these credentials to use API.")
                                try:
                                    slack_obj.send_message(message=f"<!channel> User Sign up - {email}")
                                except:
                                    print("Slack error")
                            else:
                                st.error("Error: This email is already registered.")
                        except sqlite3.IntegrityError:
                            st.error("Error: This email is already registered.")
                    else:
                        st.error("Error: Passwords do not match.")
                else:
                    st.error("Email is invalid.")
            else:
                st.error("Please Enter all values.")
        login_button = st.button("Login")
        if login_button:
            self.navigate_to('login')
    def login_page(self):
        st.title("Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        login_button = st.button("Login")
        sign_up_button = st.button('SignUp')
        if login_button:
            if self.authenticate(email, password):
                st.session_state['email'] = email
                try:
                    slack_obj.send_message(message=f"<!channel> User Login - {email}")
                except:
                    print("Slack error")
                self.navigate_to('upload')
            else:
                st.error("Invalid credentials")
        if sign_up_button:
            self.navigate_to('Signup')

    def upload_page(self):
        st.title("Upload Google Sheet URL or Select Existing")
        sheet_url = st.text_input("Google Sheet URL")
        sheet_id = extract_document_id(sheet_url)
        upload_button = st.button("Upload")
        if upload_button and sheet_url:
            try:
                already_uploaded = 0
                try:
                    self.store_sheet(st.session_state['user_id'], sheet_url, sheet_id)
                except:
                    already_uploaded  = 1
                    st.success("Google Sheet URL already Uploaded.")
                if(already_uploaded != 1):
                    st.success("Sheet URL uploaded successfully")
                st.session_state['selected_sheet'] = sheet_url
                st.write(f"Selected Sheet: {sheet_url}")
                st.session_state['Smart_Engine'] = Smart_Engine(user_id=st.session_state['user_id'])
                #self.Smart_Engine = Smart_Engine(user_id=self.user_id)
                # Display loading status
                with st.status("Uploading..."):
                    df = upload_csv(data_url=sheet_url)
                st.session_state['Smart_Engine'].get_LLM_Agent(data_frame=df)
                try:
                    slack_obj.send_message(message=f"<!channel> user data upload - {sheet_url}")
                except:
                    print("Slack error")
                self.navigate_to('chat')
            except Exception as e:
                print("error in uploading sheet",e)
                st.error("Google Sheet URL invalid. Please make sure required permissions are granted.")
        st.write("Previously Uploaded Sheets:")
        user_sheets = self.get_user_sheets(st.session_state['user_id'])
        selected_sheet = st.selectbox("Select a Google Sheet", [sheet['sheet_link'] for sheet in user_sheets])

        if selected_sheet:
            st.session_state['selected_sheet'] = selected_sheet
            st.write(f"Selected Sheet: {selected_sheet}")

        next_button = st.button("Next")
        if next_button and selected_sheet:
            st.session_state['Smart_Engine'] = Smart_Engine(user_id=st.session_state['user_id'])
            with st.status("Uploading..."):
                df = upload_csv(data_url=st.session_state['selected_sheet'])
            st.session_state['Smart_Engine'].get_LLM_Agent(data_frame=df)
            self.navigate_to('chat')
        back_button = st.button("Back")
        if back_button:
            self.navigate_to('login')

    def chat_page(self):
        selected_sheet = st.session_state['selected_sheet']
        st.title("Enter Query")
        query = st.text_input("Query")
        query_button = st.button("Submit")
        back_button = st.button("Back")
        if query_button and query:
            # Display loading status
            with st.status("Processing... Please wait."):
                # Placeholder for response generation logic
                response = st.session_state['Smart_Engine'].Gemini_request(query=query)
            if (isinstance(response, pd.DataFrame)):
                # Style and display the dataframe
                styled_df = self.style_dataframe(response)
                st.dataframe(styled_df)
                st.write("You can download this table as csv by hovering over the table and selecting download button on top right.")
                # Convert DataFrame to JSON string
                json_str = response.to_json(orient='records')
                self.store_chat(user_id= st.session_state['user_id'], sheet_url=st.session_state['selected_sheet'], query=query, response=json_str, response_type="dataframe")
                try:
                    slack_obj.send_message(message=f"<!channel> Query:{query}\nResponse:{json_str}")
                except:
                    print("Slack error")
            #response = f"Response for query: {query}"  # You will replace this with actual logic
            else:
                st.write(f"Response: {response}")
                try:
                    slack_obj.send_message(message=f"<!channel> Query:{query}\nResponse:{response}")
                except:
                    print("Slack error")
        # Display previous chats
        st.title("Chat History")
        chats = self.get_user_chats(st.session_state['user_id'],sheet_url=selected_sheet)
        for chat in chats:
            st.write(f"Query: {chat['query']}")
            response_type =  str(chat['response_type'])
            if(response_type == "dataframe"):
                # Convert JSON string to DataFrame
                df_from_json = pd.read_json(StringIO(chat['response']))
                # Style and display the dataframe
                styled_df = self.style_dataframe(df_from_json)
                st.dataframe(styled_df)
            else:
                st.write(f"Response: {chat['response']}")
            st.write("---")

        if back_button:
            self.navigate_to('upload')

    # Function to style the dataframe
    def style_dataframe(self,df):
        return df.style.set_table_styles(
            [{
                'selector': 'thead th',
                'props': [('background-color', 'lightblue'),
                          ('color', 'black'),
                          ('border', '1px solid black'),
                          ('font-size', '14px')]
            }, {
                'selector': 'tbody tr:nth-child(even)',
                'props': [('background-color', 'lightgrey')]
            }, {
                'selector': 'tbody tr:nth-child(odd)',
                'props': [('background-color', 'red')]
            }, {
                'selector': 'tbody td',
                'props': [('border', '1px solid black'),
                          ('font-size', '12px')]
            }]
        ).set_properties(**{
            'text-align': 'center',
            'border-collapse': 'collapse'
        })




Frontend_class= Frontend(user_id=None)
st.title("Analyser-360")

# Page navigation
if 'page' not in st.session_state:
    st.session_state['page'] = 'login'
    # Navigation to login page
if st.session_state['page'] == 'login':
    Frontend_class.login_page()
elif st.session_state['page'] == 'upload':
    Frontend_class.upload_page()
elif st.session_state['page'] == 'chat':
    Frontend_class.chat_page()
elif st.session_state['page'] == 'Signup':
    Frontend_class.sign_up_page()

