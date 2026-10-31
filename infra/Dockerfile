FROM eclipse-temurin:21.0.6_7-jdk-jammy@sha256:24a8854594eea72c16822953e6cb96c78d10fc3c77b7b8a60ce8e5ac440a2337 AS jdk
FROM python:3.12.9-slim-bookworm@sha256:48a11b7ba705fd53bf15248d1f94d36c39549903c5d59edcfa2f3f84126e7b44
RUN apt-get update && apt-get install -y --no-install-recommends libstdc++6 zlib1g && rm -rf /var/lib/apt/lists/*
COPY --from=jdk /opt/java/openjdk /opt/java/openjdk
ENV JAVA_HOME=/opt/java/openjdk
ENV PATH="/opt/java/openjdk/bin:${PATH}"
RUN pip install --no-cache-dir psycopg[binary]==3.2.6
RUN mkdir -p /opt/drivers && python -c "import urllib.request; urllib.request.urlretrieve('https://repo.maven.apache.org/maven2/org/postgresql/postgresql/42.7.5/postgresql-42.7.5.jar','/opt/drivers/postgresql.jar')"
WORKDIR /work
ENTRYPOINT []
