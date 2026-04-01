#!/usr/bin/env node
/**
 * FlightMind LLM Proxy
 * Arranca con: ANTHROPIC_API_KEY=sk-... node testbench/llm_proxy.js
 * El testbench llama a http://localhost:3001/analyze
 * La API key NUNCA llega al navegador ni al repo.
 */
const http = require("http");
const https = require("https");

const PORT = 3001;
const API_KEY = process.env.ANTHROPIC_API_KEY;

if (!API_KEY) {
  console.error("[LLM Proxy] ERROR: ANTHROPIC_API_KEY no definida.");
  console.error("Uso: ANTHROPIC_API_KEY=sk-... node testbench/llm_proxy.js");
  process.exit(1);
}

console.log(`[LLM Proxy] Arrancado en http://localhost:${PORT}`);
console.log("[LLM Proxy] API key detectada. El testbench puede conectar.");

http
  .createServer((req, res) => {
    res.setHeader("Access-Control-Allow-Origin", "*");
    res.setHeader("Access-Control-Allow-Headers", "Content-Type");
    res.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");

    if (req.method === "OPTIONS") {
      res.writeHead(204);
      res.end();
      return;
    }
    if (req.method !== "POST" || req.url !== "/analyze") {
      res.writeHead(404);
      res.end("Not found");
      return;
    }

    let body = "";
    req.on("data", (chunk) => {
      body += chunk;
    });
    req.on("end", () => {
      let payload;
      try {
        payload = JSON.parse(body);
      } catch {
        res.writeHead(400);
        res.end("Bad JSON");
        return;
      }

      const prompt =
        typeof payload.prompt === "string" ? payload.prompt : String(payload.prompt || "");

      const anthropicBody = JSON.stringify({
        model: "claude-sonnet-4-20250514",
        max_tokens: 300,
        stream: true,
        system: `Eres un ingeniero experto en V&V de sistemas UAS autónomos analizando el stack FlightMind en tiempo real.
El sistema tiene: Mission FSM (9 estados), GPP (Informed-RRT* + Dubins), FDIR (4 detectores), DAIDALUS (DAA), ACAS Xu.
Responde en español. Sé conciso (máx 3 frases). Enfócate en si el comportamiento es correcto y qué significa para el evaluador.`,
        messages: [{ role: "user", content: prompt }],
      });

      const options = {
        hostname: "api.anthropic.com",
        path: "/v1/messages",
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "x-api-key": API_KEY,
          "anthropic-version": "2023-06-01",
        },
      };

      res.writeHead(200, {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        Connection: "keep-alive",
      });

      const proxyReq = https.request(options, (proxyRes) => {
        proxyRes.on("data", (chunk) => {
          res.write(chunk);
        });
        proxyRes.on("end", () => {
          res.end();
        });
      });
      proxyReq.on("error", (err) => {
        console.error("[LLM Proxy] Error:", err.message);
        try {
          res.end();
        } catch (_) {
          /* ignore */
        }
      });
      proxyReq.write(anthropicBody);
      proxyReq.end();
    });
  })
  .listen(PORT);
