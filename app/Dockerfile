FROM python:3.11-slim

WORKDIR /app

# Copy your application code
COPY app.py /app/app.py

# Install required Python libraries
RUN pip install --no-cache-dir \
    chainlit \
    langchain \
    langchain-openai \
    langchain-community \
    azure-identity \
    azure-search-documents==11.4.0

# Expose the port Chainlit listens on
EXPOSE 8000

# Run the Chainlit app
CMD ["chainlit", "run", "app.py", "-h", "0.0.0.0", "-p", "8000"]
