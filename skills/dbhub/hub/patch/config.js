import { z } from "zod";
import { DEFAULT_PORT, DEFAULT_ENCRYPT, DEFAULT_TRUST_SERVER_CERTIFICATE, DEFAULT_CONNECTION_TIMEOUT, DEFAULT_REQUEST_TIMEOUT, } from "./constants.js";
export const ConfigSchema = z.object({
    server: z.string().min(1, "Server address is required"),
    database: z.string().optional(),
    user: z.string().optional(),
    password: z.string().optional(),
    port: z.number().int().min(1).max(65535).optional().default(DEFAULT_PORT),
    encrypt: z.boolean().optional().default(DEFAULT_ENCRYPT),
    trustServerCertificate: z.boolean().optional().default(DEFAULT_TRUST_SERVER_CERTIFICATE),
    connectionTimeout: z.number().int().min(1000).max(60000).optional().default(DEFAULT_CONNECTION_TIMEOUT),
    requestTimeout: z.number().int().min(1000).max(300000).optional().default(DEFAULT_REQUEST_TIMEOUT),
});
export function loadConfigFromEnv() {
    // ACE dbhub 패치: 허브가 지금 요청의 연결 설정을 넘겨주면 그것을 쓴다(환경 변수 대신)
    const hub = globalThis.__dbhub?.currentConfig();
    if (hub) {
        const { tls, ...rest } = hub;
        return { ...ConfigSchema.parse(rest), tls };
    }
    const raw = {
        server: process.env.DB_SERVER,
        database: process.env.DB_DATABASE,
        user: process.env.DB_USER,
        password: process.env.DB_PASSWORD,
        port: process.env.DB_PORT ? parseInt(process.env.DB_PORT, 10) : DEFAULT_PORT,
        encrypt: process.env.DB_ENCRYPT !== "false",
        trustServerCertificate: process.env.DB_TRUST_SERVER_CERTIFICATE === "true",
        connectionTimeout: process.env.DB_CONNECTION_TIMEOUT
            ? parseInt(process.env.DB_CONNECTION_TIMEOUT, 10)
            : DEFAULT_CONNECTION_TIMEOUT,
        requestTimeout: process.env.DB_REQUEST_TIMEOUT
            ? parseInt(process.env.DB_REQUEST_TIMEOUT, 10)
            : DEFAULT_REQUEST_TIMEOUT,
    };
    return ConfigSchema.parse(raw);
}
export function loadHttpConfig() {
    return {
        host: process.env.MCP_HOST ?? "127.0.0.1",
        port: process.env.MCP_PORT ? parseInt(process.env.MCP_PORT, 10) : 3001,
    };
}
