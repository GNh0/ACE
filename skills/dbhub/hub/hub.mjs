// ACE dbhub: 로컬 공용 MSSQL MCP 허브. 프로세스 1개를 Claude Code·Codex·Antigravity의 모든 세션이 같이 쓴다.
//   POST http://127.0.0.1:<port>/mcp/<연결이름>   (연결 목록: 같은 폴더의 connections.json)
//   GET  http://127.0.0.1:<port>/status            (연결 상태)
// 도구 이름·입력은 mssql-mcp 3.0.0 그대로라 클라이언트 서버 이름(mssql_<연결이름>) 기준의 ACE DB 보호 훅이 그대로 동작한다.
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { AsyncLocalStorage } from "node:async_hooks";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const CONF = path.join(DIR, "connections.json");
const als = new AsyncLocalStorage();
let conf = { port: 8765, connections: {} };

function loadConf() {
    try {
        conf = JSON.parse(fs.readFileSync(CONF, "utf8").replace(/^﻿/, ""));
        console.error(`[hub] 연결 ${Object.keys(conf.connections).length}개 로드`);
        return true;
    } catch (e) {
        console.error(`[hub] connections.json 읽기 실패: ${e.message}`);
        return false;
    }
}
loadConf();

globalThis.__dbhub = {
    current: () => als.getStore() ?? null,
    currentConfig: () => {
        const name = als.getStore();
        return name ? conf.connections[name] ?? null : null;
    },
};

// 패치한 mssql-mcp 를 __dbhub 설정 뒤에 불러온다
const { createServer } = await import("./vendor/mssql-mcp/dist/src/server.js");
const { NodeStreamableHTTPServerTransport } = await import("@modelcontextprotocol/node");
const db = await import("./vendor/mssql-mcp/dist/src/db/connection.js");
const { loadConfigFromEnv } = await import("./vendor/mssql-mcp/dist/src/config.js");

// connections.json 이 바뀌면 다시 읽고, 설정이 바뀐 연결의 풀은 닫는다(다음 호출 때 새 설정으로 연결)
let watchTimer = null;
fs.watch(DIR, (ev, file) => {
    // dbhub.py 는 임시 파일에 쓴 뒤 바꿔치기한다(Windows는 임시 파일 이름만 알려 줄 때가 있다)
    if (!file || !String(file).startsWith("connections.json")) return;
    clearTimeout(watchTimer);
    watchTimer = setTimeout(async () => {
        const before = JSON.stringify(conf.connections);
        const old = conf.connections;
        if (!loadConf() || JSON.stringify(conf.connections) === before) return;
        for (const name of Object.keys(old)) {
            if (JSON.stringify(old[name]) !== JSON.stringify(conf.connections[name])) await db.closeNamed(name);
        }
    }, 300);
});

const NO_AUTOCONNECT = new Set(["mssql_connect_database", "mssql_disconnect_database", "mssql_connection_status"]);
const ALLOWED_HOSTS = new Set(["127.0.0.1", "localhost", "[::1]"]);

function readBody(req) {
    return new Promise((resolve, reject) => {
        const chunks = [];
        req.on("data", (c) => chunks.push(c));
        req.on("end", () => resolve(Buffer.concat(chunks).toString("utf8")));
        req.on("error", reject);
    });
}
function sendJson(res, code, obj) {
    res.writeHead(code, { "content-type": "application/json; charset=utf-8" });
    res.end(JSON.stringify(obj, null, 2));
}

const server = http.createServer(async (req, res) => {
    try {
        const host = (req.headers.host ?? "").replace(/:\d+$/, "");
        if (!ALLOWED_HOSTS.has(host)) return sendJson(res, 403, { error: "localhost only" });
        if (req.headers.origin && !/^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/.test(req.headers.origin))
            return sendJson(res, 403, { error: "origin not allowed" });

        const url = new URL(req.url, "http://localhost");
        if (url.pathname === "/status") {
            return sendJson(res, 200, {
                pid: process.pid,
                uptime_sec: Math.round(process.uptime()),
                memory_mb: Math.round(process.memoryUsage().rss / 1048576),
                connections: Object.keys(conf.connections),
                open_pools: db.allStates(),
            });
        }
        const m = url.pathname.match(/^\/mcp\/([^/]+)\/?$/);
        if (!m) return sendJson(res, 404, { error: "use /mcp/<connection>" });
        const name = decodeURIComponent(m[1]);
        if (!conf.connections[name]) return sendJson(res, 404, { error: `unknown connection: ${name}` });

        if (req.method !== "POST") {
            // 상태 없는(stateless) 서버: SSE GET 스트림·세션 DELETE 없음
            res.writeHead(405, { allow: "POST" });
            return res.end();
        }
        const raw = await readBody(req);
        let body;
        try { body = JSON.parse(raw); } catch { return sendJson(res, 400, { error: "invalid JSON" }); }

        await als.run(name, async () => {
            // 도구 호출 전에 연결을 자동으로 연다(이미 열려 있으면 그대로 공유)
            const msgs = Array.isArray(body) ? body : [body];
            if (msgs.some((x) => x?.method === "tools/call" && !NO_AUTOCONNECT.has(x?.params?.name))) {
                try { await db.ensurePool(loadConfigFromEnv()); }
                catch (e) { console.error(`[${name}] 자동 연결 실패: ${e.message}`); }
            }
            const mcp = createServer();
            const transport = new NodeStreamableHTTPServerTransport({ sessionIdGenerator: undefined, enableJsonResponse: true });
            res.on("close", () => { transport.close().catch(() => {}); mcp.close().catch(() => {}); });
            await mcp.connect(transport);
            await transport.handleRequest(req, res, body);
        });
    } catch (e) {
        console.error("[hub] 요청 처리 오류:", e?.stack ?? e);
        if (!res.headersSent) sendJson(res, 500, { error: String(e?.message ?? e) });
    }
});

server.on("error", (e) => {
    if (e.code === "EADDRINUSE") {
        console.error(`[hub] 포트 ${conf.port} 이미 사용 중 — 허브가 이미 떠 있으면 정상. 종료.`);
        process.exit(0);
    }
    console.error("[hub] 서버 오류:", e);
    process.exit(1);
});
const shutdown = async () => { server.close(); await db.closePoolOnShutdown(); process.exit(0); };
process.on("SIGINT", shutdown);
process.on("SIGTERM", shutdown);
process.on("uncaughtException", (e) => console.error("[hub] uncaught:", e?.stack ?? e));
process.on("unhandledRejection", (e) => console.error("[hub] unhandled:", e?.stack ?? e));

server.listen(conf.port ?? 8765, "127.0.0.1", () => console.error(`[hub] listening http://127.0.0.1:${conf.port ?? 8765}`));
