"""Refuse real names in the public ACE repository. Prints the hits; exit 1 when any.

  python -B scripts/check_public.py [--staged]

The real names come only from the user's local profile (never from this repository): <profile>/profile.json
(base_forms, framework_markers, number_table, numbering_sp, save_calls keys, private_words, private_regex),
<profile>/designer.json (control_prefix, label_type, name_prefix keys), the file names in <profile>/projects/ and
the protected_db entries of ~/.claude/ace/config.json. <profile> = $ACE_PROFILE_DIR or ~/.claude/ace/profile.
Without a local profile nothing is checked. Install as the clone's pre-commit hook:
  printf '#!/bin/sh\\npython -B scripts/check_public.py --staged\\n' > .git/hooks/pre-commit
"""
import io
import json
import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = os.path.expanduser('~')
PROFILE = os.environ.get('ACE_PROFILE_DIR') or os.path.join(HOME, '.claude', 'ace', 'profile')


def load(path):
    try:
        with io.open(path, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


def words():
    prof = load(os.path.join(PROFILE, 'profile.json'))
    des = load(os.path.join(PROFILE, 'designer.json'))
    cfg = load(os.path.join(HOME, '.claude', 'ace', 'config.json'))
    w = set()
    for key in ('base_forms', 'framework_markers', 'private_words'):
        w.update(prof.get(key) or [])
    for key in ('number_table', 'numbering_sp', 'profile'):
        if prof.get(key):
            w.add(prof[key])
    w.update((prof.get('save_calls') or {}).keys())
    w.update((des.get('name_prefix') or {}).keys())
    if des.get('label_type'):
        w.add(des['label_type'])
    w.update(cfg.get('protected_db') or [])
    pdir = os.path.join(PROFILE, 'projects')
    if os.path.isdir(pdir):
        w.update(os.path.splitext(f)[0] for f in os.listdir(pdir) if f.endswith('.md'))
    return sorted((x.strip('.') for x in w if x and len(x.strip('.')) >= 3), key=len, reverse=True)


def tracked(staged):
    cmd = ['git', '-C', ROOT, 'diff', '--cached', '--name-only', '--diff-filter=ACMR'] if staged else \
        ['git', '-C', ROOT, 'ls-files', '-co', '--exclude-standard']
    out = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8').stdout
    return [l.strip() for l in out.split('\n') if l.strip()]


def main(argv):
    ws = words()
    if not ws:
        print('check_public: no local profile, nothing checked')
        return 0
    extra = load(os.path.join(PROFILE, 'profile.json')).get('private_regex') or []
    rx = re.compile('|'.join([r'(?<![A-Za-z0-9])' + re.escape(x) + r'(?![a-z0-9])' for x in ws] + extra), re.I)
    hits = []
    for rel in tracked('--staged' in argv):
        p = os.path.join(ROOT, rel)
        if not os.path.isfile(p):
            continue
        try:
            text = io.open(p, encoding='utf-8').read()
        except (UnicodeDecodeError, OSError):
            continue
        for i, line in enumerate(text.split('\n'), 1):
            m = rx.search(line)
            if m:
                hits.append('%s:%d: %s' % (rel, i, m.group(0)))
    if hits:
        print('check_public: real names from the local profile in the repository (use the example profile):')
        print('\n'.join(hits[:50]) + ('\n... %d more' % (len(hits) - 50) if len(hits) > 50 else ''))
        return 1
    print('check_public: OK (%d private words)' % len(ws))
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
