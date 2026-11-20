# Build the React app, then serve it with nginx, which also proxies /api/ to the API container.
FROM node:26.13.1-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# npm install, not npm ci: the Windows-written lock file lacks Linux-only optional packages
# (@emnapi/core, @emnapi/runtime). Switch back to npm ci once the lock file is regenerated.
RUN npm install --no-audit --no-fund
COPY . .
# Mocks are on unless this is 'false'; the image talks to the real API by default.
ARG VITE_USE_MOCKS=false
ENV VITE_USE_MOCKS=$VITE_USE_MOCKS
RUN npm run build

FROM nginx:stable-alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
