import streamlit as st

from ui.chatbot import chatbot
from ui.common_queries import common_queries
from ui.indices import indices
from ui.sources import sources


def st_side_bar():
    with st.sidebar:

        indices()

        st.divider()

        common_queries()
        #dashboard()


def app_body():

    st.logo(
        "assets/horizontal_NB.png",
        size="large",
        icon_image="assets/square_NB.png"
    )

    st_side_bar()

    c1, c2 = st.columns([2,1], vertical_alignment="top", gap="large")
    with c1:
        chatbot()

    with c2:
        #file_manager()
        sources()
