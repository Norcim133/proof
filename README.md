# Proof - AI-Powered Board Intelligence Platform

![Proof Application Screenshot](https://i.postimg.cc/vTQrtbS0/horizontal-name-only.jpg)

Proof is an AI-powered intelligence layer for enterprise boards. It addresses the critical challenge of distilling material information from a vast and complex set of documents spanning multiple meetings, committees, and topics. By leveraging a sophisticated RAG (Retrieval-Augmented Generation) pipeline, Proof allows board members and executives to converse with their documents, identify risks, track strategic initiatives, and uncover insights that would otherwise remain buried in text.

## Key Features

*   **Conversational AI Chat:** Engage in a natural language dialogue with your entire repository of board materials.
*   **Verifiable Sourcing:** Every AI-generated answer is backed by direct references to the source documents, including text and image excerpts.
*   **In-Browser Document Previews:** Instantly open and view source files (PDFs, Word documents, etc.) in a new browser tab directly from a reference.
*   **Common Queries:** One-click access to frequently asked, high-value questions like "Show budget trends" or "Identify potential risk gaps."
*   **Scoped Analysis:** Dynamically manage the "Data Stores" (e.g., specific committee documents) the AI uses for its analysis.
*   **Secure Authentication:** Enterprise-grade user authentication to ensure data privacy and access control.

## Tech Stack

Proof is built on a modern, scalable stack designed for building state-of-the-art AI applications.

*   **Frontend:** [Streamlit](https://streamlit.io/)
*   **RAG Pipeline & Data Ingestion:** [LlamaCloud](https://cloud.llamaindex.ai/)
*   **Language Models (LLMs):** OpenAI (GPT series) & Anthropic (Claude series)
*   **Authentication:** [Auth0](https://auth0.com/)
*   **Deployment:** [Streamlit Community Cloud](https://streamlit.io/cloud)

![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?style=for-the-badge&logo=streamlit&logoColor=white)
![LlamaIndex](https://img.shields.io/badge/LlamaIndex-6B45A3?style=for-the-badge&logo=llama&logoColor=white)
![OpenAI](https://img.shields.io/badge/OpenAI-412991?style=for-the-badge&logo=openai&logoColor=white)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)

## Getting Started

To run this project locally, you will need Python 3.11+ and `uv` installed.

### 1. Clone the Repository

```
git clone https://github.com/your-username/proof.git
cd proof
```

### 2. Set up the Environment
This project uses uv for fast dependency and environment management.

#### Create and activate a virtual environment
```
uv venv
```

#### Install required packages
```
uv sync
```
Installs packages contained in **pyproject.toml**

### 3. Configure Environment Variables
The application requires API keys and authentication details. For local development, create a **.streamlit/secrets.toml** file.
Do not commit this file to GIT.
```
.streamlit/secrets.toml
```

#### Core API Keys
```
OPENAI_API_KEY = "sk-..."
LLAMA_CLOUD_API_KEY = "llx-..."
```

#### Auth0 Configuration
```
[auth]
redirect_uri = "http://localhost:8501/oauth2callback"
cookie_secret = "generate_a_random_string_for_this"
client_id = "your_auth0_client_id"
client_secret = "your_auth0_client_secret"
server_metadata_url = "https://your-tenant.us.auth0.com/.well-known/openid-configuration"
```

### 4. Run the Application
```
streamlit run app.py
```
## Usage
Once the application is running:
1. Log In: Use your provided credentials to authenticate (NOTE: Requires admin in auth0).
2. Select a Data Store: Use the "Manage a Store" dropdown on the left to see or rename/delete stores.
3. Ask Questions: Use the "Common Queries" buttons for pre-set questions or type a custom question into the "Board Chat" input.
4. Review Results: The AI's answer will appear in the chat. The "References" panel on the right will show the source documents, which can be expanded or opened via the "Open original file" button.
