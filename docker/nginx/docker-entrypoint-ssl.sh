#!/bin/sh
# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).

set -eu

SSL_CERT_PATH="${SSL_CERT_PATH:-/etc/nginx/certs/tls.crt}"
SSL_KEY_PATH="${SSL_KEY_PATH:-/etc/nginx/certs/tls.key}"
SSL_CERT_CN="${SSL_CERT_CN:-localhost}"

mkdir -p "$(dirname "$SSL_CERT_PATH")"

if [ ! -f "$SSL_CERT_PATH" ] || [ ! -f "$SSL_KEY_PATH" ]; then
  openssl req -x509 -nodes -newkey rsa:2048 -days 365 \
    -keyout "$SSL_KEY_PATH" \
    -out "$SSL_CERT_PATH" \
    -subj "/CN=$SSL_CERT_CN"
fi

exec "$@"
