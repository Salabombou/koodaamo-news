FROM alpine:3.20.1

ENV TZ=Europe/Helsinki

WORKDIR /root

RUN apk add --no-cache ffmpeg python3 tzdata

COPY record-news.sh ./
RUN chmod +x record-news.sh

COPY cron-scheduler.py ./
RUN echo "* * * * * python cron-scheduler.py" > /etc/crontabs/root

CMD ["crond", "-f"]
