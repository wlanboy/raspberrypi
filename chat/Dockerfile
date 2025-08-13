# Use an official Python runtime as a parent image
FROM python:3.12-slim

# Set the working directory in the container
WORKDIR /app

# Copy the requirements file into the working directory
COPY requirements.txt .

# Install any needed packages specified in requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application's source code into the working directory
COPY main.py /app/
COPY templates/ /app/templates/
COPY static/ /app/static/

# Expose the port that Flask-SocketIO will run on
EXPOSE 2500

# Set the command to run the application
# Use gunicorn with a worker class that supports WebSockets for SocketIO
CMD ["gunicorn", "--worker-class", "eventlet", "--bind", "0.0.0.0:2500", "app:app"]