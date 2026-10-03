import glob, io, os, re

R = []
def add(s=''):
    R.append(s)

tpl = sorted(set(glob.glob('templates/**/*.html', recursive=True)))
add('TEMPLATES total: %d' % len(tpl))
add('')

hx = {}
for p in tpl:
    s = io.open(p, encoding='utf-8', errors='replace').read()
    f = re.findall(r'hx-[a-zA-Z0-9_-]+', s)
    if f:
        hx[p] = f
add('== HTMX: files=%d attrs=%d' % (len(hx), sum(len(v) for v in hx.values())))
for p in sorted(hx):
    add('   %-52s %s' % (p.replace(chr(92),'/'), dict((k, hx[p].count(k)) for k in sorted(set(hx[p])))))
add('')

ht = []
for p in tpl:
    s = io.open(p, encoding='utf-8', errors='replace').read()
    for m in re.findall(r'[^\s"\'<>]*htmx[^\s"\'<>]*', s, re.I):
        ht.append((p, m))
add('== HTMX script/url refs: %d' % len(ht))
for p, m in ht:
    add('   %-52s %s' % (p.replace(chr(92),'/'), m))
add('')

tw = []
for p in tpl:
    s = io.open(p, encoding='utf-8', errors='replace').read()
    if re.search('tailwind', s, re.I):
        tw.append(p)
add('== TAILWIND in templates: %d' % len(tw))
for p in tw:
    add('   ' + p.replace(chr(92),'/'))
for p in ['static/js/app.js','static/js/ghdi-site.js','static/css/ghdi.css','static/css/ghdi-site.css','static/css/ghdi-premium.css','static/css/ghdi-compat.css']:
    if os.path.exists(p):
        s = io.open(p, encoding='utf-8', errors='replace').read()
        if re.search('tailwind', s, re.I):
            add('   TAILWIND-in: ' + p)
for p in sorted(glob.glob('*.js') + glob.glob('*.json')):
    add('   ROOT-FILE: ' + p)
add('')

for p in tpl:
    s = io.open(p, encoding='utf-8', errors='replace').read()
    if re.search('alpine|x-data|x-init', s, re.I):
        add('   ALPINE-in: ' + p.replace(chr(92),'/'))
add('')

add('== STATIC TREE')
for root, d, fs in os.walk('static'):
    for f in sorted(fs):
        fp = os.path.join(root, f).replace(chr(92),'/')
        add('   %-58s %8d' % (fp, os.path.getsize(fp)))
add('')

add('== EXTENDS MAP')
for p in tpl:
    s = io.open(p, encoding='utf-8', errors='replace').read()
    m = re.search(r'{%\s*extends\s+["\']([^"\']+)', s)
    add('   %-52s -> %s' % (p.replace(chr(92),'/'), m.group(1) if m else '(none)'))
add('')

add('== TESTS mentioning htmx/tailwind/design-system')
for p in sorted(glob.glob('apps/**/*.py', recursive=True)):
    s = io.open(p, encoding='utf-8', errors='replace').read().lower()
    hits = [k for k in ['htmx','hx-','tailwind','designsystemcss','htmxlist','bootstrap'] if k in s]
    if hits:
        add('   %-52s %s' % (p.replace(chr(92),'/'), hits))
add('')

add('=' * 70)
add('BASE HTML (templates/base.html)')
add('=' * 70)
if os.path.exists('templates/base.html'):
    add(io.open('templates/base.html', encoding='utf-8', errors='replace').read())
add('')
add('=' * 70)
add('WEBSITE BASE (templates/website/base_site.html)')
add('=' * 70)
if os.path.exists('templates/website/base_site.html'):
    add(io.open('templates/website/base_site.html', encoding='utf-8', errors='replace').read())

io.open('MIGRATION_AUDIT.txt', 'w', encoding='utf-8').write('\n'.join(R))
print('\n'.join(R))
