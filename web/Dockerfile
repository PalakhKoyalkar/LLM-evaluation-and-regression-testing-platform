FROM node:26-alpine
RUN npm i -g pnpm@12.14.0
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY . .
CMD ["pnpm", "dev"]
