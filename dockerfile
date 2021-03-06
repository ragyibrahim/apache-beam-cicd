FROM gcr.io/dataflow-templates-base/python3-template-launcher-base

ARG WORKDIR=/dataflow/template
RUN mkdir -p ${WORKDIR}
RUN mkdir -p ${WORKDIR}/modules
WORKDIR ${WORKDIR}
COPY app/modules ${WORKDIR}/modules

RUN pip install --upgrade pip \
    && pip install --upgrade setuptools \
    && pip install --upgrade python-dotenv \
    && pip install apache-beam[gcp] \
    && pip install google-cloud-secret-manager==2.0.0

COPY app/__init__.py ${WORKDIR}/__init__.py
COPY app/setup.py ${WORKDIR}/setup.py
COPY app/__main__.py ${WORKDIR}/__main__.py
COPY app/spec/metadata.json ${WORKDIR}/metadata.json

ENV FLEX_TEMPLATE_PYTHON_SETUP_FILE="${WORKDIR}/setup.py"
ENV FLEX_TEMPLATE_PYTHON_PY_FILE="${WORKDIR}/__main__.py"

ARG PROJECT_ID
ARG IMAGE 
ARG BUCKET 
ARG REGION 

RUN echo "PROJECT_ID=${PROJECT_ID}" >> .env
RUN echo "IMAGE=${IMAGE}" >> .env
RUN echo "BUCKET=${BUCKET}" >> .env
RUN echo "REGION=${REGION}" >> .env


