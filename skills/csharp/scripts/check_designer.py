"""ACE csharp 기계 점검. 사용법:
python check_designer.py <X.Designer.cs | X.cs> [--original <원본 사본>] [--project <솔루션 루트>]
                         [--sibling <형제.Designer.cs> ...]
*.Designer.cs는 Designer 점검, 그 밖의 .cs는 비하인드 코드 점검이다. --original이 있으면 원본에 없던 것만 판정한다.
마지막 줄은 'ACE-CHECK: PASS 통과/판정' 또는 'ACE-CHECK: FAIL 통과/판정'. 실패가 있으면 종료 코드 1.
"""
import argparse
import io
import json
import os
import re
import sys

PASS, FAIL, CHECK = '통과', '실패', '확인'


def profile_dir():
    """Local framework profile (real names never ship in the repo): $ACE_PROFILE_DIR or ~/.claude/ace/profile."""
    return os.environ.get('ACE_PROFILE_DIR') or os.path.join(os.path.expanduser('~'), '.claude', 'ace', 'profile')


def load_framework():
    """프로필의 컨트롤 값(<profile>/designer.json, 형식은 skills/erp/data/designer.example.json). 없으면 빈 값:
    컨트롤 라이브러리 크기·블록·역할·접두어 점검을 건너뛴다."""
    p = os.path.join(profile_dir(), 'designer.json')
    try:
        with io.open(p, encoding='utf-8') as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError):
        return {}


FW = load_framework()
# 프로필 컨트롤의 생성자 base.Size. --project에서 컨트롤 소스를 찾으면 그 값을 쓴다
CTRL_PREFIX = FW.get('control_prefix') or None
LABEL = FW.get('label_type') or None
DEFAULTS = {k: tuple(v) for k, v in FW.get('defaults', {}).items()}
EXTRA_W = {k: set(v) for k, v in FW.get('extra_width', {}).items()}  # erp controls.md 날짜 블록의 폭
SINGLE = set(FW.get('single_line', []))
# 이름 접두어(erp controls.md#names): DevExpress 형식 + 프로필 컨트롤(designer.json name_prefix)
PREFIX = {'SimpleButton': 'btn', 'GroupControl': 'grp', 'GridControl': 'grd', 'GridView': 'gvw',
          'BandedGridView': 'gvw', 'SplitterControl': 'splitter|split', 'RepositoryItemLookUpEdit': 'rpscbo',
          'RepositoryItemButtonEdit': 'rpsbtn', 'RepositoryItemCheckEdit': 'rpschk', 'RepositoryItemSpinEdit': 'rpsSpin',
          'TreeList': 'treeList'}
PREFIX.update(FW.get('name_prefix', {}))
DEFAULT_NAME = re.compile(r'^(' + (re.escape(CTRL_PREFIX) + r'[A-Za-z]+|' if CTRL_PREFIX else '') + r'gridColumn|bandedGridColumn|gridBand|gridView|bandedGridView|gridControl'
                          r'|repositoryItem[A-Za-z]+|labelControl|textEdit|simpleButton|panelControl|groupControl'
                          r'|splitterControl|treeListColumn|xtraTabPage|xtraTabControl|checkEdit|lookUpEdit)\d+$')
TABLE = re.compile(r'^(Tab\d)?[A-Z]{2}\d{3}T\d?$')
# 기준 프로젝트 화면의 그리드 역할 이름(designer.json grid_roles). 목록 List, 상세 Detail, 테이블 기준 grd<테이블>은 따로 허용
ROLES = set(FW.get('grid_roles', [])) | {'List', 'Detail'}
# erp controls.md 블록 필수 줄: 버튼은 사용자 화면 100%, Mask·Display/ValueMember는 82~92%라 [확인]
REQUIRED = {k: tuple(v) for k, v in FW.get('required', {}).items()}
USUAL = {k: tuple(v) for k, v in FW.get('usual', {}).items()}
SKIP_LAYOUT = {'TableLayoutPanel', 'FlowLayoutPanel', 'LayoutControl'}


def read_text(path):
    with io.open(path, 'rb') as f:
        data = f.read()
    for enc in ('utf-8-sig', 'cp949'):
        try:
            return data.decode(enc).replace('\r\n', '\n').replace('\r', '\n')
        except UnicodeError:
            continue
    raise ValueError('인코딩을 읽을 수 없음: ' + path)


def size_of(v):
    m = re.search(r'Size\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', v or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


def point_of(v):
    m = re.search(r'Point\(\s*(-?\d+)\s*,\s*(-?\d+)\s*\)', v or '')
    return (int(m.group(1)), int(m.group(2))) if m else None


class Designer(object):
    def __init__(self, text):
        self.types, self.props, self.parent, self.cols, self.events, self.main = {}, {}, {}, {}, [], {}
        self.has_count = 'SummaryItemType.Count' in text
        lines = text.split('\n')
        start = next((i for i, l in enumerate(lines) if 'void InitializeComponent' in l), 0)
        view = None
        for i in range(start, len(lines)):
            l, n = lines[i], i + 1
            if view:
                for c in re.findall(r'this\.(\w+)', l):
                    self.cols[view].append((c, n))
                if '}' in l:
                    view = None
                continue
            m = re.match(r'\s*this\.(\w+)\s*=\s*new\s+([\w.]+)\s*\(', l)
            if m:
                self.types[m.group(1)] = (m.group(2).split('.')[-1], n)
                continue
            m = re.match(r'\s*this\.(\w+)\.Columns\.AddRange\(', l)
            if m:
                view = m.group(1)
                self.cols[view] = [(c, n) for c in re.findall(r'this\.(\w+)', l.split('{', 1)[-1])]
                if '}' in l:
                    view = None
                continue
            m = re.match(r'\s*this\.(?:(\w+)\.)?Controls\.Add\(this\.(\w+)\)', l)
            if m:
                self.parent[m.group(2)] = m.group(1) or 'this'
                continue
            m = re.match(r'\s*this\.([\w.]+?)\s*\+=', l)
            if m:
                self.events.append((m.group(1), n))
                continue
            m = re.match(r'\s*this\.(\w+)\.([\w.]+)\s*=\s*(.*?);?\s*$', l)
            if m:
                self.props.setdefault(m.group(1), {})[m.group(2)] = (m.group(3), n)
                if m.group(2) == 'MainView':
                    self.main[m.group(1)] = m.group(3).replace('this.', '')

    def typ(self, name):
        return self.types.get(name, ('', 0))[0]

    def prop(self, name, key):
        return self.props.get(name, {}).get(key, (None, 0))

    def line(self, name):
        return self.types.get(name, ('', 0))[1]

    def size(self, name, defaults):
        s = size_of(self.prop(name, 'Size')[0]) or defaults.get(self.typ(name))
        w, h = self.prop(name, 'Width')[0], self.prop(name, 'Height')[0]
        if s and (w or h):
            s = (int(w) if w and w.isdigit() else s[0], int(h) if h and h.isdigit() else s[1])
        return s

    def grid_suffixes(self):
        return {g[3:] for g in self.main if g.startswith('grd')}


def find_project(path):
    d = os.path.dirname(os.path.abspath(path))
    while d and os.path.dirname(d) != d:
        if any(f.endswith('.sln') for f in os.listdir(d)):
            return d
        d = os.path.dirname(d)
    return None


def project_info(root, self_path):
    """(생성자 기본 크기, 프로젝트 화면들의 그리드 이름 접미어)"""
    defaults, suffixes = {}, set()
    if not root:
        return defaults, suffixes
    me = os.path.normcase(os.path.abspath(self_path))
    for d, dirs, files in os.walk(root):
        dirs[:] = [x for x in dirs if x.lower() not in ('bin', 'obj', 'backup', '.svn', '.git', 'packages')]
        for f in files:
            p = os.path.join(d, f)
            if CTRL_PREFIX and f.startswith(CTRL_PREFIX) and f.endswith('.cs') and not f.lower().endswith('.designer.cs'):  # 프로필의 컨트롤 라이브러리 소스
                m = re.search(r'^\s*base\.Size\s*=\s*new\s+(?:System\.Drawing\.)?Size\((\d+),\s*(\d+)\)', read_text(p),
                              re.M)
                if m:
                    defaults[f[:-3]] = (int(m.group(1)), int(m.group(2)))
            elif f.lower().endswith('.designer.cs') and os.path.normcase(p) != me and 'BAK' not in f.upper():
                suffixes |= set(re.findall(r'this\.grd(\w+)\.MainView\s*=', read_text(p)))
    return defaults, suffixes


def first_locked(d, v):
    """편집 안 되는 보이는 열 중 VisibleIndex가 가장 작은 열(뷰 전체 Editable=false면 첫 보이는 열)."""
    view_ro = d.prop(v, 'OptionsBehavior.Editable')[0] == 'false' or d.prop(v, 'OptionsBehavior.ReadOnly')[0] == 'true'
    vis = []
    for c, _ in d.cols.get(v, []):
        if c not in d.types or d.prop(c, 'Visible')[0] != 'true':
            continue
        ro = (view_ro or d.prop(c, 'OptionsColumn.AllowEdit')[0] == 'false'
              or d.prop(c, 'OptionsColumn.ReadOnly')[0] == 'true')
        vi = d.prop(c, 'VisibleIndex')[0] or ''
        if ro:
            vis.append((int(vi) if vi.lstrip('-').isdigit() else 999, c))
    return min(vis)[1] if vis else None


def check_designer(raw, orig, sibs, defaults, proj_suffixes):
    d = Designer(raw)
    o = Designer(orig) if orig is not None else None
    # 이름은 새 컨트롤만, 배치·크기·정렬은 새 컨트롤과 속성을 바꾼 기존 컨트롤만 판정한다
    vals = lambda x, n: {k: v[0] for k, v in x.props.get(n, {}).items()}
    added = [n for n in d.types if o is None or n not in o.types]
    new = [n for n in d.types if n in added or vals(o, n) != vals(d, n) or o.parent.get(n) != d.parent.get(n)]
    r = []

    def item(name, ls, note='', st=FAIL):
        r.append((st if ls else PASS, name, sorted(set(ls)), note))

    bad, notes = [], []
    for n in new:
        if d.typ(n) != LABEL:
            continue
        for key, ok in (('Appearance.TextOptions.HAlignment', 'Far'), ('Appearance.TextOptions.VAlignment', 'Center'),
                        ('AutoSizeMode', 'None')):
            v, ln = d.prop(n, key)
            if v is not None and not v.endswith('.' + ok):
                bad.append(ln)
                notes.append('%s.%s=%s' % (n, key.split('.')[-1], v.split('.')[-1]))
    item('라벨 오른쪽 정렬·세로 가운데·AutoSizeMode None', bad, ', '.join(notes[:6]))

    bad, notes, tall = [], [], []
    for n in new:
        t = d.typ(n)
        if t not in SINGLE and t != LABEL:
            continue
        s = d.size(n, defaults)
        # 기존 컨트롤의 높이가 원본과 같으면 판정하지 않는다(폭만 바꿨는데 Size 줄 전체가 걸리던 오탐, QR 입력 칸 66·72)
        was = o.size(n, defaults) if o is not None and n in o.types else None
        if s and s[1] != 25 and not (was and was[1] == s[1]):
            (tall if t == LABEL and s[1] > 25 else bad).append(d.prop(n, 'Size')[1] or d.line(n))
            notes.append('%s 높이 %d' % (n, s[1]))
        for key, free in (('MaximumSize', 65535), ('MinimumSize', 0)):  # free = 생성자 기본(제한 없음)
            v, ln = d.prop(n, key)
            ov = size_of(o.prop(n, key)[0]) if o is not None and n in o.types else None
            if size_of(v) and ov and ov[1] == size_of(v)[1]:
                continue
            if size_of(v) and size_of(v)[1] not in (25, free):
                bad.append(ln)
                notes.append('%s.%s' % (n, key))
    # 확인 항목: 사용자가 높이를 요청하는 경우가 있다(QR 입력 칸 72). 훅이 막지 않고 답변에서 요청과 맞는지 밝힌다
    item('라벨·한 줄 입력 높이 25(Maximum/MinimumSize 높이 25)', bad, ', '.join(notes[:6]) + (' / 요청한 높이면 그대로 둔다' if bad else ''), st=CHECK)
    if tall:
        r.append((CHECK, '두 줄 높이 라벨', tall, '여러 줄 영역을 덮는 라벨인지 확인'))

    accepted = {t: {w} | EXTRA_W.get(t, set()) for t, (w, h) in defaults.items()}
    for other in sibs + ([o] if o else []):
        for n in other.types:
            s = size_of(other.prop(n, 'Size')[0])
            if s and other.typ(n) in accepted:
                accepted[other.typ(n)].add(s[0])
    odd = []
    for n in new:
        t, s = d.typ(n), size_of(d.prop(n, 'Size')[0])
        if t in accepted and s and s[0] not in accepted[t] and d.prop(n, 'Visible')[0] != 'false':
            odd.append((n, t, s[0], d.prop(n, 'Size')[1]))
    groups = {}
    for n, t, w, ln in odd:
        if w < defaults[t][0] - 3:  # 1~3px 차이는 DPI 반올림
            groups.setdefault(w, []).append((n, t, ln))
    shrunk = []
    for w, g in groups.items():  # 라벨과 입력 칸을 같은 폭으로 줄인 묶음(2026-11-20 교정)
        kinds = {t for _, t, _ in g}
        if len(g) >= 3 and LABEL in kinds and kinds & SINGLE:
            shrunk += g
    item('여러 컨트롤을 한 폭으로 줄이지 않음(기본 크기 유지)', [ln for _, _, ln in shrunk],
         ', '.join('%s %d<%d' % (n, size_of(d.prop(n, 'Size')[0])[0], defaults[t][0]) for n, t, _ in shrunk[:8]))
    rest = [x for x in odd if x[0] not in {n for n, _, _ in shrunk}]
    if rest:
        r.append((CHECK, '기본 크기와 다른 새 컨트롤', [x[3] for x in rest],
                  ', '.join('%s %d(기본 %d)' % (n, w, defaults[t][0]) for n, t, w, _ in rest[:8])
                  + '. 지정 화면의 같은 역할 크기가 근거면 --sibling으로 넘긴다'))

    bad, notes = [], []
    kids = {}
    for n, p in d.parent.items():
        dock, vis = d.prop(n, 'Dock')[0], d.prop(n, 'Visible')[0]
        loc, s = point_of(d.prop(n, 'Location')[0]), d.size(n, defaults)
        if d.typ(p) in SKIP_LAYOUT or (dock and not dock.endswith('None')) or vis == 'false' or not loc or not s:
            continue
        kids.setdefault(p, []).append((n, loc[0], loc[1], s[0], s[1]))
    for p, ks in kids.items():
        for i, a in enumerate(ks):
            for b in ks[i + 1:]:
                if (a[0] in new or b[0] in new) and a[1] < b[1] + b[3] and b[1] < a[1] + a[3] \
                        and a[2] < b[2] + b[4] and b[2] < a[2] + a[4]:
                    bad.append(d.prop(b[0], 'Location')[1])
                    notes.append('%s↔%s' % (a[0], b[0]))
    item('같은 부모 안 컨트롤 겹침 없음', bad, ', '.join(notes[:6]))

    bad, notes, dflt = [], [], []
    for n in added:
        t = d.typ(n)
        if DEFAULT_NAME.match(n):
            dflt.append(d.line(n))
            continue
        p = PREFIX.get(t)
        if not p:
            continue
        if p.startswith('rps'):  # rpsSpinQTY, rpsSpinDetailQTY, 공용 rpsSpin
            ok = re.match(r'rps\w*?%s([A-Z0-9_]|$)' % p[3:], n, re.I) is not None
        else:
            ok = any(n.lower().startswith(q.lower()) and len(n) > len(q) and (n[len(q)].isupper() or n[len(q)].isdigit())
                     for q in p.split('|'))
        if not ok:
            bad.append(d.line(n))
            notes.append('%s(%s→%s…)' % (n, t, p.split('|')[0]))
    item('이름 접두어(controls.md#names)', bad, ', '.join(notes[:6]))
    item('디자이너 기본 이름(label17, gridColumn3 …) 없음', dflt)

    for table, st, name in ((REQUIRED, FAIL, '필수 속성 줄(controls.md#designer-blocks)'), (USUAL, CHECK, '블록의 보통 속성 빠짐')):
        bad, notes = [], []
        for n in added:
            miss = [k for k in table.get(d.typ(n), ()) if not re.search(r'this\.%s\.%s\b' % (n, re.escape(k)), raw)]
            if miss:
                bad.append(d.line(n))
                notes.append('%s: %s' % (n, ', '.join(miss)))
        if st == FAIL or bad:
            item(name, bad, '; '.join(notes[:5]), st)

    roles = ROLES | proj_suffixes | {x for s in sibs for x in s.grid_suffixes()} | (o.grid_suffixes() if o else set())
    bad, notes, odd_role = [], [], []
    for g, v in d.main.items():
        sfx = g[3:] if g.startswith('grd') else None
        if sfx is None:
            continue
        if g in added and not (TABLE.match(sfx) or sfx in roles):
            # 그리드 하나인 화면의 목록이면 실패, 여러 그리드면 확인(화면 고유 역할 이름이 있다)
            (bad if len(d.main) == 1 else odd_role).append(d.line(g))
            notes.append('%s: 목록은 grdList, 상세는 grdDetail, 테이블 기준 화면은 grd<테이블>' % g)
        if v != 'gvw' + sfx and (g in added or v in added):
            bad.append(d.line(v))
            notes.append('%s↔%s' % (g, v))
        for c, ln in d.cols.get(v, []):
            if c in added and not DEFAULT_NAME.match(c) and not c.lower().startswith(('col%s_' % sfx).lower()):
                bad.append(ln)
                notes.append('%s(col%s_필드)' % (c, sfx))
    item('그리드 이름 grd<X>/gvw<X>/col<X>_<FIELD>', bad, ', '.join(notes[:6]))
    if odd_role:
        r.append((CHECK, '사용자 화면에 없는 그리드 역할 이름', odd_role, '비교 화면에서 같은 역할의 이름을 찾는다'))

    bad, notes = [], []
    need = {'AppearanceCell.Options.UseFont': 'true', 'AppearanceHeader.Options.UseFont': 'true',
            'AppearanceHeader.Options.UseTextOptions': 'true', 'AppearanceHeader.TextOptions.HAlignment': 'Center',
            'AppearanceHeader.TextOptions.VAlignment': 'Center'}
    for n in added:
        t = d.typ(n)
        if t not in ('GridColumn', 'BandedGridColumn', 'TreeListColumn'):
            continue
        keys = need if t != 'TreeListColumn' else {k: v for k, v in need.items() if 'TextOptions' in k}
        miss = [k.split('.')[-1] for k, v in keys.items() if not (d.prop(n, k)[0] or '').endswith(v)]
        fonts = [ln for k, (v, ln) in d.props.get(n, {}).items() if re.match(r'Appearance(Cell|Header)\.Font$', k)]
        if miss or fonts:
            bad += fonts or [d.line(n)]
            notes.append('%s %s' % (n, '·'.join(miss) + (' Font 지정' if fonts else '')))
    item('열 Appearance(UseFont, 머리글 가운데, Font 없음)', bad, ', '.join(notes[:5]))

    # 사용자 화면: QTY/AMT/UNP/WGT 열 879/885가 rpsSpin, UNIT/ACNT/STS 열 161/175가 rpscbo(DIV/EMP/MAN은 70~77%)
    summ = {c: s for c, s in re.findall(r'this\.(\w+)\.Summary\.AddRange\((.*?)\}\);', raw, re.S)}
    reg = set(re.findall(r'this\.(\w+)', ' '.join(re.findall(r'RepositoryItems\.AddRange\((.*?)\}\);', raw, re.S))))
    att = {v[0].replace('this.', '') for p in d.props.values() for k, v in p.items() if k == 'ColumnEdit'}
    edit_bad, edit_chk, foot_bad, sum_chk, cnt_chk, cnt_bad = [], [], [], [], [], []
    o_summ = {c: s for c, s in re.findall(r'this\.(\w+)\.Summary\.AddRange\((.*?)\}\);', orig, re.S)} if o else {}
    cnt_ref = any(x.has_count for x in sibs + ([o] if o else []))  # 건수는 사용자 뷰의 61%: 비교 화면에 있으면 실패
    for g, v in d.main.items():
        cols = [c for c, _ in d.cols.get(v, []) if c in added and d.prop(c, 'Visible')[0] == 'true']
        for c in cols:
            fld = (d.prop(c, 'FieldName')[0] or '').strip('"')
            ed = d.typ((d.prop(c, 'ColumnEdit')[0] or '').replace('this.', ''))
            for pat, kind, lst in ((r'(QTY|AMT|UNP|WGT)\d*$', 'SpinEdit', edit_bad), (r'(UNIT|ACNT|STS)\d*$', 'LookUp', edit_bad),
                                   (r'(DIV|EMP|MAN)\d*$', 'LookUp', edit_chk)):
                if re.search(pat, fld) and kind not in ed:
                    lst.append((d.line(c), '%s→rps%s' % (c, 'Spin' if kind == 'SpinEdit' else 'cbo')))
            if re.search(r'(QTY|AMT)\d*$', fld) and 'Sum' not in summ.get(c, ''):
                sum_chk.append((d.line(c), c))
        has_sum = any(summ.get(c) for c, _ in d.cols.get(v, []))
        if v in added:
            if has_sum and d.prop(v, 'OptionsView.ShowFooter')[0] != 'true':
                foot_bad.append((d.line(v), v + ' ShowFooter'))
            # 건수는 보통 넣지만 통계·집계 그리드(행이 합계)에는 넣지 않는다: 참조에 있으면 실패, 아니면 확인
            if not any('Count' in summ.get(c, '') for c, _ in d.cols.get(v, [])):
                (foot_bad if cnt_ref else cnt_chk).append(
                    (d.line(v), v + (' 건수(Count) 합계 없음(참조 화면에 있음)' if cnt_ref else '')))
        # 이번에 추가된 건수: 편집 안 되는 가장 앞 열(VisibleIndex)에, 표시는 '건'
        for c, _ in d.cols.get(v, []):
            s = summ.get(c, '')
            if 'Count' not in s or (o is not None and 'Count' in o_summ.get(c, '')):
                continue
            target = first_locked(d, v)
            m = re.search(r'Count\s*,\s*"[^"]*"\s*,\s*"([^"]*)"', s)
            if target and c != target:
                cnt_bad.append((d.line(c), '%s→%s(편집 안 되는 첫 열)' % (c, target)))
            if not m or '건' not in m.group(1):
                cnt_bad.append((d.line(c), '%s 표시 "%s"(…건)' % (c, m.group(1) if m else '')))
    for rp in added:
        if d.typ(rp).startswith(('RepositoryItem',) + ((CTRL_PREFIX + 'rps',) if CTRL_PREFIX else ())) and (rp not in reg or rp not in att):
            edit_bad.append((d.line(rp), '%s %s' % (rp, '등록 안 됨' if rp not in reg else 'ColumnEdit 연결 없음')))
    item('숫자 열 rpsSpin·코드 열 rpscbo, Repository 등록·연결', [x[0] for x in edit_bad],
         ', '.join(x[1] for x in edit_bad[:6]))
    if edit_chk:
        r.append((CHECK, '코드 열(DIV/EMP/MAN)에 rpscbo 없음', [x[0] for x in edit_chk], ', '.join(x[1] for x in edit_chk[:6])))
    item('그리드 푸터(합계 있는 뷰 ShowFooter, 참조 화면의 건수)', [x[0] for x in foot_bad], ', '.join(x[1] for x in foot_bad[:4]))
    item('그리드 건수 위치·표시(편집 안 되는 첫 열, …건)', [x[0] for x in cnt_bad], ', '.join(x[1] for x in cnt_bad[:4]))
    if cnt_chk:
        r.append((CHECK, '그리드 건수 합계 없음', [x[0] for x in cnt_chk], ', '.join(x[1] for x in cnt_chk[:4])
                  + ': 행이 레코드인 목록이면 편집 안 되는 첫 열에 Count "{0:#,##0}건". 통계·집계 그리드면 넣지 않음'))
    if sum_chk:
        r.append((CHECK, '수량·금액 열 Sum 합계 없음', [x[0] for x in sum_chk], ', '.join(x[1] for x in sum_chk[:6])
                  + '. 사용자 화면은 QTY 69%·AMT 85%에 Sum'))

    old_ev = {e for e, _ in o.events} if o else set()
    item('InitializeComponent 안 새 이벤트 구독 없음(생성자에서 구독)', [ln for e, ln in d.events if e not in old_ev],
         ', '.join(e for e, _ in d.events if e not in old_ev)[:200])

    if o:
        for n in d.types:
            if n not in o.types:
                continue
            a, b = o.props.get(n, {}), d.props.get(n, {})
            diff = [k for k in sorted(set(a) | set(b)) if a.get(k, (None,))[0] != b.get(k, (None,))[0]
                    and k not in ('TabIndex',)]
            if diff:
                r.append((CHECK, '기존 컨트롤 속성 변경: ' + n, [b[k][1] for k in diff if k in b],
                          ', '.join(('-' if k not in b else '+' if k not in a else '~') + k for k in diff[:8])
                          + '. 요청한 변경인지 확인'))
        gone = [n for n in o.types if n not in d.types]
        if gone:
            r.append((CHECK, '삭제된 컨트롤', [], ', '.join(gone[:10])))
    return r


CS_RULES = [
    (FAIL, 'PostEditor/CloseEditor/UpdateCurrentRow 추가 없음', r'\.(PostEditor|CloseEditor|UpdateCurrentRow)\(\)'),
    (FAIL, '툴바 권한 P_* 대입 없음(권한은 프로그램 등록 테이블)',
     r'\bP_(Add|Edit|Save|Delete|Copy|Print|Clear|Excel)\s*=(?!=)'),
    (FAIL, 'ColumnFilterInfo/FilterInfo 필터 없음', r'ColumnFilterInfo|\.FilterInfo\s*=(?!=)'),
    (FAIL, '포커스 강제(FocusedRowHandle = GetRowHandle/숫자) 없음',
     r'\.FocusedRowHandle\s*=(?!=)\s*(\w+\.GetRowHandle\(|-?\d+\s*;)'),
    (FAIL, '열 MinWidth 코드 대입 없음', r'\.MinWidth\s*=(?!=)'),
    (FAIL, '그룹 제목(grp….Text) 코드 대입 없음', r'\bgrp\w*\.Text\s*=(?!=)'),
    (FAIL, 'MessageBox.Show 없음(Msg 계열)', r'\bMessageBox\.Show\('),
    (FAIL, '람다·delegate 이벤트 구독 없음', r'\+=\s*(\([^)]*\)|\w+)\s*=>|\+=\s*delegate\b'),
    (CHECK, 'FocusedRowHandle/FocusedColumn 대입 추가', r'\.Focused(RowHandle|Column)\s*=(?!=)'),
    (CHECK, 'BestFitColumns 호출 추가', r'\.BestFitColumns\('),
]


def no_brace(lines):
    out = []
    for i, l in enumerate(lines):
        s = re.sub(r'//.*', '', l).strip()
        m = re.match(r'(else\s+if|if|for|foreach|while)\s*\((.*)\)\s*(.*)$', s)
        if m and m.group(2).count('(') == m.group(2).count(')'):
            tail = m.group(3)
            nxt = next((x.strip() for x in lines[i + 1:] if x.strip()), '')
            # 같은 줄의 한 문장(`if (...) return;`)은 사용자 방식(기준 프로젝트 화면 29/30). 다음 줄 본문만 중괄호 필수
            if not tail and not nxt.startswith('{'):
                out.append(i)
        elif s == 'else' and not next((x.strip() for x in lines[i + 1:] if x.strip()), '').startswith(('{', 'if')):
            out.append(i)
    return out


def check_cs(raw, orig):
    lines = raw.split('\n')
    old = set(x.strip() for x in orig.split('\n')) if orig is not None else set()
    added = [i for i, l in enumerate(lines) if l.strip() not in old and not l.strip().startswith('//')]
    r = []
    for st, name, pat in CS_RULES:
        if pat is None:
            hit = [i + 1 for i in no_brace(lines) if i in set(added)]
        else:
            hit = [i + 1 for i in added if re.search(pat, lines[i])]
        r.append((st if hit else PASS, name, hit, ''))
    return [x for x in r if not (x[0] == PASS and x[1].endswith('추가'))]


def fmt_lines(ls, limit=12):
    s = ', '.join(str(x) for x in ls[:limit])
    return ('줄 ' + s + (' 외 %d줄' % (len(ls) - limit) if len(ls) > limit else '')) if ls else ''


def report(results):
    out = []
    for st, name, ls, note in results:
        tail = ' / '.join(x for x in (fmt_lines(ls), note) if x)
        out.append('[%s] %s%s' % (st, name, (': ' + tail) if tail else ''))
    judged = [x for x in results if x[0] in (PASS, FAIL)]
    ok = sum(1 for x in judged if x[0] == PASS)
    verdict = 'PASS' if ok == len(judged) else 'FAIL'
    out.append('ACE-CHECK: %s %d/%d' % (verdict, ok, len(judged)))
    return out, verdict == 'PASS'


def run(path, original=None, project=None, siblings=(), orig_text=None):
    raw = read_text(path)
    orig = read_text(original) if original else orig_text
    if not path.lower().endswith('.designer.cs'):
        return check_cs(raw, orig), 'cs'
    root = project or find_project(path)
    found, suffixes = project_info(root, path)
    defaults = dict(DEFAULTS)
    defaults.update(found)
    sibs = [Designer(read_text(s)) for s in siblings]
    return check_designer(raw, orig, sibs, defaults, suffixes), 'designer(기본 크기: %s)' % (
        '소스' if found else '내장 표')


def main(argv=None):
    ap = argparse.ArgumentParser(description='ACE csharp 기계 점검')
    ap.add_argument('file')
    ap.add_argument('--original')
    ap.add_argument('--project')
    ap.add_argument('--sibling', nargs='*', default=[])
    a = ap.parse_args(argv)
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')
    try:
        results, mode = run(a.file, a.original, a.project, a.sibling)
    except (OSError, ValueError) as e:
        print('ACE-CHECK: ERROR %s' % e)
        return 2
    lines, ok = report(results)
    print('대상: %s (%s%s)' % (a.file, mode, ', 원본 대조' if a.original else ''))
    print('\n'.join(lines))
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
