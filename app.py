"""
Simple Streamlit Chatbot for Local LLM Communication

This module provides a clean web interface for chatting with a local LLM
using OpenAI-compatible API endpoints.

Requirements:
    pip install streamlit openai

Usage:
    streamlit run app.py
"""

import streamlit as st
from openai import OpenAI
from typing import Dict, List


def initialize_session_state() -> None:
    """
    Initialize Streamlit session state variables.
    
    Creates necessary session state variables if they don't exist:
    - messages: List of chat messages
    - client: OpenAI client instance
    """
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "client" not in st.session_state:
        st.session_state.client = None


def create_openai_client(base_url: str, api_key: str) -> OpenAI:
    """
    Create an OpenAI client instance configured for local LLM.
    
    Args:
        base_url: The base URL of the local LLM API endpoint
        api_key: API key for authentication (use 'dummy' for local models)
    
    Returns:
        OpenAI: Configured OpenAI client instance
    """
    return OpenAI(base_url=base_url, api_key=api_key)


def display_chat_messages() -> None:
    """
    Display all chat messages from session state.
    
    Renders the conversation history with appropriate styling for
    user and assistant messages.
    """
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])


def get_llm_response(
    client: OpenAI,
    model: str,
    messages: List[Dict[str, str]],
    temperature: float = 0.7
) -> str:
    """
    Get response from the LLM.
    
    Args:
        client: OpenAI client instance
        model: Name of the model to use
        messages: List of message dictionaries with 'role' and 'content'
        temperature: Sampling temperature (default: 0.7)
    
    Returns:
        str: The assistant's response text
    
    Raises:
        Exception: If the API call fails
    """
    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature
    )
    return response.choices[0].message.content


def main() -> None:
    """
    Main application function.
    
    Sets up the Streamlit interface, handles user input,
    and manages the chat conversation flow.
    """
    # Page configuration
    st.set_page_config(
        page_title="LLM Chatbot",
        page_icon="💬",
        layout="centered"
    )
    
    # Initialize session state
    initialize_session_state()
    
    # Sidebar for configuration
    with st.sidebar:
        st.title("⚙️ Configuration")
        
        # LLM settings
        llm_url = st.text_input(
            "LLM API URL",
            value="http://localhost:11434/v1",
            help="Base URL for your local LLM API (e.g., Ollama, LM Studio)"
        )
        
        model_name = st.text_input(
            "Model Name",
            value="llama2",
            help="Name of the model to use"
        )
        
        api_key = st.text_input(
            "API Key",
            value="dummy",
            type="password",
            help="API key (use 'dummy' for most local models)"
        )
        
        temperature = st.slider(
            "Temperature",
            min_value=0.0,
            max_value=2.0,
            value=0.7,
            step=0.1,
            help="Controls randomness in responses"
        )
        
        # Update client if settings change
        if st.button("Update Settings"):
            st.session_state.client = create_openai_client(llm_url, api_key)
            st.success("Settings updated!")
        
        # Clear chat button
        if st.button("Clear Chat"):
            st.session_state.messages = []
            st.rerun()
        
        # Info section
        st.divider()
        st.caption("💡 Tip: Make sure your local LLM is running before chatting!")
    
    # Main chat interface
    st.title("💬 LLM Chatbot")
    st.caption("Chat with your local language model")
    
    # Display existing messages
    display_chat_messages()
    
    # Chat input
    if prompt := st.chat_input("Type your message here..."):
        # Ensure client is initialized
        if st.session_state.client is None:
            st.session_state.client = create_openai_client(llm_url, api_key)
        
        # Add user message to chat
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Display user message
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Get and display assistant response
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            
            try:
                # Get response from LLM
                response = get_llm_response(
                    client=st.session_state.client,
                    model=model_name,
                    messages=st.session_state.messages,
                    temperature=temperature
                )
                
                # Display response
                message_placeholder.markdown(response)
                
                # Add assistant response to chat history
                st.session_state.messages.append(
                    {"role": "assistant", "content": response}
                )
                
            except Exception as e:
                error_message = f"❌ Error: {str(e)}"
                message_placeholder.error(error_message)
                st.error(
                    "Failed to get response. Please check your LLM URL and "
                    "ensure the model is running."
                )


if __name__ == "__main__":
    main()
