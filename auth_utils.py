import streamlit as st
from firebase_config import auth

def signup(email, password):
    try:
        user = auth.create_user_with_email_and_password(email, password)
        return user
    except Exception as e:
        return str(e)

def login(email, password):
    try:
        user = auth.sign_in_with_email_and_password(email, password)
        return user
    except Exception as e:
        return str(e)

def logout():
    if "user" in st.session_state:
        del st.session_state["user"]
