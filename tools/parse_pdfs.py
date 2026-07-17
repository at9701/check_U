# -*- coding: utf-8 -*-
"""解析食藥署中聯油脂案三份 PDF 清單 → JSON"""
import pdfplumber, json, re, sys, collections, os

SRC = 'sources/'
OUT = 'tools/parsed/'

CITY_MAP = {
    '基隆':'基隆市','台北':'臺北市','臺北':'臺北市','新北':'新北市','桃園':'桃園市',
    '台中':'臺中市','臺中':'臺中市','台南':'臺南市','臺南':'臺南市','高雄':'高雄市',
    '苗栗':'苗栗縣','彰化':'彰化縣','南投':'南投縣','雲林':'雲林縣','屏東':'屏東縣',
    '宜蘭':'宜蘭縣','花蓮':'花蓮縣','台東':'臺東縣','臺東':'臺東縣','澎湖':'澎湖縣',
    '金門':'金門縣','連江':'連江縣',
    '基隆市':'基隆市','台北市':'臺北市','臺北市':'臺北市','新北市':'新北市','桃園市':'桃園市',
    '新竹市':'新竹市','新竹縣':'新竹縣','苗栗縣':'苗栗縣','台中市':'臺中市','臺中市':'臺中市',
    '彰化縣':'彰化縣','南投縣':'南投縣','雲林縣':'雲林縣','嘉義市':'嘉義市','嘉義縣':'嘉義縣',
    '台南市':'臺南市','臺南市':'臺南市','高雄市':'高雄市','屏東縣':'屏東縣','宜蘭縣':'宜蘭縣',
    '花蓮縣':'花蓮縣','台東縣':'臺東縣','臺東縣':'臺東縣','金門縣':'金門縣','澎湖縣':'澎湖縣',
    '連江縣':'連江縣',
}
def norm_city(c):
    c = re.sub(r'\s+', '', c or '')
    return CITY_MAP.get(c, c)

def clean(s):
    if s is None: return ''
    return re.sub(r'\s+', ' ', str(s).replace('\n', ' ')).strip()

def parse_simple(fn, cols, has_seq):
    """通用：每頁一張表，欄位 [序號?] 縣市 業者 品項 批號 有效日期"""
    rows, bad = [], []
    with pdfplumber.open(SRC + fn) as pdf:
        for pi, page in enumerate(pdf.pages):
            t = page.extract_table()
            if not t:
                bad.append(('no-table', pi + 1)); continue
            for r in t:
                cells = [clean(x) for x in r]
                if not any(cells): continue
                if '縣市' in cells and '業者' in cells: continue  # header
                if has_seq:
                    if len(cells) < 6: bad.append((pi + 1, cells)); continue
                    seq, city, vendor, item, batch, exp = cells[:6]
                    if not re.match(r'^\d+$', seq): bad.append((pi + 1, cells)); continue
                else:
                    if len(cells) < 5: bad.append((pi + 1, cells)); continue
                    city, vendor, item, batch, exp = cells[:5]
                if not vendor: bad.append((pi + 1, cells)); continue
                rows.append({'city': norm_city(city), 'vendor': vendor,
                             'item': item, 'batch': batch, 'exp': exp, 'page': pi + 1})
    return rows, bad

def parse_taishan():
    rows, bad = [], []
    fn = '1150716_泰山下游廠商產品名單_官網公告.pdf'
    with pdfplumber.open(SRC + fn) as pdf:
        for pi, page in enumerate(pdf.pages):
            t = page.extract_table()
            if not t: continue
            for r in t:
                cells = [clean(x) for x in r]
                if not any(cells): continue
                if '中聯批次' in cells: continue
                # 中聯批次 業者序號 縣市 業者 品項 批號 有效日期 產品序號 產品 產品效期 產品毛重 產品淨重
                if len(cells) < 10: bad.append((pi + 1, cells)); continue
                rows.append({'srcBatch': cells[0], 'vseq': cells[1], 'city': norm_city(cells[2]),
                             'vendor': cells[3], 'oil': cells[4], 'oilBatch': cells[5],
                             'oilExp': cells[6], 'pseq': cells[7], 'product': cells[8],
                             'pExp': cells[9],
                             'gross': cells[10] if len(cells) > 10 else '',
                             'net': cells[11] if len(cells) > 11 else ''})
    return rows, bad

def main():
    os.makedirs(OUT, exist_ok=True)
    fumao, bad1 = parse_simple(
        '(人名遮蔽_官網資料)1150710食藥署_食安處-29批中聯油脂股份有限公司下游流向_福懋_0406-0623.pdf',
        6, True)
    l46, bad2 = parse_simple('115年4到6月下游業者清單-20260711.pdf', 5, False)
    ts, bad3 = parse_taishan()

    for name, rows, bad in [('fumao', fumao, bad1), ('list46', l46, bad2), ('taishan', ts, bad3)]:
        json.dump(rows, open(OUT + name + '.json', 'w'), ensure_ascii=False)
        print(f'{name}: {len(rows)} rows, {len(bad)} skipped')
        for b in bad[:5]: print('   skipped:', b)
        cities = collections.Counter(r['city'] for r in rows)
        weird = {c: n for c, n in cities.items() if c not in set(CITY_MAP.values())}
        if weird: print('   非標準縣市:', weird)

    # 檢查 list46 / fumao 去重後規模
    for name, rows in [('fumao', fumao), ('list46', l46)]:
        uniq = {(r['city'], r['vendor'], r['item'], r['batch'], r['exp']) for r in rows}
        vend = {(r['city'], r['vendor']) for r in rows}
        print(f'{name}: 去重後 {len(uniq)} 筆 / {len(vend)} 家業者')
    tsv = {(r['city'], r['vendor']) for r in ts}
    print(f'taishan: {len(ts)} 項產品 / {len(tsv)} 家業者 / 中聯批次 {sorted({r["srcBatch"] for r in ts})}')

if __name__ == '__main__':
    main()
