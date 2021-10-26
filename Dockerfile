FROM python:3.8-slim-buster

WORKDIR /bot

COPY . .
RUN pip3 install -r requirements.txt

CMD [ "python3", "mentor.py"]
