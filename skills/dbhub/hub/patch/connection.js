// ACE dbhub 패치(mssql-mcp 3.0.0 db/connection.js): 원본은 프로세스당 풀 1개(모듈 전역). 허브는 연결 이름(globalThis.__dbhub.current())별로 풀을 따로 둔다.
import sql from "mssql";
import { POOL_MAX, POOL_MIN, POOL_IDLE_TIMEOUT_MS } from "../constants.js";
const pools = new Map(); // name -> { pool, config }
const pending = new Map(); // name -> Promise (동시 연결 1회로 묶기)
const lastError = new Map(); // name -> 마지막 연결 실패 메시지 (도구 오류에 같이 보여 준다)
function key() {
    return globalThis.__dbhub?.current() ?? "_default";
}
async function openPool(name, config) {
    const old = pools.get(name);
    if (old) {
        pools.delete(name);
        try { await old.pool.close(); } catch { /* ignore */ }
    }
    console.error(`[${name}] Connecting to ${config.server}:${config.port}`);
    const options = {
        encrypt: config.encrypt,
        trustServerCertificate: config.trustServerCertificate,
        enableArithAbort: true,
        useUTC: false,
    };
    // 오래된 서버용 TLS 설정(예: TLS 1.0, SECLEVEL=0). 원래는 NODE_OPTIONS로 프로세스 전체에 걸던 것을 연결별로 건다.
    if (config.tls) options.cryptoCredentialsDetails = { ...config.tls };
    const newPool = new sql.ConnectionPool({
        server: config.server,
        database: config.database,
        user: config.user,
        password: config.password,
        port: config.port,
        options,
        connectionTimeout: config.connectionTimeout,
        requestTimeout: config.requestTimeout,
        pool: { max: POOL_MAX, min: POOL_MIN, idleTimeoutMillis: POOL_IDLE_TIMEOUT_MS },
    });
    newPool.on("error", (err) => console.error(`[${name}] Pool error:`, err?.message ?? err));
    try {
        await newPool.connect();
    }
    catch (err) {
        lastError.set(name, String(err?.message ?? err));
        try { await newPool.close(); } catch { /* ignore */ }
        throw err;
    }
    lastError.delete(name);
    pools.set(name, { pool: newPool, config });
    console.error(`[${name}] Connected to ${config.server}${config.database ? `/${config.database}` : ""}`);
}
export async function connectPool(config) {
    const name = key();
    const p = openPool(name, config).finally(() => pending.delete(name));
    pending.set(name, p);
    await p;
}
// 허브가 tools/call 전에 부른다: 이미 연결돼 있으면 그대로, 연결 중이면 기다리고, 없으면 연다.
export async function ensurePool(config) {
    const name = key();
    if (pools.get(name)?.pool?.connected) return;
    if (pending.has(name)) return pending.get(name);
    return connectPool(config);
}
export async function disconnectPool() {
    const name = key();
    const e = pools.get(name);
    if (e) {
        pools.delete(name);
        await e.pool.close();
    }
}
export async function closeNamed(name) {
    const e = pools.get(name);
    if (e) {
        pools.delete(name);
        try { await e.pool.close(); } catch { /* ignore */ }
    }
}
export function getPool() {
    return pools.get(key())?.pool ?? null;
}
export function requirePool() {
    const pool = getPool();
    if (!pool?.connected) {
        const why = lastError.get(key());
        throw new Error(why
            ? `No active database connection. Last connect error: ${why}`
            : "No active database connection. Use mssql_connect_database first.");
    }
    return pool;
}
export function getConnectionState() {
    const e = pools.get(key());
    const pool = e?.pool;
    return {
        connected: pool?.connected ?? false,
        config: e ? { server: e.config.server, database: e.config.database, port: e.config.port } : null,
        pool_info: pool
            ? { size: pool.size, available: pool.available, pending: pool.pending, borrowed: pool.borrowed }
            : null,
    };
}
export function allStates() {
    const out = {};
    for (const [name, e] of pools) {
        out[name] = { connected: e.pool.connected, server: e.config.server, database: e.config.database, size: e.pool.size };
    }
    return out;
}
export async function closePoolOnShutdown() {
    for (const name of [...pools.keys()]) await closeNamed(name);
}
