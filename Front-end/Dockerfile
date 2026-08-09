# frontend/Dockerfile
# ------------------------------------------------------------
# CarbonSense frontend image — static site served by nginx.
# Build context: ./frontend
# ------------------------------------------------------------

FROM nginx:1.27-alpine

# Remove nginx's default sample site
RUN rm -rf /usr/share/nginx/html/*

# Static assets
COPY index.html style.css script.js /usr/share/nginx/html/

# Custom server block (adds the /api/ reverse proxy to the backend)
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

HEALTHCHECK CMD wget --no-verbose --tries=1 http://localhost:80/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
