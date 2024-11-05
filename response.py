#
# user_id = 1000
# from helper_functions import load_faiss_vector_db,query_retrieval_qa
#
# vect_db = load_faiss_vector_db(user_id)
# query = "give me the certifications of sriram vasudeven?"
# category = "LINKEDIN"  # Optional; if no category, pass None
# # category = None
# output = query_retrieval_qa(query,category,vect_db)
# print(output)


import streamlit as st
import os
from typing import List, Dict
import random
from dotenv import load_dotenv
# from haystack_integrations.components.generators.google_ai import GoogleAIGeminiGenerator
# from app import responseGenerator

load_dotenv()

## INITIALIZE SESSION STATE
if "messages" not in st.session_state:
    st.session_state.messages = [{"role": "assistant", "response": "Hi 👋, How may I assist you today?"}]

if 'source' not in st.session_state:
    st.session_state.source = {"active": False}

if 'metadata' not in st.session_state:
    st.session_state.metadata = [{}]

if 'session_id' not in st.session_state:
    st.session_state.session_id = None

if 'knowledge_base' not in st.session_state:
    st.session_state.knowledge_base = None

## INITIALIZE VARIABLES
kb_dict = {"Arxiv KB": "AWS_KNOWLEDGE_BASE_ID"}
kb_selected = ""


## FUNCTION TO CLEAR CHAT HISTORY
def clear_chat_history():
    st.session_state.messages = [{"role": "assistant", "response": "Hi 👋, How may I assist you today?"}]


def cancel_source():
    st.session_state.source = {"active": False}


def source_callback(metadata: List[Dict]):
    st.session_state.metadata = metadata
    st.session_state.source = {"active": True}


### HEADER COMPONENTS
st.title("Search APP")
st.subheader(f"AI-Powered Search Assistant")
st.caption(f"Uses the {st.session_state.knowledge_base} Knowledge Base")
st.divider()

### SIDEBAR COMPONENTS
with st.sidebar:
    st.header("Settings")
    kb_selected = st.selectbox(
        "Choose a knowledge base",
        (list(kb_dict.keys()))
    )
    st.session_state.knowledge_base = os.getenv(kb_dict[kb_selected])
    st.write("You selected:", kb_selected)

    if st.session_state.source["active"]:
        st.divider()
        container = st.container(border=True)
        container.title("Source details")
        container.divider()
        metadata = st.session_state.metadata
        container.subheader("Name:")
        container.write(metadata[0]["documentName"])
        container.subheader("Content:")
        container.write(metadata[0]["documentContent"])
        container.subheader("Location:")
        container.write(metadata[0]["documentLocation"])
        container.subheader("URL:")
        container.write(metadata[0]["preSignedUrl"])
        container.button('cancel', on_click=cancel_source)

    st.divider()
    st.sidebar.button('Clear Chat History', on_click=clear_chat_history)

## DISPLAY CHAT HISTORY
for message in st.session_state.messages:

    with st.chat_message(message["role"]):

        if message["role"] != "assistant":
            st.markdown(message["response"])
        else:
            response = message["response"]
            if isinstance(response, str):
                try:
                    response = eval(response)
                except Exception as e:
                    response = {"summary": message["response"]}
            st.markdown(response["summary"])
            if response.get("metadata") and len(response["metadata"]) > 0 and response["metadata"][0][
                "documentContent"]:
                st.button("ℹ", key=f"{hash(response['summary'])}",
                          on_click=lambda r=response["metadata"]: source_callback(r))

### CHAT
if prompt := st.chat_input("Ask anything..."):

    st.session_state.messages.append({"role": "user", "response": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    response_instance = st.chat_message("assistant")
    with response_instance:
        with st.spinner("Analyzing..."):
            response = responseGenerator(query=prompt, session_id=st.session_state.session_id,
                                         knowledge_base_id=st.session_state.knowledge_base)

    with response_instance:
        st.markdown(response["summary"])

        if response.get("metadata") and len(response["metadata"]) > 0 and response["metadata"][0]["documentContent"]:
            st.button("ℹ", key=f"{hash(response['summary'])}",
                      on_click=lambda r=response["metadata"]: source_callback(r))
        st.session_state.session_id = response['sessionId']

        st.session_state.messages.append({"role": "assistant", "response":response})
