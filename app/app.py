import os
import chainlit as cl
from azure.identity import DefaultAzureCredential
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# Use managed identity / Azure auth
credential = DefaultAzureCredential()

# Chat model deployment (from your Azure OpenAI resource)
llm = AzureChatOpenAI(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment="gpt-4o-mini",        # must match your deployment name
    api_version="2024-07-18",              # adjust if your region uses a different version
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
)

# Embeddings deployment (for Azure AI Search RAG)
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
    azure_deployment="text-embedding-3-small",  # must match your embedding deployment name
    api_version="2024-07-18",
    azure_ad_token_provider=lambda: credential.get_token(
        "https://cognitiveservices.azure.com/.default"
    ).token,
)

# All tutors and their corresponding Azure AI Search indexes
TUTOR_CONFIGS = {
    "Azure": {
        "index": "azure-docs",
        "desc": "Microsoft Azure Infrastructure Expert",
    },
    "AWS": {
        "index": "aws-docs",
        "desc": "Amazon Web Services Solutions Architect",
    },
    "GCP": {
        "index": "gcp-docs",
        "desc": "Google Cloud Platform Engineer",
    },
    "OCI": {
        "index": "oci-docs",
        "desc": "Oracle Cloud Infrastructure Specialist",
    },
    "Kubernetes": {
        "index": "k8s-docs",
        "desc": "CNCF Kubernetes, Gateways, and Service Mesh Expert",
    },
    "Ansible": {
        "index": "ansible-docs",
        "desc": "Red Hat Ansible Automation Guru",
    },
    "HashiCorp": {
        "index": "hashicorp-docs",
        "desc": "Terraform, Vault, Consul, and Nomad Architect",
    },
    "Dynatrace": {
        "index": "dynatrace-docs",
        "desc": "Dynatrace Observability Expert",
    },
    "Datadog": {
        "index": "datadog-docs",
        "desc": "Datadog Monitoring & APM Specialist",
    },
    "Harness": {
        "index": "harness-docs",
        "desc": "Harness CI/CD Pipeline Architect",
    },
    "Prometheus/Grafana": {
        "index": "prom-grafana-docs",
        "desc": "Open Source Metrics & Dashboard Expert",
    },
    "RedHat": {
        "index": "redhat-docs",
        "desc": "Red Hat Enterprise Linux, OpenShift, and Automation Expert",
    },
}

# -------- Chainlit UI: tutor dropdown (Chat Profiles) --------

@cl.set_chat_profiles
async def chat_profile():
    profiles = []
    for name, config in TUTOR_CONFIGS.items():
        profiles.append(
            cl.ChatProfile(
                name=name,
                markdown_description=(
                    f"**{config['desc']}**\n\n"
                    f"Ask me anything about {name} architecture, troubleshooting, or code generation."
                ),
            )
        )
    return profiles

# -------- Initialize a tutor session when chat starts --------

@cl.on_chat_start
async def on_chat_start():
    profile_name = cl.user_session.get("chat_profile", "Azure")
    config = TUTOR_CONFIGS[profile_name]

    await cl.Message(
        content=(
            f"Hello! I am your **{profile_name} Tutor**. "
            f"I am searching the `{config['index']}` knowledge base. "
            "How can I help you architect your system today?"
        )
    ).send()

    # Connect to the appropriate Azure AI Search index
    vector_store = AzureSearch(
        azure_search_endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        # Using a token from Managed Identity to call Search
        azure_search_key=credential.get_token(
            "https://search.azure.com/.default"
        ).token,
        index_name=config["index"],
        embedding_function=embeddings.embed_query,
    )

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})

    # System prompt for the selected tutor
    prompt = ChatPromptTemplate.from_messages(
        [
            (
                "system",
                f"You are an elite, highly technical {config['desc']}. "
                f"You strictly answer questions about {profile_name} and its ecosystem. "
                "If the user asks about an unrelated technology, politely redirect them to select "
                "the appropriate Tutor from the UI dropdown. "
                "Use the following retrieved context to answer the user's question accurately. "
                "If the answer is not in the context, say you don't know.\n\n"
                "Context: {context}",
            ),
            ("human", "{question}"),
        ]
    )

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()
    )

    cl.user_session.set("chain", rag_chain)

# -------- Handle user messages --------

@cl.on_message
async def main(message: cl.Message):
    chain = cl.user_session.get("chain")
    msg = cl.Message(content="")
    async for chunk in chain.astream(message.content):
        await msg.stream_token(chunk)
    await msg.send()

