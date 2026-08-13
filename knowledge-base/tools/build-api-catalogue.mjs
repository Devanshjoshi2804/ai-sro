#!/usr/bin/env node
// Turns the raw browser capture into indexes that sit alongside the help-derived
// knowledge graph, and joins app routes to the help navigation tree by label.
//
//   node tools/build-api-catalogue.mjs [extra-capture.json …]
//   node tools/build-api-catalogue.mjs --check

import { readFile, writeFile } from 'node:fs/promises'
import { existsSync } from 'node:fs'
import path from 'node:path'

const KG = path.resolve(import.meta.dirname, '../knowlegde_graph/blue-yonder-sce')
const RAW = path.join(KG, 'index/api-capture.raw.json')

// /data/<service>/<area>/<rest…>
function classify(p) {
  const m = /^\/data\/([A-Z]+)\/(.+)$/.exec(p)
  if (!m) return { service: p.startsWith('/refs/') ? 'refs' : 'other', kind: 'platform', resource: p }
  const [, service, rest] = m
  if (rest.startsWith('rpux/filter/columns/')) {
    return { service, kind: 'grid-columns', resource: rest.slice('rpux/filter/columns/'.length) }
  }
  if (rest.startsWith('rpux/filter/default/')) {
    return { service, kind: 'grid-default-filter', resource: rest.slice('rpux/filter/default/'.length) }
  }
  if (rest.startsWith('rpux/')) return { service, kind: 'ui-support', resource: rest.slice(5) }
  // /data/WM/listCountries — a MOCA-style command surfaced over HTTP
  if (/^[a-z]+[A-Z]/.test(rest) && !rest.includes('/')) {
    return { service, kind: 'command', resource: rest }
  }
  if (rest.startsWith('wm/') || rest.startsWith('mcs/')) {
    return { service, kind: 'collection', resource: rest.replace(/^(wm|mcs)\//, '') }
  }
  return { service, kind: 'other', resource: rest }
}

// "#wm.config/wm.config.warehouse.warehouse////" -> menu wm.config, page wm.config.warehouse.warehouse
function parseHash(h) {
  const body = h.replace(/^#/, '')
  const [menu, rest = ''] = body.split('/')
  const page = rest.split('/')[0] || null
  return { menu: menu || null, page }
}

async function run(extras) {
  const merged = new Map()
  let routes = []
  let progress = null

  for (const f of [...extras, RAW]) {
    if (!existsSync(f)) continue
    const d = JSON.parse(await readFile(f, 'utf8'))
    if (d.routes?.length) routes = d.routes
    if (d.captured_at_route_progress) progress = d.captured_at_route_progress
    for (const e of d.endpoints ?? []) {
      const cur = merged.get(e.path) ?? { path: e.path, hits: 0, params: new Set(), routes: new Set(), sources: new Set() }
      cur.hits += e.hits
      cur.sources.add('observed')
      for (const p of e.params) cur.params.add(p)
      for (const r of e.routes) if (r && r !== 'init') cur.routes.add(r)
      merged.set(e.path, cur)
    }

    // ExtJS store proxies declare their URL even when the store never loaded, so a
    // screen that fetches nothing on open still yields its endpoint.
    for (const s of d.store_urls ?? []) {
      let u
      try { u = new URL(s.url, 'https://x') } catch { continue }
      if (!/^\/(data|refs)\//.test(u.pathname)) continue
      const cur = merged.get(u.pathname) ?? { path: u.pathname, hits: 0, params: new Set(), routes: new Set(), sources: new Set() }
      cur.sources.add('store-config')
      for (const k of u.searchParams.keys()) if (!/^(_dc|siteId|subsites)$/.test(k)) cur.params.add(k)
      for (const r of s.routes ?? []) if (r && r !== 'init') cur.routes.add(r)
      merged.set(u.pathname, cur)
    }
  }

  const endpoints = [...merged.values()]
    .map((e) => ({
      ...classify(e.path),
      path: e.path,
      hits: e.hits,
      sources: [...e.sources].sort(),
      params: [...e.params].sort(),
      seen_on_routes: [...e.routes].sort(),
    }))
    .sort((a, b) => a.path.localeCompare(b.path))

  // join routes to the help-derived navigation tree by label
  const nav = JSON.parse(await readFile(path.join(KG, 'index/navigation.json'), 'utf8'))
  const navLabels = new Map()
  const walk = (nodes, trail) => {
    for (const n of nodes) {
      const t = [...trail, n.name]
      navLabels.set(n.name.toLowerCase(), t)
      if (n.children.length) walk(n.children, t)
    }
  }
  walk(nav, [])

  const pages = JSON.parse(await readFile(path.join(KG, 'index/pages.json'), 'utf8'))
  const pageByTitle = new Map(pages.map((p) => [p.title.toLowerCase(), p]))

  const routeIndex = routes.map((r) => {
    const label = r.label
    const key = label.toLowerCase()
    const help = pageByTitle.get(key)
    return {
      label,
      hash: r.hash,
      ...parseHash(r.hash),
      nav_path: navLabels.get(key) ?? null,
      help_topic: help ? { title: help.title, url: help.url, md: help.md } : null,
      endpoints: endpoints.filter((e) => e.seen_on_routes.includes(label)).map((e) => e.path),
    }
  })

  await writeFile(path.join(KG, 'index/api-endpoints.json'), JSON.stringify(endpoints, null, 1))
  await writeFile(path.join(KG, 'index/app-routes.json'), JSON.stringify(routeIndex, null, 1))

  const byKind = {}
  for (const e of endpoints) byKind[e.kind] = (byKind[e.kind] ?? 0) + 1
  const storeOnly = endpoints.filter((e) => !e.sources.includes('observed')).length
  const visited = routeIndex.filter((r) => r.endpoints.length).length
  console.log(
    `endpoints: ${endpoints.length} ${JSON.stringify(byKind)}\n` +
      `sources: ${endpoints.length - storeOnly} observed in traffic, ${storeOnly} from store config only\n` +
      `routes: ${routeIndex.length} (${visited} with captured traffic, capture progress ${progress})\n` +
      `joined: ${routeIndex.filter((r) => r.help_topic).length} routes matched a help topic, ` +
      `${routeIndex.filter((r) => r.nav_path).length} matched the navigation tree`,
  )
}

async function check() {
  const fail = []
  const ok = (c, m) => { if (!c) fail.push(m) }
  const eps = JSON.parse(await readFile(path.join(KG, 'index/api-endpoints.json'), 'utf8'))
  const routes = JSON.parse(await readFile(path.join(KG, 'index/app-routes.json'), 'utf8'))

  ok(eps.length > 100, `only ${eps.length} endpoints`)
  ok(eps.some((e) => e.path === '/data/WM/wm/locations'), 'missing /data/WM/wm/locations')
  ok(eps.some((e) => e.kind === 'command'), 'no MOCA-style command endpoints classified')
  ok(eps.some((e) => e.kind === 'grid-columns'), 'no grid-column endpoints classified')
  ok(eps.every((e) => e.path.startsWith('/')), 'endpoint path not rooted')
  ok(eps.some((e) => e.sources.includes('store-config')), 'no store-config endpoints merged')
  ok(eps.every((e) => e.sources.length), 'endpoint with no source')
  ok(routes.length > 150, `only ${routes.length} routes`)
  ok(routes.some((r) => r.help_topic), 'no route joined to a help topic')
  ok(routes.every((r) => r.hash.startsWith('#')), 'route hash malformed')

  if (fail.length) {
    console.error(`FAIL ${fail.length}:`)
    for (const f of fail) console.error('  ' + f)
    process.exit(1)
  }
  console.log(`check OK — ${eps.length} endpoints, ${routes.length} routes`)
}

const args = process.argv.slice(2)
if (args.includes('--check')) await check()
else await run(args.filter((a) => !a.startsWith('--')))
