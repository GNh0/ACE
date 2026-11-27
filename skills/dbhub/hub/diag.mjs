// ACE dbhub 진단: node diag.mjs <연결이름>  → JSON (연결 설정을 바꿔 가며 직접 접속해 본 결과)
// 비밀번호는 출력하지 않는다. connections.json 은 같은 폴더.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import sql from "mssql";

const DIR = path.dirname(fileURLToPath(import.meta.url));
const name = process.argv[2];
const conf = JSON.parse(fs.readFileSync(path.join(DIR, "connections.json"), "utf8").replace(/^﻿/, ""));
const c = conf.connections?.[name];
if (!c) {
    console.log(JSON.stringify({ error: `unknown connection: ${name}` }));
    process.exit(0);
}
const LEGACY = { minVersion: "TLSv1", ciphers: "DEFAULT@SECLEVEL=0" };

async function attempt(label, over, query) {
    const cfg = { ...c, ...over };
    const options = { encrypt: cfg.encrypt !== false, trustServerCertificate: cfg.trustServerCertificate !== false,
        enableArithAbort: true, useUTC: false };
    if (cfg.tls) options.cryptoCredentialsDetails = { ...cfg.tls };
    const pool = new sql.ConnectionPool({ server: cfg.server, port: cfg.port ?? 1433, database: cfg.database,
        user: cfg.user, password: cfg.password, options, connectionTimeout: 12000, requestTimeout: 15000,
        pool: { max: 1, min: 0 } });
    pool.on("error", () => {});
    const t0 = Date.now();
    try {
        await pool.connect();
        let rows = null;
        if (query) rows = (await pool.request().query(query)).recordset;
        return { label, over: Object.keys(over), ok: true, ms: Date.now() - t0, rows };
    } catch (e) {
        const o = e?.originalError ?? e;
        return { label, over: Object.keys(over), ok: false, ms: Date.now() - t0, code: e?.code ?? o?.code ?? null,
            number: o?.info?.number ?? e?.number ?? null, message: String(o?.message ?? e?.message ?? e) };
    } finally {
        try { await pool.close(); } catch { /* ignore */ }
    }
}

const res = [];
const asIs = await attempt("as-is", {}, "SELECT DB_NAME() AS db");
res.push(asIs);
if (!asIs.ok) {
    // 로그인 자체가 되는지: DB 없이(master) 접속하고, 이 계정으로 보이는 DB 목록을 받는다
    res.push(await attempt("master", { database: "master" },
        "SELECT name FROM sys.databases WHERE HAS_DBACCESS(name) = 1 ORDER BY name"));
    const variants = [
        ["encrypt-off", { encrypt: false, tls: undefined }],
        ["legacy-tls", { encrypt: true, tls: LEGACY }],
        ["encrypt-off+legacy-tls", { encrypt: false, tls: LEGACY }],
        ["trust-cert", { trustServerCertificate: true }],
    ].filter(([, o]) => Object.entries(o).some(([k, v]) => JSON.stringify(c[k]) !== JSON.stringify(v)));
    for (const [label, over] of variants) {
        const r = await attempt(label, over, null);
        res.push(r);
        if (r.ok) break;
    }
}
console.log(JSON.stringify({ name, server: c.server, port: c.port ?? 1433, database: c.database, user: c.user,
    encrypt: c.encrypt !== false, legacyTls: !!c.tls, results: res }));
process.exit(0);
