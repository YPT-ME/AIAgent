# Agent Chat UI - Direct Build from GitHub
FROM node:20-alpine AS base

# Install git
RUN apk add --no-cache git

WORKDIR /app

# Clone the repository directly
RUN git clone --depth 1 https://github.com/langchain-ai/agent-chat-ui.git . && \
    rm -rf .git .github

# Install dependencies
RUN corepack enable pnpm && pnpm install --frozen-lockfile

# Build arguments
ARG NEXT_PUBLIC_API_URL=http://localhost:2024
ARG NEXT_PUBLIC_ASSISTANT_ID=rag_agent

ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
ENV NEXT_PUBLIC_ASSISTANT_ID=${NEXT_PUBLIC_ASSISTANT_ID}
ENV NEXT_TELEMETRY_DISABLED=1

# Configure for standalone output
RUN echo 'module.exports = { output: "standalone" }' > next.config.js

# Build
RUN pnpm build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1

RUN addgroup --system --gid 1001 nodejs && \
    adduser --system --uid 1001 nextjs

COPY --from=base /app/public ./public
COPY --from=base --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=base --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

CMD ["node", "server.js"]
