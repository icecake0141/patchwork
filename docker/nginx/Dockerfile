# SPDX-License-Identifier: Apache-2.0
# This file was created or modified with the assistance of an AI (Large Language Model).

FROM nginx:1.27-alpine

RUN apk add --no-cache openssl

COPY default.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint-ssl.sh /usr/local/bin/docker-entrypoint-ssl.sh

RUN chmod +x /usr/local/bin/docker-entrypoint-ssl.sh

ENTRYPOINT ["/usr/local/bin/docker-entrypoint-ssl.sh"]
CMD ["nginx", "-g", "daemon off;"]
