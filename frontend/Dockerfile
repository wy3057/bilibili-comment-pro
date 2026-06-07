FROM node:20-alpine

WORKDIR /app

COPY package.json tsconfig.json tsconfig.app.json vite.config.ts index.html ./
COPY src ./src

RUN npm install

EXPOSE 4173

CMD ["npm", "run", "dev"]

