import { Client } from "@langchain/langgraph-sdk";

export function createClient(apiUrl: string, apiKey: string | undefined) {
  // Use API key from parameter, environment variable, or undefined
  const effectiveApiKey = apiKey || process.env.NEXT_PUBLIC_API_KEY || undefined;
  
  return new Client({
    apiKey: effectiveApiKey,
    apiUrl,
  });
}
