FROM python:3.9-slim-buster as builder
COPY ./falcon-requirements.txt /tmp/requirements.txt
WORKDIR /tmp
RUN pip install --upgrade pip && pip install -r requirements.txt

FROM python:3.9-slim-buster
COPY --from=builder /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin
COPY --from=junio/gunicorn:local /usr/local/lib/python3.9/site-packages /usr/local/lib/python3.9/site-packages
COPY --from=junio/gunicorn:local /usr/local/bin /usr/local/bin
COPY --from=junio/gunicorn:local /server /server
RUN mkdir /tmp/prometheus
WORKDIR /target
RUN touch __init__.py
COPY app.py app.py
ENV GUNICORN_APP=app:app
ENV PROMETHEUS_MULTIPROC_DIR=/tmp/prometheus
ENV PYTHONPATH="${PYTHONPATH}:/target"
CMD [ "python", "/server/server.py" ]