# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

FROM --platform=$BUILDPLATFORM python:3.12.8-alpine@sha256:54bec49592c8455de8d5983d984efff76b6417a6af9b5dcc8d0237bf6ad3bd20 AS base

FROM base AS builder

RUN apk update \
    && apk add --no-cache build-base linux-headers postgresql-dev \
    && rm -rf /var/cache/apk/*

COPY requirements.txt .

RUN pip install --prefix="/install" -r requirements.txt

FROM base

RUN apk update \
    && apk add --no-cache libpq \
    && rm -rf /var/cache/apk/*

WORKDIR /reviewservice

COPY --from=builder /install /usr/local
# Add CA certificates for Secret Manager authentication
COPY --from=builder /etc/ssl/certs/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt

# Add application code
COPY . .

# Create non-root user
RUN addgroup -g 1000 reviewservice && \
    adduser -u 1000 -G reviewservice -s /bin/sh -D reviewservice

USER reviewservice

EXPOSE 8080

ENTRYPOINT ["python", "server.py"]
