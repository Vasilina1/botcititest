FROM python:3.10-slim

WORKDIR /usr/src/app/botcititest

COPY requirements.txt /usr/src/app/botcititest/
RUN pip install --upgrade pip
RUN pip install -r /usr/src/app/BotCreateSchedule/requirements.txt
COPY . /usr/src/app/botcititest

CMD python3 -m bot.py

