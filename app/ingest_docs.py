import os
import sys
from typing import List

from azure.identity import DefaultAzureCredential
from langchain_community.document_loaders import WebBaseLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_openai import AzureOpenAIEmbeddings
from langchain_community.vectorstores.azuresearch import AzureSearch

credential = DefaultAzureCredential()

def get_embeddings():
    return AzureOpenAIEmbeddings(
        azure_endpoint=os.environ["AZURE_OPENAI_ENDPOINT"],
        azure_deployment="text-embedding-3-small",
        api_version="2024-07-18",
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"
        ).token,
    )

def build_vector_store(index_name: str, embeddings):
    return AzureSearch(
        azure_search_endpoint=os.environ["AZURE_SEARCH_ENDPOINT"],
        azure_search_key=credential.get_token("https://search.azure.com/.default").token,
        index_name=index_name,
        embedding_function=embeddings.embed_query,
    )

def ingest(index_name: str, urls: List[str]):
    print(f"Index: {index_name}")
    print("Loading docs...")
    loader = WebBaseLoader(urls)
    docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    chunks = splitter.split_documents(docs)

    embeddings = get_embeddings()
    vector_store = build_vector_store(index_name, embeddings)

    print(f"Uploading {len(chunks)} chunks to '{index_name}'...")
    vector_store.add_documents(chunks)
    print("Done.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python ingest_docs.py <topic>")
        sys.exit(1)

    topic = sys.argv[1].lower()

    INDEXES_AND_URLS = {
        "azure": {
            "index": "azure-docs",
            "urls": [
                "https://learn.microsoft.com/en-us/azure/architecture/framework/",
                "https://learn.microsoft.com/en-us/azure/architecture/best-practices/api-design",
                "https://learn.microsoft.com/en-us/azure/virtual-network/virtual-networks-overview",
            ],
        },
        "aws": {
            "index": "aws-docs",
            "urls": [
                "https://docs.aws.amazon.com/wellarchitected/latest/framework/welcome.html",
                "https://docs.aws.amazon.com/whitepapers/latest/aws-overview/aws-overview.pdf",
            ],
        },
        "gcp": {
            "index": "gcp-docs",
            "urls": [
                "https://cloud.google.com/architecture/framework",
                "https://cloud.google.com/docs/overview",
            ],
        },
        "oci": {
            "index": "oci-docs",
            "urls": [
                "https://docs.oracle.com/en-us/iaas/Content/CloudArchitecture/Concepts/best-practices.htm",
            ],
        },
        "kubernetes": {
            "index": "k8s-docs",
            "urls": [
                "https://kubernetes.io/docs/concepts/overview/what-is-kubernetes/",
                "https://kubernetes.io/docs/concepts/architecture/",
            ],
        },
        "ansible": {
            "index": "ansible-docs",
            "urls": [
                "https://docs.ansible.com/ansible/latest/getting_started/index.html",
            ],
        },
        "hashicorp": {
            "index": "hashicorp-docs",
            "urls": [
                "https://developer.hashicorp.com/terraform/intro",
                "https://developer.hashicorp.com/vault/docs/what-is-vault",
                "https://developer.hashicorp.com/consul/docs/intro",
                "https://developer.hashicorp.com/nomad/docs/intro",
            ],
        },
        "dynatrace": {
            "index": "dynatrace-docs",
            "urls": [
                "https://docs.dynatrace.com/docs/get-started/what-is-dynatrace",
            ],
        },
        "datadog": {
            "index": "datadog-docs",
            "urls": [
                "https://docs.datadoghq.com/getting_started/",
                "https://docs.datadoghq.com/observability_pipelines/",
            ],
        },
        "harness": {
            "index": "harness-docs",
            "urls": [
                "https://developer.harness.io/docs/platform/getting-started/overview/",
                "https://developer.harness.io/docs/continuous-delivery/",
            ],
        },
        "prometheus": {
            "index": "prom-grafana-docs",
            "urls": [
                "https://prometheus.io/docs/introduction/overview/",
                "https://grafana.com/docs/grafana/latest/getting-started/",
            ],
        },
        "redhat": {
            "index": "redhat-docs",
            "urls": [
                "https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/",
                "https://docs.openshift.com/container-platform/latest/architecture/architecture.html",
            ],
        },
    }

    if topic not in INDEXES_AND_URLS:
        print(f"Unknown topic '{topic}'. Available: {', '.join(INDEXES_AND_URLS.keys())}")
        sys.exit(1)

    config = INDEXES_AND_URLS[topic]
    ingest(config["index"], config["urls"])
