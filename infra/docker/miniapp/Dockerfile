FROM node:20-alpine AS build
WORKDIR /app
COPY apps/miniapp/package*.json ./
RUN npm ci
COPY apps/miniapp .
ARG NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
RUN npm run build && npm prune --production

FROM node:20-alpine
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app/.next ./.next
COPY --from=build /app/package*.json ./
COPY --from=build /app/node_modules ./node_modules
COPY --from=build /app/public ./public
EXPOSE 3000
CMD ["npm", "start"]
