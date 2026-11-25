"""Draft a framework profile for an unfamiliar WinForms solution (ideas from ECC codebase-onboarding / code-explorer, MIT).

  python map_project.py <solution folder> [--name <PROJECT>] [--md <out.md>]

Scans .cs / .Designer.cs files (bin, obj, backup folders skipped) and counts what the screens actually use:
base form class, edit-mode enum, control types and their prefix, DB call methods, grid→XML helper, message
methods, code-binding helper, SP names and modules. Prints a Markdown draft of the role table in
<profile>/profile.md plus a <profile>/projects/<PROJECT>.md skeleton (local only, never in the repo). Counts are evidence; check the top file of each row
before writing names into rules.
"""
import argparse
import collections
import io
import os
import re
import sys

SKIP = {'bin', 'obj', 'backup', '.svn', '.git', 'packages', '.vs', 'node_modules'}


def read(p):
    for enc in ('utf-8-sig', 'cp949', 'utf-16'):
        try:
            with io.open(p, encoding=enc) as f:
                return f.read()
        except (UnicodeError, OSError):
            continue
    return ''


def walk(root):
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x.lower() not in SKIP and 'backup' not in x.lower()]
        for f in files:
            if f.endswith('.cs'):
                yield os.path.join(d, f)


def top(counter, n=3):
    return ', '.join('`%s` (%d)' % (k, v) for k, v in counter.most_common(n)) or '없음'


def main(argv):
    ap = argparse.ArgumentParser()
    ap.add_argument('root')
    ap.add_argument('--name')
    ap.add_argument('--md')
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    root = os.path.abspath(a.root)
    name = a.name or os.path.basename(root.rstrip('\\/'))
    C = collections.Counter
    base, ctypes, prefixes, dbcalls, xml, msgs, binds, sps, mods, enums, users = C(), C(), C(), C(), C(), C(), C(), C(), C(), {}, C()
    screens, files = 0, 0
    for p in walk(root):
        files += 1
        t = read(p)
        if p.endswith('.Designer.cs'):
            for typ in re.findall(r'^\s*(?:private|protected|internal|public)\s+([\w\.]+)\s+\w+\s*;', t, re.M):
                short = typ.split('.')[-1]
                ctypes[short] += 1
                m = re.match(r'([a-z]+_|[A-Z][a-z]+(?=[A-Z]))', short)
                if m and not typ.startswith(('System.', 'DevExpress.')):
                    prefixes[m.group(1)] += 1
            continue
        for cls, b in re.findall(r'\bpartial\s+class\s+(\w+)\s*:\s*([\w\.]+)', t):
            base[b.split('.')[-1]] += 1
            if os.path.isfile(p[:-3] + '.Designer.cs'):
                screens += 1
                rel = os.path.relpath(os.path.dirname(p), root).split(os.sep)
                mods[rel[1] if len(rel) > 1 and rel[0].lower() == 'programs' else rel[0]] += 1
        for en, body in re.findall(r'\benum\s+(\w*(?:Mode|Edit)\w*)\s*\{([^}]*)\}', t):
            enums.setdefault(en, (p, ' '.join(x.strip() for x in body.split(',') if x.strip())))
        for obj, meth in re.findall(r'\b(\w+)\.(Exec\w*|GetDataSet\w*|GetDataTable\w*|ExecuteNonQuery|Fill)\s*\(', t):
            dbcalls['%s.%s' % (obj, meth)] += 1
        xml.update(re.findall(r'\b(\w+\.\w*ToXml\w*|\w*ToXml\w*)\s*\(', t))
        msgs.update(re.findall(r'\b((?:Show)?(?:Message|Msg)\w*|MessageBox\.Show|XtraMessageBox\.Show)\s*\(', t))
        binds.update(re.findall(r'\b(\w+\.Binding\w*Code|\w+\.Bind\w*Code\w*)\s*\(', t))
        sps.update(re.findall(r'"((?:sp|SP|usp|USP)_\w+)"', t))
        users.update(re.findall(r'\b(userInfo\.\w+|UserInfo\.\w+|LoginInfo\.\w+)', t))
    sp_pref = C(re.sub(r'_(SELECT|SAVE|SEL|INS|UPD|DEL)$', r'_<\1>', s, flags=re.I).split('_')[0] for s in sps)
    lines = ['# %s: framework profile draft' % name, '',
             '%s, %d .cs files, %d screens (class with a Designer). Counts = uses; check the top file before using a name.' % (root, files, screens), '',
             '| Role | Found | Count/evidence |', '| --- | --- | --- |',
             '| Base form class | %s | screens inheriting it |' % top(base, 2),
             '| Edit-mode enum | %s | %s |' % (', '.join('`%s`' % k for k in list(enums)[:2]) or '없음',
                                           '; '.join('%s: %s' % (k, v[1][:80]) for k, v in list(enums.items())[:2]) or ''),
             '| Control library prefix | %s | Designer field types |' % top(prefixes, 2),
             '| Most used control types | %s | |' % top(ctypes, 6),
             '| DB calls | %s | |' % top(dbcalls, 4),
             '| Grid → XML | %s | |' % top(xml, 2),
             '| Messages | %s | |' % top(msgs, 4),
             '| Code binding | %s | |' % top(binds, 2),
             '| User/session info | %s | |' % top(users, 3),
             '| SP name prefix | %s | %d SP names in code |' % (top(sp_pref, 2), len(sps)),
             '| Modules (screens) | %s | |' % top(mods, 8),
             '', '## projects/%s.md skeleton' % name, '',
             '| Fact | Detail | Source |', '| --- | --- | --- |',
             '| Edit modes | %s | %s |' % ('; '.join('%s = %s' % (k, v[1][:60]) for k, v in list(enums.items())[:1]) or '확인 필요',
                                         os.path.relpath(next(iter(enums.values()))[0], root) if enums else ''),
             '| Save call | %s | count |' % top(C({k: v for k, v in dbcalls.items() if 'Exec' in k}), 2),
             '| DB | 확인 필요 (connection settings of the solution) | |']
    text = '\n'.join(lines) + '\n'
    if a.md:
        io.open(a.md, 'w', encoding='utf-8').write(text)
    print(text)
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
