import streamlit as st

def common_queries():
    st.subheader("Frequent Queries")
    st.text("")
    if st.button("Show open risk items", use_container_width=True):
        st.session_state.common_prompt = "Tell me about Jack"

    if st.button("Identify potential risk gaps", use_container_width=True):
        st.session_state.common_prompt = "Tell me about demand"

    if st.button("Share status of risk projects", use_container_width=True):
        st.session_state.common_prompt = "Tell me about Open Items"
