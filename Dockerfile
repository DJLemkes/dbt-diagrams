ARG PYTHON_VERSION="3.11-slim-bullseye"
FROM python:$PYTHON_VERSION as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ./ /tmp/

RUN poetry build

FROM python:$PYTHON_VERSION

WORKDIR /wheels

COPY --from=requirements-stage /tmp/dist/dbt_diagrams-*.whl /wheels/dbt_diagrams-0.0.0-py3-none-any.whl

RUN pip install --no-cache-dir --upgrade /wheels/dbt_diagrams-0.0.0-py3-none-any.whl[rest-api]
RUN playwright install --with-deps chromium

EXPOSE 8080

CMD ["dbt-diagrams", "rest-api"]
