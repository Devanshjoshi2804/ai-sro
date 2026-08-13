#!/usr/bin/env node
// Second pass over the scraped corpus: derive the automation-facing indexes.
// Reads knowlegde_graph/blue-yonder-sce/md + index/pages.json, writes index/{navigation,procedures,ui-vocabulary}.json.
// No network.
//
//   node tools/derive-kb.mjs
//   node tools/derive-kb.mjs --check

import { readFile, writeFile } from 'node:fs/promises'
import path from 'node:path'

const OUT = path.resolve(import.meta.dirname, '../knowlegde_graph/blue-yonder-sce')

// "Select Configuration > Warehouse > Locations > Dock Locations."
// A segment is space-separated words — written this way so a trailing space is never
// swallowed into the segment, which would eat the next " > " separator.
const SEG = "[A-Za-z0-9&/'()-]+(?: +[A-Za-z0-9&/'()-]+)*"
const NAV = new RegExp(`\\b[Ss]elect (${SEG}(?: > ${SEG})+)`, 'g')
const BOLD = /\*\*([^*]+?)\*\*/g
const IMG = /!\[([^\]]*)\]\(([^)\s]+)\)/g
const LINK = /(?<!!)\[([^\]]+)\]\(([^)\s]+)\)/g
const STEP = /^(\s*)(\d+)\.\s+(.*)$/
const FIELDS_HEADING = /fields?$/i

const clean = (s) => s.replace(/\s+/g, ' ').trim().replace(/[.,;:]+$/, '')

// Menu labels are Title Case; a lowercase word is only part of the label when a
// capitalized word follows it ("Waves and Picks"). Anything past that is sentence
// prose that the greedy segment match swallowed ("Waves and then click Release").
function trimLabel(seg) {
  const w = seg.split(' ')
  const end = w.findIndex(
    (word, i) => /^[a-z]/.test(word) && !/^[A-Z0-9]/.test(w[i + 1] ?? ''),
  )
  return (end === -1 ? w : w.slice(0, end)).join(' ')
}

const navPath = (raw) => clean(raw).split(' > ').map((s) => trimLabel(clean(s))).filter(Boolean)

function parse(md) {
  const lines = md.split('\n')
  const start = lines.indexOf('---', 1) + 1 // skip front matter
  const out = { sections: [] }
  let cur = null
  for (const line of lines.slice(start)) {
    const h = /^(#{1,3})\s+(.*)$/.exec(line)
    if (h) {
      cur = { level: h[1].length, name: clean(h[2]), lines: [] }
      out.sections.push(cur)
      continue
    }
    cur?.lines.push(line)
  }
  return out
}

function stepsOf(lines) {
  const steps = []
  let last = null
  for (const line of lines) {
    const m = STEP.exec(line)
    if (m) {
      last = { depth: Math.floor(m[1].length / 4), n: Number(m[2]), text: m[3].trim() }
      steps.push(last)
      continue
    }
    // continuation: bullets and prose indented under the current step
    const t = line.trim()
    if (last && t && /^[-*]\s|^\*\*(Note|IMPORTANT|Tip|Warning)/.test(t)) {
      last.text += ' ' + t.replace(/^[-*]\s+/, '• ')
    } else if (!t) {
      last = null
    }
  }
  return steps
}

// markdown markers stripped: menu paths arrive as **Configuration** > **Warehouse**
const plain = (s) => s.replace(IMG, '$1').replace(LINK, '$1').replace(BOLD, '$1')

function annotate(text) {
  const nav = [...plain(text).matchAll(NAV)].map((m) => navPath(m[1])).filter((p) => p.length > 1)
  const labels = [...text.matchAll(BOLD)]
    .map((m) => clean(m[1]))
    .filter((b) => b && !/^(Note|IMPORTANT|Tip|Warning|Caution)$/i.test(b))
  const icons = [...text.matchAll(IMG)].map((m) => ({ alt: m[1], src: m[2] }))
  const fieldRefs = [...text.matchAll(LINK)]
    .filter((m) => FIELDS_HEADING.test(m[1]))
    .map((m) => clean(m[1]))
  const seeAlso = [...text.matchAll(LINK)]
    .filter((m) => !FIELDS_HEADING.test(m[1]))
    .map((m) => ({ title: clean(m[1]), href: m[2] }))
  return { nav, labels, icons, fieldRefs, seeAlso }
}

async function run() {
  const pages = JSON.parse(await readFile(path.join(OUT, 'index/pages.json'), 'utf8'))

  const procedures = []
  const navHits = new Map() // "A > B > C" -> Set(page urls)
  const labelHits = new Map()
  const iconHits = new Map()

  for (const p of pages) {
    const md = await readFile(path.join(OUT, 'md', p.md), 'utf8')
    const { sections } = parse(md)

    for (const sec of sections) {
      const text = sec.lines.join('\n')
      const steps = stepsOf(sec.lines)
      const secAnn = annotate(text)

      for (const n of secAnn.nav) {
        const key = n.join(' > ')
        if (!navHits.has(key)) navHits.set(key, new Set())
        navHits.get(key).add(p.url)
      }
      for (const b of secAnn.labels) labelHits.set(b, (labelHits.get(b) ?? 0) + 1)
      for (const ic of secAnn.icons) {
        const rec = iconHits.get(ic.alt) ?? { alt: ic.alt, count: 0, pages: new Set() }
        rec.count++
        rec.pages.add(p.url)
        iconHits.set(ic.alt, rec)
      }

      // a section with an ordered list and a non-"fields" title is a procedure
      if (!steps.length || FIELDS_HEADING.test(sec.name)) continue
      procedures.push({
        name: sec.name,
        page_url: p.url,
        page_title: p.title,
        toc_path: p.toc_path,
        md: p.md,
        entry_nav: secAnn.nav[0] ?? null,
        field_tables: [...new Set(secAnn.fieldRefs)],
        steps: steps.map((s) => {
          const a = annotate(s.text)
          return {
            depth: s.depth,
            n: s.n,
            text: clean(plain(s.text)),
            nav_path: a.nav[0] ?? null,
            labels: [...new Set(a.labels)],
            icons: a.icons.map((i) => i.alt).filter(Boolean),
            see_also: a.seeAlso,
          }
        }),
      })
    }
  }

  // menu tree from every observed "Select A > B > C"
  const root = { name: null, children: {}, pages: [] }
  for (const [key, urls] of navHits) {
    let node = root
    for (const part of key.split(' > ')) {
      node.children[part] ??= { name: part, children: {}, pages: [] }
      node = node.children[part]
    }
    node.pages = [...urls].sort()
  }
  const toTree = (n) => ({
    name: n.name,
    pages: n.pages,
    children: Object.values(n.children).sort((a, b) => a.name.localeCompare(b.name)).map(toTree),
  })
  const navigation = toTree(root).children

  const vocabulary = {
    labels: [...labelHits.entries()]
      .sort((a, b) => b[1] - a[1])
      .map(([label, count]) => ({ label, count })),
    icons: [...iconHits.values()]
      .sort((a, b) => b.count - a.count)
      .map((i) => ({ alt: i.alt, count: i.count, pages: [...i.pages].sort() })),
  }

  await writeFile(path.join(OUT, 'index/navigation.json'), JSON.stringify(navigation, null, 1))
  await writeFile(path.join(OUT, 'index/procedures.json'), JSON.stringify(procedures, null, 1))
  await writeFile(path.join(OUT, 'index/ui-vocabulary.json'), JSON.stringify(vocabulary, null, 1))

  const leaves = (ns) => ns.reduce((a, n) => a + (n.children.length ? leaves(n.children) : 1), 0)
  console.log(
    `navigation: ${navigation.length} roots, ${leaves(navigation)} leaf paths\n` +
      `procedures: ${procedures.length}, ${procedures.reduce((a, p) => a + p.steps.length, 0)} steps\n` +
      `vocabulary: ${vocabulary.labels.length} UI labels, ${vocabulary.icons.length} icon labels`,
  )
}

async function check() {
  const fail = []
  const ok = (c, m) => { if (!c) fail.push(m) }
  const nav = JSON.parse(await readFile(path.join(OUT, 'index/navigation.json'), 'utf8'))
  const procs = JSON.parse(await readFile(path.join(OUT, 'index/procedures.json'), 'utf8'))
  const vocab = JSON.parse(await readFile(path.join(OUT, 'index/ui-vocabulary.json'), 'utf8'))

  ok(nav.some((n) => n.name === 'Configuration'), 'navigation missing Configuration root')
  const cfg = nav.find((n) => n.name === 'Configuration')
  ok(cfg?.children.some((c) => c.name === 'Warehouse'), 'Configuration > Warehouse missing')

  const wh = procs.find((p) => p.name === 'Add or modify a warehouse')
  ok(wh, 'procedure "Add or modify a warehouse" missing')
  ok(wh?.steps.length >= 3, `warehouse procedure has ${wh?.steps.length} steps`)
  ok(
    wh?.steps[0].nav_path?.join(' > ') === 'Configuration > Warehouse > Warehouse',
    `warehouse step 1 nav_path = ${wh?.steps[0].nav_path}`,
  )
  ok(wh?.field_tables.includes('Warehouse fields'), 'warehouse procedure missing Warehouse fields ref')

  ok(procs.every((p) => p.name && p.page_url && p.steps.length), 'procedure with empty name/url/steps')
  ok(procs.every((p) => p.steps.every((s) => !/\*\*|\]\(/.test(s.text))), 'markup leaked into step text')
  ok(vocab.labels.some((b) => b.label === 'Save'), 'vocabulary missing Save label')
  ok(vocab.icons.some((i) => i.alt === 'Lookup'), 'vocabulary missing Lookup icon')

  if (fail.length) {
    console.error(`FAIL ${fail.length}:`)
    for (const f of fail.slice(0, 30)) console.error('  ' + f)
    process.exit(1)
  }
  console.log(`check OK — ${procs.length} procedures, ${vocab.labels.length} UI labels`)
}

if (process.argv.includes('--check')) await check()
else await run()
