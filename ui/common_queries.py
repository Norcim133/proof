import streamlit as st
import inspect
import logging

logger = logging.getLogger(__name__)

def custom_button_1():
    frame = inspect.currentframe()
    key = frame.f_code.co_name
    logger.info(f"{key}")
    query = "Show open risk items"
    if st.button(query, use_container_width=True, key=key):
        st.session_state.common_prompt = query

def custom_button_2():
    frame = inspect.currentframe()
    key = frame.f_code.co_name
    logger.info(f"{key}")
    query = "Identify potential risk gaps"
    if st.button(query, use_container_width=True, key=key):
        st.session_state.common_prompt = query

def custom_button_3():
    frame = inspect.currentframe()
    key = frame.f_code.co_name
    query = "Share status of risk projects"
    if st.button(query, use_container_width=True, key=key):
        st.session_state.common_prompt = query

def custom_button_4():
    frame = inspect.currentframe()
    key = frame.f_code.co_name
    query = "Flag financial issues"
    if st.button(query, use_container_width=True, key=key):
        st.session_state.common_prompt = query


def common_queries():
    st.subheader("Frequent Queries")
    st.text("")

    custom_button_1()
    custom_button_2()
    custom_button_3()
    custom_button_4()
