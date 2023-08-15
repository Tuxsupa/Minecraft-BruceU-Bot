FROM python:3.11.4
WORKDIR /bot
RUN apt-get update && apt-get install ffmpeg libsm6 libxext6  -y
COPY requirements.txt /bot/
RUN pip install -r requirements.txt
COPY . /bot
CMD python main.py