FROM python:3.11

WORKDIR /segwise_assignment

COPY . .
# Copy function code

# Install the specified packages
RUN pip install -r requirements.txt


EXPOSE 8080
HEALTHCHECK --interval=30s --timeout=10s CMD curl --fail http://localhost:8000/ || exit 1
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]