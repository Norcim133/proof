import streamlit as st
import logging

logger = logging.getLogger(__name__)

def reg_toggle():

    st.subheader('Regulatory Checks')

    if st.checkbox('Include All Regulations'):
        st.session_state["reg_prompt"] = True
    if st.checkbox('Include Cyber Regulations'):
        st.session_state["reg_prompt"] = True
    if st.checkbox('Include Operational Risk Regulations'):
        st.session_state["reg_prompt"] = True