FROM node:22-alpine

WORKDIR /app

# Dependencies first: this layer stays cached as long as the lockfile does not change.
COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
