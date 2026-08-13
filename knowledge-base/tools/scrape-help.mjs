#!/usr/bin/env node
// Scrape the Blue Yonder Supply Chain Execution Web Applications help system
// (MadCap Flare WebHelp2) into markdown + JSON indexes.
//
//   node tools/scrape-help.mjs            pilot: Warehouse Management > Configuration
//   node tools/scrape-help.mjs --all      every topic
//   node tools/scrape-help.mjs --check    assertions over the generated corpus

import { mkdir, writeFile, readFile, readdir, stat } from 'node:fs/promises'
import { createHash } from 'node:crypto'
import { existsSync } from 'node:fs'
import path from 'node:path'
import * as cheerio from 'cheerio'
import TurndownService from 'turndown'
import { gfm } from 'turndown-plugin-gfm'

const BASE = 'https://bf56-kms-wms-web-np2.jdadelivers.com/web/help'
const OUT = path.resolve(import.meta.dirname, '../knowlegde_graph/blue-yonder-sce')
const UA = 'sce-help-kb-scraper/1.0 (one-time documentation extract)'
const CONCURRENCY = 4
const GAP_MS = 150

const sha1 = (b) => createHash('sha1').update(b).digest('hex')
const slug = (s) =>
  s.toLowerCase().replace(/[^a-z0-9]+/g, '-').replace(/^-|-$/g, '').slice(0, 80) || 'untitled'

async function get(url, { binary = false } = {}) {
  for (let attempt = 0; attempt < 2; attempt++) {
    try {
      const res = await fetch(url, { headers: { 'User-Agent': UA }, signal: AbortSignal.timeout(30_000) })
      if (res.status >= 500) throw new Error(`HTTP ${res.status}`)
      if (!res.ok) return { error: `HTTP ${res.status}` }
      return binary ? { buf: Buffer.from(await res.arrayBuffer()) } : { text: await res.text() }
    } catch (err) {
      if (attempt === 1) return { error: String(err.message || err) }
      await new Promise((r) => setTimeout(r, 1000))
    }
  }
}

// Flare data files are `define({...})` with bare keys and single-quoted strings.
function parseDefine(src) {
  let s = src.slice(src.indexOf('(') + 1, src.lastIndexOf(')')).trim()
  s = s.replace(/([{,])\s*(\w+)\s*:/g, '$1"$2":')
  // single-quoted -> JSON strings, preserving escaped quotes
  s = s.replace(/'((?:\\.|[^'\\])*)'/g, (_, body) =>
    JSON.stringify(body.replace(/\\'/g, "'").replace(/\\\\/g, '\\')),
  )
  return JSON.parse(s)
}

async function buildToc() {
  const sys = (await get(`${BASE}/Data/HelpSystem.xml`)).text
  const tocPath = /Toc="([^"]+)"/.exec(sys)[1]
  const buildVersion = /BuildVersion="([^"]+)"/.exec(sys)?.[1]
  const toc = parseDefine((await get(`${BASE}/${tocPath}`)).text)

  const entries = {}
  for (let c = 0; c < toc.numchunks; c++) {
    const chunk = parseDefine(
      (await get(`${BASE}/${path.posix.dirname(tocPath)}/${toc.prefix}${c}.js`)).text,
    )
    for (const [link, v] of Object.entries(chunk)) {
      v.i.forEach((id, k) => (entries[id] = { link, title: v.t[k] }))
    }
  }

  const nodes = []
  const walk = (list, depth, parentId, trail) => {
    for (const n of list) {
      const e = entries[n.i] ?? { link: null, title: `#${n.i}` }
      const tocPathTrail = [...trail, e.title]
      const node = {
        id: n.i,
        depth,
        title: e.title,
        url: e.link,
        parent_id: parentId,
        toc_path: tocPathTrail,
        children: [],
      }
      nodes.push(node)
      if (parentId !== null) nodes.find((p) => p.id === parentId)?.children.push(n.i)
      if (n.n) walk(n.n, depth + 1, n.i, tocPathTrail)
    }
  }
  walk(toc.tree.n, 0, null, [])
  return { nodes, buildVersion }
}

function subtree(nodes, rootTitle) {
  const root = nodes.find((n) => n.depth === 1 && n.title === rootTitle)
  if (!root) throw new Error(`no depth-1 node titled ${rootTitle}`)
  const i = nodes.indexOf(root)
  let j = nodes.length
  for (let k = i + 1; k < nodes.length; k++) {
    if (nodes[k].depth <= 1) { j = k; break }
  }
  return nodes.slice(i, j)
}

// md/<slugged toc path>.md — mirrors the TOC hierarchy, not the source URLs.
// The top-level section stays in the path: "Reports" exists under both
// Warehouse Management and Warehouse Labor Management.
const mdPathFor = (node) =>
  path.posix.join(...node.toc_path.slice(0, -1).map(slug), `${slug(node.title)}.md`) ||
  `${slug(node.title)}.md`

const td = new TurndownService({ headingStyle: 'atx', codeBlockStyle: 'fenced', bulletListMarker: '-' })
td.use(gfm)
td.keep(['sup', 'sub'])
// keep line breaks literal so they survive inside GFM table cells
td.addRule('br', { filter: 'br', replacement: () => '<br>' })

const FIELD_CAPTION = /fields?$/i
const FIELD_HEADER = /^(field|column|name|option|button|icon|setting|parameter)s?$/i

function extract(html, node, urlToMd) {
  const $ = cheerio.load(html)
  const $main = $('div.main-section')
  if (!$main.length) return null

  // Breadcrumbs and the "In this topic" mini-TOC are populated by JS at runtime and
  // are empty in the served HTML — their static shells are stripped and the equivalent
  // data comes from toc_path and the heading scan below.
  $main
    .find(
      '.nocontent, script, style, noscript, nav.sidenav-wrapper, .side-content, .side-menu, .top-menu, .MCBreadcrumbsBox, .MCMiniTocBox, .InThisSectionHeader',
    )
    .remove()

  // The docs mark UI labels (buttons, menu items, field names) with span.specialbold —
  // 9k of them. Without this they turndown to plain prose and become unextractable.
  $main.find('span.specialbold, span.notebold').each((_, el) => {
    const $s = $(el)
    $s.replaceWith(`<strong>${$s.html() ?? ''}</strong>`)
  })

  // MadCap togglers: a decorative transparent.gif glyph inside an href="#" link whose
  // target div is inline in the HTML, so nothing is lost by flattening them to text.
  $main.find('img.MCToggler_Image_Icon, img[src*="transparent.gif"]').remove()
  $main.find('a.MCToggler, a.MCTogglerHotSpot').each((_, el) => {
    const $a = $(el)
    $a.replaceWith($a.html() ?? '')
  })

  // Field-table cells hold multiple <p>/<li> blocks. Left alone, turndown emits raw
  // newlines inside pipe cells and the GFM table stops rendering — flatten to <br>.
  $main.find('td, th').each((_, el) => {
    const $c = $(el)
    if (!$c.children('p, div, ul, ol, li').length) return
    $c.find('li').each((_, li) => $(li).prepend('• '))
    $c.find('p, div, li').each((_, b) => $(b).after('<br>'))
    $c.find('p, div, ul, ol, li').each((_, b) => $(b).replaceWith($(b).html() ?? ''))
    $c.html(
      ($c.html() ?? '')
        .replace(/\s*(<br\s*\/?>\s*)+/gi, '<br>')
        .replace(/^(<br>)+|(<br>)+$/g, '')
        .replace(/\s+/g, ' '),
    )
  })

  const pageDir = path.posix.dirname(node.url) // e.g. /content or /content/admin
  const abs = (src) =>
    src.startsWith('http') ? src : path.posix.normalize(path.posix.join(pageDir, src))

  const images = []
  $main.find('img').each((_, el) => {
    const src = $(el).attr('src')
    if (!src) return
    const resolved = abs(src)
    const alt = ($(el).attr('alt') || '').trim()
    images.push({ src: resolved, alt })
    // rewrite to the local copy, relative from this file's md/ location
    const depth = mdPathFor(node).split('/').length - 1
    $(el).attr('src', `${'../'.repeat(depth)}../images${resolved.replace(/^\/content/, '')}`)
  })

  const outlinks = []
  $main.find('a[href]').each((_, el) => {
    const href = $(el).attr('href')
    if (!href || href.startsWith('#') || href.startsWith('mailto:')) return
    if (/^https?:/i.test(href)) { outlinks.push({ url: href, external: true }); return }
    const resolved = abs(href.split('#')[0])
    outlinks.push({ url: resolved, external: false })
    const target = urlToMd.get(resolved)
    if (target) {
      const from = path.posix.dirname(mdPathFor(node))
      $(el).attr('href', path.posix.relative(from, target) || './' + path.posix.basename(target))
    } else {
      // outside this run's scope — keep it reachable against the live help system
      $(el).attr('href', BASE + resolved)
    }
  })

  const tables = []
  $main.find('table').each((_, el) => {
    const $t = $(el)
    let caption = $t.find('caption').first().text().trim()
    if (!caption) {
      const $prev = $t.prevAll('h1, h2, h3, h4, h5, h6').first()
      caption = $prev.text().trim()
    }
    const headers = $t
      .find('tr')
      .first()
      .find('th, td')
      .map((_, c) => $(c).text().trim())
      .get()
    const rows = $t
      .find('tr')
      .slice(1)
      .map((_, tr) => [$(tr).find('td, th').map((_, c) => $(c).text().replace(/\s+/g, ' ').trim()).get()])
      .get()
    const isFieldTable =
      (caption && FIELD_CAPTION.test(caption)) || (headers[0] && FIELD_HEADER.test(headers[0]))
    tables.push({ caption, headers, rows, is_field_table: Boolean(isFieldTable) })
  })

  const collapsibles =
    $main.find('.MCDropDown, .MCExpanding, .MCTextPopup, [class*="MCDropDown"]').length

  const sections = $main
    .find('h2, h3')
    .map((_, el) => $(el).text().replace(/\s+/g, ' ').trim())
    .get()
    .filter(Boolean)

  // the topic supplies its own <h1>; don't prepend a duplicate
  const hasH1 = $main.find('h1').length > 0
  const body = td
    .turndown($main.html() || '')
    // source nests <b><span class="bold">, which turndown renders as ****X****
    .replace(/\*{4,}/g, '**')
    // menu separators come through as bolded, escaped "\>"
    .replace(/\*\*\s*\\?>\s*\*\*/g, ' > ')
    .replace(/\\>/g, '>')
    // normalise menu separators: "Shipping> Outbound" / "Configuration >Inventory"
    .replace(/([A-Za-z0-9*])[ \t]*>[ \t]*([A-Za-z0-9*])/g, '$1 > $2')
    // a bold span that opens inside one element and closes in another leaves an odd
    // number of ** on the line; drop the unmatched one
    .split('\n')
    .map((l) => ((l.match(/\*\*/g)?.length ?? 0) % 2 ? l.replace(/\*\*(?![\s\S]*\*\*)/, '') : l))
    .join('\n')
  return { sections, images, outlinks, tables, body, collapsibles, hasH1 }
}

async function pool(items, worker) {
  const out = new Array(items.length)
  let next = 0
  await Promise.all(
    Array.from({ length: CONCURRENCY }, async () => {
      while (next < items.length) {
        const i = next++
        out[i] = await worker(items[i], i)
        await new Promise((r) => setTimeout(r, GAP_MS))
      }
    }),
  )
  return out
}

async function writeOut(rel, data) {
  const p = path.join(OUT, rel)
  await mkdir(path.dirname(p), { recursive: true })
  await writeFile(p, data)
}

const yamlList = (a) => (a.length ? `\n${a.map((x) => `  - ${JSON.stringify(x)}`).join('\n')}` : ' []')

async function run(all) {
  console.log('fetching TOC…')
  const { nodes, buildVersion } = await buildToc()
  const scope = all ? nodes : subtree(nodes, 'Configuration')
  const topics = scope.filter((n) => n.url)
  console.log(`toc: ${nodes.length} nodes, scope: ${topics.length} topics${all ? '' : ' (Configuration)'}`)

  await writeOut('index/toc.json', JSON.stringify(nodes, null, 1))

  // only in-scope topics get a local .md target; the rest stay as live URLs
  const urlToMd = new Map(topics.map((n) => [n.url, mdPathFor(n)]))

  const failures = []
  const pages = []
  const fields = []
  const icons = new Map()

  await pool(topics, async (node, i) => {
    const res = await get(BASE + node.url)
    if (res.error) { failures.push({ url: node.url, error: res.error }); return }
    await writeOut(`raw${node.url}`, res.text)

    const x = extract(res.text, node, urlToMd)
    if (!x) { failures.push({ url: node.url, error: 'no div.main-section' }); return }
    if (x.collapsibles) failures.push({ url: node.url, error: `${x.collapsibles} collapsible(s) — needs browser pass` })

    const mdRel = mdPathFor(node)
    const fm = [
      '---',
      `title: ${JSON.stringify(node.title)}`,
      `url: ${JSON.stringify(BASE + node.url)}`,
      `source: ${JSON.stringify(node.url)}`,
      `toc_path:${yamlList(node.toc_path)}`,
      `sections:${yamlList(x.sections)}`,
      `images:${yamlList(x.images.map((im) => im.src))}`,
      `source_sha1: ${sha1(res.text)}`,
      '---',
      '',
    ].join('\n')
    const heading = x.hasH1 ? '' : `# ${node.title}\n\n`
    await writeOut(`md/${mdRel}`, fm + heading + x.body.trim() + '\n')

    for (const im of x.images) {
      const rec = icons.get(im.src) ?? { src: im.src, alt: [], used_on: [], sha1: null }
      if (im.alt && !rec.alt.includes(im.alt)) rec.alt.push(im.alt)
      if (!rec.used_on.includes(node.url)) rec.used_on.push(node.url)
      icons.set(im.src, rec)
    }

    for (const t of x.tables) {
      if (!t.is_field_table) continue
      for (const row of t.rows) {
        if (!row[0]) continue
        fields.push({
          field: row[0],
          description: row.slice(1).join(' — ').trim(),
          table_caption: t.caption,
          page_url: node.url,
          page_title: node.title,
          toc_path: node.toc_path,
        })
      }
    }

    pages.push({
      id: node.id,
      url: node.url,
      title: node.title,
      md: mdRel,
      toc_path: node.toc_path,
      sections: x.sections,
      outlinks: x.outlinks,
      inlinks: [],
      images: x.images,
      tables: x.tables.map((t) => ({
        caption: t.caption,
        headers: t.headers,
        row_count: t.rows.length,
        is_field_table: t.is_field_table,
      })),
      word_count: x.body.split(/\s+/).length,
    })

    if ((i + 1) % 25 === 0) console.log(`  ${i + 1}/${topics.length}`)
  })

  console.log(`downloading ${icons.size} images…`)
  await pool([...icons.values()], async (rec) => {
    if (rec.src.startsWith('http')) return
    const res = await get(BASE + rec.src, { binary: true })
    if (res.error) { failures.push({ url: rec.src, error: res.error }); return }
    rec.sha1 = sha1(res.buf)
    await writeOut(`images${rec.src.replace(/^\/content/, '')}`, res.buf)
  })

  const byUrl = new Map(pages.map((p) => [p.url, p]))
  for (const p of pages) {
    for (const l of p.outlinks) {
      if (l.external) continue
      const t = byUrl.get(l.url)
      if (t && !t.inlinks.includes(p.url)) t.inlinks.push(p.url)
    }
  }

  const graph = {
    nodes: pages.map((p) => ({ id: p.id, url: p.url, title: p.title })),
    edges: [
      ...nodes
        .filter((n) => n.parent_id !== null && byUrl.has(n.url))
        .map((n) => ({ type: 'parent', from: nodes.find((m) => m.id === n.parent_id)?.url, to: n.url })),
      ...pages.flatMap((p) =>
        p.outlinks.filter((l) => !l.external && byUrl.has(l.url)).map((l) => ({ type: 'xref', from: p.url, to: l.url })),
      ),
    ].filter((e) => e.from && e.to),
  }

  await writeOut('index/pages.json', JSON.stringify(pages, null, 1))
  await writeOut('index/fields.json', JSON.stringify(fields, null, 1))
  await writeOut('index/icons.json', JSON.stringify([...icons.values()], null, 1))
  await writeOut('index/graph.json', JSON.stringify(graph, null, 1))
  await writeOut(
    'index/manifest.json',
    JSON.stringify(
      {
        base: BASE,
        product: 'Supply Chain Execution Web Applications',
        product_version: '2022.1.0.0',
        flare_build_version: buildVersion,
        fetched_at: new Date().toISOString(),
        scope: all ? 'all' : 'Warehouse Management > Configuration',
        counts: {
          toc_nodes: nodes.length,
          topics_in_scope: topics.length,
          pages: pages.length,
          fields: fields.length,
          images: icons.size,
          edges: graph.edges.length,
        },
        failures,
      },
      null,
      1,
    ),
  )

  console.log(
    `done: ${pages.length} pages, ${fields.length} field rows, ${icons.size} images, ${graph.edges.length} edges, ${failures.length} failures`,
  )
}

async function check() {
  const fail = []
  const ok = (cond, msg) => { if (!cond) fail.push(msg) }

  const { nodes } = await buildToc()
  ok(nodes.length === 586, `toc nodes ${nodes.length} != 586`)
  ok(new Set(nodes.map((n) => n.url)).size === 585, `unique urls ${new Set(nodes.map((n) => n.url)).size} != 585`)

  const pages = JSON.parse(await readFile(path.join(OUT, 'index/pages.json'), 'utf8'))
  const icons = JSON.parse(await readFile(path.join(OUT, 'index/icons.json'), 'utf8'))
  const fields = JSON.parse(await readFile(path.join(OUT, 'index/fields.json'), 'utf8'))

  for (const p of pages) {
    ok(p.title, `empty title ${p.url}`)
    ok(p.word_count > 3, `empty body ${p.url}`)
    ok(existsSync(path.join(OUT, 'md', p.md)), `missing md ${p.md}`)
  }

  const wh = pages.find((p) => p.url === '/content/warehouses.htm')
  if (wh) {
    const ft = wh.tables.filter((t) => t.is_field_table).map((t) => t.caption)
    ok(ft.length >= 5, `warehouses.htm field tables ${ft.length} < 5`)
    ok(ft.includes('Warehouse fields'), 'warehouses.htm missing "Warehouse fields"')
    ok(ft.includes('Address fields'), 'warehouses.htm missing "Address fields"')
  }

  const pl = pages.find((p) => p.url === '/content/people_labor_section.htm')
  if (pl) ok(pl.images.some((i) => i.alt === 'My Details'), 'people_labor_section missing "My Details" icon')

  for (const ic of icons) {
    if (ic.src.startsWith('http')) continue
    ok(existsSync(path.join(OUT, 'images', ic.src.replace(/^\/content/, ''))), `missing image ${ic.src}`)
  }

  // every internal md link resolves on disk
  const walkMd = async (dir) => {
    const out = []
    for (const e of await readdir(dir, { withFileTypes: true })) {
      const p = path.join(dir, e.name)
      if (e.isDirectory()) out.push(...(await walkMd(p)))
      else if (e.name.endsWith('.md')) out.push(p)
    }
    return out
  }
  for (const f of await walkMd(path.join(OUT, 'md'))) {
    const txt = await readFile(f, 'utf8')
    for (const m of txt.matchAll(/\]\((\.{1,2}\/[^)\s]+\.md)\)/g)) {
      ok(existsSync(path.resolve(path.dirname(f), m[1])), `dead link ${m[1]} in ${path.relative(OUT, f)}`)
    }
  }

  ok(fields.length > 100, `fields ${fields.length} <= 100`)

  if (fail.length) {
    console.error(`FAIL ${fail.length}:`)
    for (const f of fail.slice(0, 40)) console.error('  ' + f)
    process.exit(1)
  }
  console.log(`check OK — ${pages.length} pages, ${fields.length} fields, ${icons.length} images`)
}

const args = process.argv.slice(2)
if (args.includes('--check')) await check()
else await run(args.includes('--all'))
