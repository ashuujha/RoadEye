FROM node:22.15.0-bookworm-slim
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY . .
RUN npm run build
RUN chown -R node:node /app
USER node
CMD ["npm", "run", "dev"]
