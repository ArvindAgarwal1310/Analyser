import os
import google.generativeai as genai
import pandas as pd
import re
from pandasai.llm.google_gemini import GoogleGemini
from pandasai import Agent
from pandasai import SmartDataframe
import pandasql as psql

class Smart_Engine:
    """
        A class representing all data query execution and operations.
        """

    def __init__(self,user_id):
        """
        Initializes the Database object.
        """
        self.user_id = user_id
        self.GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]
        self.agent = GoogleGemini(api_key=self.GEMINI_API_KEY)
        self.LLM_agent =None
        self.df = None
    def set_dataframe(self, data_frame):
        self.df = data_frame
        return True
    def get_LLM_Agent(self, data_frame):
        pd.set_option('display.max_colwidth', None) #get entire pandas dataframe without ellipisis
        self.df=data_frame
        self.LLM_agent = Agent(data_frame)
        self.sdf = SmartDataframe(data_frame)


    def chat_with_LLM_agent(self,query):
        input_text = f"Analyse dataframe completely as a csv; answer this query based on it DO NOT PROVIDE CODE AND GIVE DIRECT ANSWER AND AN EXPLAINATION IF APPLICABLE: {query}"
        response =  self.sdf.chat(str(query))
        print(response, type(response))
        return response

    def fill_empty_column_names(self, df):
        """
        Fill empty column names in a DataFrame with unique values.

        :param df: The input DataFrame.
        :return: DataFrame with filled column names.
        """
        # Generate new unique column names for empty string or None column names
        unique_column_names = {col: f"Unnamed_{i}" for i, col in enumerate(df.columns) if col == '' or pd.isnull(col)}
        # Rename columns in the DataFrame
        df = df.rename(columns=unique_column_names)
        return df

    def extract_sql_query(self, text):
        """
        Extracts the SQL query from a given text block.

        :param text: A string containing the SQL query.
        :return: Extracted SQL query as a string.
        """
        # Define the regex pattern to match SQL queries
        sql_pattern = re.compile(r'```(.*?)```', re.DOTALL | re.IGNORECASE)

        # Search for the SQL query in the text
        match = sql_pattern.search(text)

        if match:
            # Extract the SQL query
            return match.group(1).strip()
        else:
            return None

    def get_column_info(self, df):
        """
        Get column names and their data types from a pandas DataFrame.
        Convert columns with date-like names or values to datetime format.

        :param df: pandas DataFrame
        :return: A dictionary with column names as keys and data types as values
        """
        date_keywords = ['date', 'time', 'timestamp']  # Keywords to identify date columns
        if(self.df is None): #Conditional check for DataFrame
            self.df = df
        # Detect and convert date-like columns

        for col in self.df.columns:
            if any(keyword in col.lower() for keyword in date_keywords):
                try:
                    self.df[col] = pd.to_datetime(self.df[col], errors='coerce')
                except Exception as e:
                    print("Error in datetime conversion",e)
        # Create the column info dictionary
        column_info = {col: str(dtype) for col, dtype in self.df.dtypes.items()}
        return column_info

    def Gemini_request(self, query):
        try:
            genai.configure(api_key=self.GEMINI_API_KEY)
            # Set up the model
            generation_config = {
                "temperature": 0.8,
                "top_p": 1,
                "top_k": 1,
                "max_output_tokens": 2048,
            }
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_MEDIUM_AND_ABOVE"
                },
            ]
            model = genai.GenerativeModel(model_name="gemini-1.5-pro",
                                          generation_config=generation_config,
                                          safety_settings=safety_settings, )

            convo = model.start_chat(history=[])
            # Adjust pandas display settings
            pd.set_option('display.max_colwidth', None)
            try:
                print("Average",self.df['Price'].mean())
            except Exception as e:
                print("Trivial error",e)
            #self.df.to_string(index=False)
            # Convert DataFrame to JSON
            print(self.df)
            self.df = self.fill_empty_column_names(df=self.df)
            column_names = self.get_column_info(df=self.df)
            sample_data = self.df.head(4)
            print(column_names)
            input_text = f"this is a pandas dataframe: \n\nA dictionary with column names as keys and data types as values:\n{column_names}\n\nSample Data Rows:{sample_data}\n\nAnalyse it completely as a csv with respect to the column name and data-type and data format stored as per the sample data row I provided--\n{sample_data}\n; answer this return query based on column names, sample data and based on it PROVIDE SQL query to perform the operation->JUST RETURN THE SQL query with the pandas dataframe variable name to be `df` AND NOT ANY OTHER THING IN IT, THE OUTPUT WILL BE DIRECTLY EXEcuted using exec: QUESTION-> {query}"
            str(convo.send_message(input_text))

            print(str(convo.last.text))
            ans = str(convo.last.text)
            ans = ans.replace("sql","")
            ans = self.extract_sql_query(text=ans)
            print("ANS", ans)
            #print("dataframe", df,type(df))
            a=None
            df = self.df
            try:
                a=(psql.sqldf(query=ans, env=locals()))
                return a
                #print(self.df.query('Price.mean()'))
            except Exception as e:
                print("error",e)
            print(a)
        except Exception as e:
            print("Error in Gemini_request", e)
