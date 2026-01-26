# Agent Chat UI - Build from Local Source
FROM node:20-alpine AS base

WORKDIR /app

# Copy package files
COPY package.json pnpm-lock.yaml ./

# Install dependencies
RUN corepack enable pnpm && pnpm install --frozen-lockfile

# Copy all source code and configuration files
COPY tsconfig.json next.config.mjs postcss.config.mjs tailwind.config.js components.json ./
COPY public ./public
COPY src ./src

# Build arguments - MUST be before ENV
ARG NEXT_PUBLIC_API_URL=http://localhost:2024
ARG NEXT_PUBLIC_ASSISTANT_ID=rag_agent
ARG NEXT_PUBLIC_API_KEY=""
ARG NEXT_PUBLIC_AGENT_NAME="Agent Chat"
ARG NEXT_PUBLIC_WELCOME_MESSAGE=""
ARG NEXT_PUBLIC_SHOW_TOOL_CALLS_TOGGLE="true"
ARG NEXT_PUBLIC_SHOW_FILE_UPLOAD="true"
ARG NEXT_PUBLIC_MAX_MESSAGE_LENGTH="5000"

# Set environment variables
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_ASSISTANT_ID=$NEXT_PUBLIC_ASSISTANT_ID
ENV NEXT_PUBLIC_API_KEY=$NEXT_PUBLIC_API_KEY
ENV NEXT_PUBLIC_AGENT_NAME=$NEXT_PUBLIC_AGENT_NAME
ENV NEXT_PUBLIC_WELCOME_MESSAGE=$NEXT_PUBLIC_WELCOME_MESSAGE
ENV NEXT_PUBLIC_SHOW_TOOL_CALLS_TOGGLE=$NEXT_PUBLIC_SHOW_TOOL_CALLS_TOGGLE
ENV NEXT_PUBLIC_SHOW_FILE_UPLOAD=$NEXT_PUBLIC_SHOW_FILE_UPLOAD
ENV NEXT_PUBLIC_MAX_MESSAGE_LENGTH=$NEXT_PUBLIC_MAX_MESSAGE_LENGTH
ENV NEXT_TELEMETRY_DISABLED=1

# Build with variables
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
