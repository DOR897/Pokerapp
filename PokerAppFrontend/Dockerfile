# PokerAppFrontend/Dockerfile
FROM node:20-bullseye

# Optional but nice: faster file watching in containers
ENV WATCHPACK_POLLING=true
ENV CI=false
# Tell Expo/Metro what IP to advertise in the QR (we'll pass it in compose)
ARG HOST_IP
ENV REACT_NATIVE_PACKAGER_HOSTNAME=$HOST_IP

WORKDIR /app

# install deps first (better cache)
COPY package.json package-lock.json* yarn.lock* ./
RUN if [ -f package-lock.json ]; then npm ci; \
    elif [ -f yarn.lock ]; then corepack enable && yarn install --frozen-lockfile; \
    else npm install; fi

# copy the rest
COPY . .

# Ports:
# 8081 - Metro/Dev Server (Expo's current default)
# 19006 - Expo Web preview
# 19000/19001 - Legacy Expo Go ports (still useful on some devices)
EXPOSE 8081 19006 19000 19001

# Start Expo dev server in LAN mode so phones on Wi-Fi can see it
CMD ["npx", "expo", "start", "--host", "lan", "--port", "8081", "--web-port", "19006", "--clear"]
