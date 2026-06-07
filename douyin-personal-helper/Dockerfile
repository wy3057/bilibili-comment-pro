FROM node:20-bookworm-slim

WORKDIR /app

COPY douyin-personal-helper/package.json ./
RUN npm install
RUN npx playwright install --with-deps chromium

COPY douyin-personal-helper/index.js ./

EXPOSE 4300

CMD ["npm", "run", "start"]
