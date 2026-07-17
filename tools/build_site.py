# -*- coding: utf-8 -*-
"""合併官方清單 → 產出 data/products.js、data/vendors.js、index.html"""
import json, re, collections, os

SP = 'tools/parsed/'
REPO = './'

# ---------- 載入 ----------
old = open('archive/index_1150716版.html', encoding='utf-8').read()
DATA = json.loads(re.search(r'const DATA = (\[.*?\]);', old, re.S).group(1))
OLD_VDATA = json.loads(re.search(r'const VDATA = (\[.*?\]);', old, re.S).group(1))
OLD_VCITY = json.loads(re.search(r'const VCITY = (\[.*?\]);', old, re.S).group(1))
fumao = json.load(open(SP + 'fumao.json'))
l46 = json.load(open(SP + 'list46.json'))
ts = json.load(open(SP + 'taishan.json'))

# ---------- 縣市第二階段修正 ----------
CITY_FIX = {'彰化市':'彰化縣','宜蘭市':'宜蘭縣','南投市':'南投縣','台東市':'臺東縣',
            '花蓮市':'花蓮縣','屏東市':'屏東縣','桃園縣':'桃園市','宜縣市':'宜蘭縣',
            'SOUTHKOREA':'外銷','':'未註明'}
def fixcity(c): return CITY_FIX.get(c, c)
for rows in (fumao, l46, ts):
    for r in rows: r['city'] = fixcity(r['city'])

# 福懋 p24 解析失敗列補回（原始格式跑版）
fumao.append({'city':'臺中市','vendor':'福懋油脂股份有限公司','item':'益康烹調油(調合油)18L',
              'batch':'20270424000403','exp':'2027/04/24','page':24})

# ---------- 泰山修正 ----------
def zh_despace(s): return re.sub(r'(?<=[㐀-鿿）)])\s+(?=[㐀-鿿（(])', '', s)
for r in ts:
    r['vendor'] = zh_despace(r['vendor'])
    r['product'] = zh_despace(r['product'])
# 漏列補回：鬍鬚張 #22 蝦醬（PDF跨頁首列）
ts.append({'srcBatch':'318-1150517','vseq':'4','city':'新北市','vendor':'鬍鬚張',
           'oil':'黃金優選沙拉油18L','oilBatch':'20270520','oilExp':'20270520',
           'pseq':'22','product':'蝦醬','pExp':'2027.06.22','gross':'','net':''})
# 換行造成的效期亂碼，依原始PDF逐筆修正
PEXP_FIX = {
 ('金福華','沙茶醬'): '2029.04.09、2029.04.12',
 ('金福華','豆瓣醬'): '2027.04.12、2027.04.13、2027.04.14',
 ('金福華','麻辣鴨血'): '2027.02.27、2027.04.07、2027.05.20、2027.05.21',
 ('松鼎','黃金調和油'): '2.8L/桶*6：2028.04.13；2L/桶*6：2028.04.10；0.6L/桶*12：2028.04.10；1.8L/桶*6：2028.04.10',
}
SUWEI_EXP = '115.07.10、07.13、07.14、07.15、07.16、07.17、07.20、07.21'
for r in ts:
    k = (r['vendor'], r['product'])
    if k in PEXP_FIX: r['pExp'] = PEXP_FIX[k]
    elif r['vendor'] == '素味食品股份有限公司': r['pExp'] = SUWEI_EXP
    else: r['pExp'] = re.sub(r'\s+', '', r['pExp']) or '—'
ts.sort(key=lambda r: (int(r['vseq']), int(r['pseq'])))
assert len(ts) == 42, len(ts)

# ---------- 業者合併 ----------
# VCITY 擴充
VCITY = OLD_VCITY + ['新竹', '嘉義', '未註明', '外銷']
CIDX = {c: i for i, c in enumerate(VCITY)}
def cidx(c):
    if c not in CIDX:
        CIDX[c] = len(VCITY); VCITY.append(c)
    return CIDX[c]

def nkey(s): return re.sub(r'[\s　]+', '', s)

vendors = {}   # (namekey, cityidx) -> {'n':display, 'ci':ci, 'rows':{(item,batch,exp):[mask,count]}}
def add_row(name, ci, item, batch, exp, mask, count=1):
    k = (nkey(name), ci)
    v = vendors.setdefault(k, {'n': name, 'ci': ci, 'rows': collections.OrderedDict()})
    rk = (nkey(item), str(batch).strip(), str(exp).strip())
    if rk in v['rows']:
        v['rows'][rk][0] |= mask
        v['rows'][rk][1] = max(v['rows'][rk][1], count)
    else:
        v['rows'][rk] = [mask, count, (item.strip(), str(batch).strip(), str(exp).strip())]

# 來源1：既有 1150716 整併清單（1,322家）
orig_keys = set()
for seq, ci, name, rows in OLD_VDATA:
    orig_keys.add((nkey(name), ci))
    for item, batch, exp in rows:
        add_row(name, ci, item, batch, exp, 1)

# 來源2：福懋29批流向；來源4：4–6月清單（原始清單重複列＝多次進貨 → 次數）
def add_list(rows, mask):
    cnt = collections.Counter((r['city'], nkey(r['vendor']), nkey(r['item']),
                               r['batch'].strip(), r['exp'].strip()) for r in rows)
    seen = set()
    for r in rows:
        key = (r['city'], nkey(r['vendor']), nkey(r['item']), r['batch'].strip(), r['exp'].strip())
        if key in seen: continue
        seen.add(key)
        add_row(r['vendor'], cidx(r['city']), r['item'], r['batch'], r['exp'], mask, cnt[key])

add_list(fumao, 2)
add_list(l46, 4)

# 排序：縣市 → 業者名
VOUT = []
for (nk2, ci), v in vendors.items():
    rows = [[t[2][0], t[2][1], t[2][2], t[0], t[1]] for t in v['rows'].values()]
    VOUT.append([v['n'], ci, rows])
VOUT.sort(key=lambda v: (v[1], v[0]))

# ---------- 統計 ----------
total_v = len(VOUT)
total_r = sum(len(v[2]) for v in VOUT)
def src_vcount(mask):
    return sum(1 for v in VOUT if any(r[3] & mask for r in v[2]))
fm_v = src_vcount(2); l46_v = src_vcount(4)
fm_r = sum(1 for v in VOUT for r in v[2] if r[3] & 2)
l46_r = sum(1 for v in VOUT for r in v[2] if r[3] & 4)
new_v = sum(1 for v in VOUT if (nkey(v[0]), v[1]) not in orig_keys)
stats = dict(VSTAT_TOTAL=f'{total_v:,}', VSTAT_ROWS=f'{total_r:,}',
             FM_V=str(fm_v), FM_R=f'{fm_r:,}', L46_V=str(l46_v), L46_R=f'{l46_r:,}',
             NEWV_COUNT=str(new_v))
print('統計：', stats)

# ---------- 輸出 ----------
os.makedirs(REPO + 'data', exist_ok=True)
j = lambda o: json.dumps(o, ensure_ascii=False, separators=(',', ':'))

TSDATA = [[r['srcBatch'], r['city'], r['vendor'], r['oil'], r['oilBatch'], r['pseq'], r['product'], r['pExp']] for r in ts]
with open(REPO + 'data/products.js', 'w', encoding='utf-8') as f:
    f.write('// 中聯油脂案：下架產品資料（由 tools/ 腳本產生，勿手動編輯）\n')
    f.write('// DATA：食藥署115.07.09版440項（第1批315-1150404衍生）\n')
    f.write('const DATA = ' + j(DATA) + ';\n')
    f.write('// TSDATA：泰山官網115.07.16下游廠商產品名單42項\n')
    f.write('// 格式：[中聯批次, 縣市, 業者, 使用油品, 油品批號, 產品序號, 產品, 產品效期]\n')
    f.write('const TSDATA = ' + j(TSDATA) + ';\n')

with open(REPO + 'data/vendors.js', 'w', encoding='utf-8') as f:
    f.write('// 中聯油脂案：下游業者合併資料（由 tools/ 腳本產生，勿手動編輯）\n')
    f.write('// 來源 bitmask：1=食藥署1150716整併清單(7批,1322家) 2=福懋29批下游流向(1150710) 4=115年4-6月下游業者清單(20260711)\n')
    f.write('// VDATA 格式：[業者名, 縣市索引, [[品項, 批號, 有效日期, 來源bitmask, 同來源重複次數], ...]]\n')
    f.write('const VCITY = ' + j(VCITY) + ';\n')
    f.write('const VDATA = ' + j(VOUT) + ';\n')

html = open('tools/index.template.html', encoding='utf-8').read()
for k, vv in stats.items():
    html = html.replace('@@' + k + '@@', vv)
assert '@@' not in html, '尚有未填入的佔位符'
with open(REPO + 'index.html', 'w', encoding='utf-8') as f:
    f.write(html)
print('已寫出 index.html', len(html), 'bytes；products.js / vendors.js 完成')
print('data sizes:', os.path.getsize(REPO+'data/products.js'), os.path.getsize(REPO+'data/vendors.js'))
