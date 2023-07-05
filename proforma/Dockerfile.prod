## Use Node Slim image
FROM node:18.16 as Builder

ENV HOME_DEV=/app/proforma
## Copy source code
COPY . $HOME_DEV
WORKDIR $HOME_DEV
RUN npm install -g @angular/cli@16.1.0
RUN npm i
RUN ng build 

#--base-href /laminas/
RUN ng run proforma:server

# RUN addgroup -S app && adduser -S app -G app
# EXPOSE 4000

# CMD ["npm", "run","dev:ssr"]


FROM node:18.16-alpine3.18
RUN addgroup -S app && adduser -S app -G app
ENV HOME=/app
WORKDIR $HOME
COPY --from=Builder /app/proforma/dist/proforma ./dist/proforma
RUN chown -R app:app /app/dist/proforma
EXPOSE 4000
CMD ["node","dist/proforma/server/main.js"]
