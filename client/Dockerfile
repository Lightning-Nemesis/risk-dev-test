FROM node:22-slim

WORKDIR /code

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

EXPOSE 5173
# --host 0.0.0.0 makes the dev server reachable from outside the container
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
