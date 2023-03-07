FROM python:3.10-slim

RUN apt-get update && apt-get install -y libpq-dev gcc

COPY requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install -r requirements.txt
RUN pip install gunicorn openpyxl
COPY . ./philly-bus-tracker
WORKDIR /philly-bus-tracker

CMD gunicorn -b 0.0.0.0:8050 application:server