#!/usr/bin/env node
// Append-only audit sink for write testing. The browser page tees every request it makes
// (method, url, body, status, response head) here as JSONL, so there is a complete,
// timestamped record of everything that touched the QA system during a write test.
//
//   node tools/audit-log.mjs [outfile.jsonl]
//
// Every POST body is appended as one JSON line. Never overwrites. Ctrl-C to stop.

import { createServer } from 'node:http'
import { appendFileSync } from 'node:fs'
import path from 'node:path'

const out = path.resolve(process.argv[2] ?? 'write-audit.jsonl')
let n = 0

const server = createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'content-type')
  if (req.method === 'OPTIONS') return res.writeHead(204).end()
  if (req.method !== 'POST') return res.writeHead(405).end()

  const chunks = []
  req.on('data', (c) => chunks.push(c))
  req.on('end', () => {
    const raw = Buffer.concat(chunks).toString('utf8')
    // one audit event per line, exactly as the page sent it, plus a receive stamp
    appendFileSync(out, raw.trim() + '\n')
    n++
    let label = ''
    try { const e = JSON.parse(raw); label = `${e.method ?? '?'} ${e.url ?? ''}`.slice(0, 90) } catch {}
    res.writeHead(200).end('ok')
    console.log(`#${n} ${label}`)
  })
})

server.listen(8788, '127.0.0.1', () => console.log(`audit log -> ${out} (listening on :8788)`))
process.on('SIGINT', () => { console.log(`\n${n} events logged to ${out}`); process.exit(0) })
