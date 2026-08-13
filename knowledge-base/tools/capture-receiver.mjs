#!/usr/bin/env node
// Tiny localhost sink so a browser page can hand large capture payloads to disk
// without going through the tool-result channel (which truncates).
//
//   node tools/capture-receiver.mjs <outfile>
//
// Listens on 127.0.0.1:8787 and writes every POST body to <outfile>, so a long
// harvest can checkpoint itself. Ctrl-C or the idle timeout stops it.

import { createServer } from 'node:http'
import { writeFile } from 'node:fs/promises'
import path from 'node:path'

const out = path.resolve(process.argv[2] ?? 'capture.json')

const server = createServer((req, res) => {
  res.setHeader('Access-Control-Allow-Origin', '*')
  res.setHeader('Access-Control-Allow-Headers', 'content-type')
  if (req.method === 'OPTIONS') return res.writeHead(204).end()
  if (req.method !== 'POST') return res.writeHead(405).end()

  const chunks = []
  req.on('data', (c) => chunks.push(c))
  req.on('end', async () => {
    const body = Buffer.concat(chunks)
    await writeFile(out, body)
    res.writeHead(200).end('ok ' + body.length)
    console.log(`wrote ${body.length} bytes to ${out}`)
    idle.refresh()
  })
})

server.listen(8787, '127.0.0.1', () => console.log('listening on http://127.0.0.1:8787'))
// exits once nothing has checkpointed for 15 minutes
const idle = setTimeout(() => { console.error('idle, exiting'); process.exit(0) }, 900_000)
