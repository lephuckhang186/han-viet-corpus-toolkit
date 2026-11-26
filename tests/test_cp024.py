import tempfile
import unittest
import json
import os
import csv
import zipfile
from pathlib import Path
from unittest.mock import patch

import tests  # noqa: F401
from hanviet.alignment.cp024 import discover_sources, sections, run_cp024, quality, export_draft_preview, aggregate_work_json
from hanviet.common.io import read_json, json_bytes


class CP024Tests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='cp024 space ')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.text = self.root / 'data' / 'CP024' / '03_text_sach'
        for kind in ('han', 'viet'):
            (self.text / kind).mkdir(parents=True)

    def pair(self, number, han='甲。\n乙。', viet='Một câu.\nHai câu.', bom=False):
        for kind, content in (('han', han), ('viet', viet)):
            (self.text / kind / f'{number}.{kind}.txt').write_text(content, encoding='utf-8-sig' if bom else 'utf-8')

    def test_inventory(self):
        self.pair('010'); self.pair('2', bom=True); self.pair('005')
        rows, errors = discover_sources(self.text)
        self.assertFalse(errors)
        self.assertEqual([r['file_id'] for r in rows], [2, 5, 10])
        self.assertTrue(all(r['status'] == 'ok' for r in rows))
        (self.text / 'han' / '5.han.txt').write_text('甲', encoding='utf-8')
        (self.text / 'viet' / '010.viet.txt').unlink()
        (self.text / 'han' / '2.han.txt').write_text('', encoding='utf-8')
        (self.text / 'viet' / '42.viet.txt').write_text('A', encoding='utf-8')
        (self.text / 'han' / 'bad.txt').write_text('A', encoding='utf-8')
        rows, errors = discover_sources(self.text)
        self.assertTrue(errors)
        self.assertIn('rỗng', rows[0]['status'])
        self.assertIn('trùng', rows[1]['status'])
        self.assertIn('thiếu', rows[2]['status'])
        self.assertIn('thiếu', rows[3]['status'])

    def test_sections(self):
        self.assertEqual(len(sections(5, 5, 2)), 3)
        with self.assertRaises(ValueError): sections(5, 6, 2)
        good = {1: {'han': [1, 2], 'nghia': [1, 3]}, 2: {'han': [3, 5], 'nghia': [4, 6]}}
        self.assertEqual(len(sections(5, 6, manual=good)), 2)
        for bad in ({1: {'han':[1, 2], 'nghia':[1, 3]}, 2: {'han':[2, 5], 'nghia':[4, 6]}},
                    {1: {'han':[1, 4], 'nghia':[1, 6]}},
                    {1: {'han':[1, 6], 'nghia':[1, 6]}}):
            with self.assertRaises(ValueError): sections(5, 6, manual=bad)
        self.assertEqual(sections(5, 6, whole=True)[0]['ranges']['nghia'], [1, 6])

    def test_workflow_with_clc_cache_and_review(self):
        self.pair('005')
        kwargs = dict(project=self.root, file_number=5, lines_per_section=10)
        with patch('hanviet.alignment.backends.clc_aligner.request_clc') as api, patch('hanviet.alignment.notebook_helpers.show_alignment'):
            run_cp024(**kwargs)
            self.assertFalse((self.root / 'san_pham').exists())
            api.assert_not_called()
            payload = {'is_success': True, 'code':'000000', 'data': {'result': [
                {'han_start':0,'han_end':1,'vi_start':0,'vi_end':1,'han_text':'甲。乙。','vietnamese_text':'Một câu. Hai câu.','score':0.8}]}}
            api.return_value = payload
            with self.assertRaises(ValueError): run_cp024(**kwargs, mode='nhap')
            result = run_cp024(**kwargs, mode='nhap', confirmed=True)
            draft = result['results']['bai0005_muc0001']
            self.assertEqual(len(quality(draft)['multi_viet']), 1)
            self.assertEqual(api.call_count, 1)
            run_cp024(**kwargs, mode='nhap', confirmed=True)
            self.assertEqual(api.call_count, 1)
            audit = self.root / 'san_pham' / 'TV04' / 'CP024' / '05_quan_ly' / 'dong_hang' / 'TV04' / 'bai0005_muc0001'
            preview = audit / 'ban_nhap'
            with (preview / 'CP024_bai0005_muc0001_ban_nhap.tsv').open(encoding='utf-8-sig', newline='') as f:
                draft_rows = list(csv.reader(f, delimiter='\t'))
            self.assertEqual(draft_rows, [['Hán', 'Dịch âm', 'Dịch nghĩa', 'Dịch thơ'],
                                          ['甲。 乙。', '', 'Một câu. Hai câu.', '']])
            with zipfile.ZipFile(preview / 'CP024_bai0005_muc0001_ban_nhap.xlsx') as workbook:
                strings = workbook.read('xl/sharedStrings.xml').decode('utf-8')
                self.assertIn('Một câu. Hai câu.', strings)
                self.assertIn('甲。 乙。', strings)
            template = read_json(audit / 'review_template.json')
            (audit / 'review.json').write_bytes(json_bytes(template))
            with self.assertRaises(ValueError): run_cp024(**kwargs, mode='xuat')
            template['approved'] = True
            (audit / 'review.json').write_bytes(json_bytes(template))
            run_cp024(**kwargs, mode='xuat')
            self.assertEqual(api.call_count, 1)
            with self.assertRaises(ValueError): run_cp024(**kwargs, mode='nhap', confirmed=True)
            exported = self.root / 'san_pham' / 'TV04' / 'CP024' / '04_dong_hang' / 'bai0005_muc0001'
            self.assertTrue((exported / 'CP024_bai0005_muc0001_parallel.xlsx').is_file())
            self.assertEqual(len((exported / 'CP024_bai0005_muc0001_parallel.tsv').read_text(encoding='utf-8').strip('\n').split('\t')), 4)
            notebook = json.loads((Path(__file__).resolve().parents[1] / 'notebooks' / 'dong_hang.ipynb').read_text(encoding='utf-8'))
            merge = next(c for c in notebook['cells'] if c.get('id') == 'gop_bang_dong_hang')
            code = ''.join(merge['source']).replace('TAC_PHAM_CHON = ["CPO_11", "CPO_12"]', 'TAC_PHAM_CHON = ["CP024"]')
            (self.root / 'ten_file.py').write_text("MA_DE_TAI = 'CV06'\n", encoding='utf-8')
            previous = Path.cwd()
            try:
                os.chdir(self.root)
                exec(compile(code, '<merge cell>', 'exec'), {})
            finally:
                os.chdir(previous)
            merged = self.root / 'san_pham' / 'TV04' / '04_dong_hang' / 'TV04_CP024_parallel.csv'
            self.assertTrue(merged.is_file())
            (self.text / 'han' / '005.han.txt').write_text('改。', encoding='utf-8')
            with self.assertRaises(ValueError): run_cp024(**kwargs, mode='xuat')

    def test_empty_clc_is_failure(self):
        self.pair('1')
        with patch('hanviet.alignment.backends.clc_aligner.request_clc', return_value={'is_success':True,'code':'000000','data':{'result':[]}}):
            with self.assertRaises(RuntimeError):
                run_cp024(self.root, file_number=1, mode='nhap', confirmed=True)

    def test_backend_cache_and_api_error(self):
        from hanviet.alignment.backends.clc_aligner import align_clc
        han = [{'id': 'h', 'text': '甲。'}]
        viet = [{'id': 'v', 'text': 'Một.'}]
        payload = {'is_success': True, 'code': '000000', 'data': {'result': [
            {'han_start': 0, 'han_end': 0, 'vi_start': 0, 'vi_end': 0,
             'han_text': '甲。', 'vietnamese_text': 'Một.'}]}}
        with patch('hanviet.alignment.backends.clc_aligner.request_clc', return_value=payload) as api:
            cache = self.root / 'cache.json'
            self.assertEqual(align_clc(han, viet, response_path=cache), align_clc(han, viet, response_path=cache))
            self.assertEqual(api.call_count, 1)
        self.pair('1')
        with patch('hanviet.alignment.backends.clc_aligner.request_clc', side_effect=RuntimeError('API error')):
            with self.assertRaisesRegex(RuntimeError, 'API error'):
                run_cp024(self.root, file_number=1, mode='nhap', confirmed=True)

    def test_preview_includes_unmatched_and_refuses_overwrite(self):
        units = {'han': [{'id': 'h1', 'text': '甲。'}, {'id': 'h2', 'text': '乙。'}],
                 'nghia': [{'id': 'v1', 'text': 'Một.'}, {'id': 'v2', 'text': 'Hai.'}],
                 'am': [], 'tho': []}
        draft = {'work': 'w', 'fingerprint': 'fp', 'links': {'am': [], 'tho': [],
                 'nghia': [{'han_ids': ['h1'], 'nghia_ids': ['v1']}]}}
        files = export_draft_preview(self.root, 'bai0001_muc0001', draft, units, 'w', 'fp')
        with files[0].open(encoding='utf-8-sig', newline='') as f:
            rows = list(csv.reader(f, delimiter='\t'))
        self.assertEqual(rows[1:], [['甲。', '', 'Một.', ''], ['乙。', '', '', ''], ['', '', 'Hai.', '']])
        files[0].write_text('changed', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            export_draft_preview(self.root, 'bai0001_muc0001', draft, units, 'w', 'fp')

    def test_full_file_request_over_ten_lines_is_rejected(self):
        self.pair('005', han='\n'.join(f'甲{i}。' for i in range(12)),
                  viet='\n'.join(f'Câu {i}.' for i in range(12)))
        legacy = self.root / 'san_pham' / 'TV04' / 'CP024' / '05_quan_ly' / 'dong_hang' / 'TV04' / 'bai0005' / 'alignment_plan.json'
        legacy.parent.mkdir(parents=True)
        legacy.write_text('{"existing": true}', encoding='utf-8')
        with patch('hanviet.alignment.backends.clc_aligner.request_clc') as api:
            with self.assertRaisesRegex(ValueError, 'tối đa 10 dòng'):
                run_cp024(self.root, mode='nhap', file_number=5, confirmed=True,
                          whole_files=None, section_number=None)
            api.assert_not_called()
        self.assertEqual(read_json(legacy), {'existing': True})
        plan = read_json(legacy.parent / 'alignment_plan_toan_file.json')
        self.assertEqual(plan['sections'][0]['ranges'], {'han': [1, 12], 'nghia': [1, 12]})
        self.assertEqual(plan['sections'][0]['section'], 'muc0000')

    def test_all_lines_processed_in_requests_of_at_most_ten(self):
        self.pair('005', han='\n'.join(f'甲{i}。乙{i}。' for i in range(23)),
                  viet='\n'.join(f'Một {i}. Hai {i}.' for i in range(23)))
        batches = []
        def response(body):
            han, viet = body['han'].splitlines(), body['vi'].splitlines()
            batches.append((len(han), len(viet)))
            return {'is_success': True, 'code': '000000', 'data': {'result': [
                {'han_start': i, 'han_end': i, 'vi_start': i, 'vi_end': i,
                 'han_text': h, 'vietnamese_text': v}
                for i, (h, v) in enumerate(zip(han, viet))]}}
        with patch('hanviet.alignment.backends.clc_aligner.request_clc', side_effect=response), patch('hanviet.alignment.notebook_helpers.show_alignment'):
            result = run_cp024(self.root, mode='nhap', file_number=5, confirmed=True)
        self.assertEqual(batches, [(10, 10), (10, 10), (3, 3)])
        self.assertEqual(len(result['results']), 3)
        self.assertEqual(sum(len(r['units']['han']) for r in result['results'].values()), 46)
        self.assertEqual(sum(len(r['units']['nghia']) for r in result['results'].values()), 46)
        bundle_path = aggregate_work_json(self.root, 5)
        bundle = read_json(bundle_path)
        self.assertEqual([s['section'] for s in bundle['sections']], ['muc0001', 'muc0002', 'muc0003'])
        self.assertEqual(bundle['section_count'], 3)
        self.assertIn('clc_request.json', bundle['sections'][0]['files'])
        self.assertIn('clc_response.json', bundle['sections'][0]['files'])
        self.assertIn('draft.json', bundle['sections'][0]['files'])
        self.assertIn('review_template.json', bundle['sections'][0]['files'])
        self.assertEqual(aggregate_work_json(self.root, 5), bundle_path)
        draft_dir = bundle_path.parent.parent / 'bai0005_muc0002'
        (draft_dir / 'review.json').write_bytes(json_bytes({'approved': False, 'note': 'test'}))
        new_path = aggregate_work_json(self.root, 5)
        self.assertNotEqual(new_path, bundle_path)
        self.assertTrue(bundle_path.exists())
        (draft_dir / 'draft.json').unlink()
        with self.assertRaises(FileNotFoundError):
            aggregate_work_json(self.root, 5)

    def test_clc_response_can_split_sentences_within_input_lines(self):
        self.pair('005', han='甲。乙。', viet='Một. Hai.')
        payload = {'is_success': True, 'code': '000000', 'data': {'result': [
            {'han_start': 0, 'han_end': 0, 'vi_start': 0, 'vi_end': 0,
             'han_text': '甲。', 'vietnamese_text': 'Một.'},
            {'han_start': 1, 'han_end': 1, 'vi_start': 1, 'vi_end': 1,
             'han_text': '乙。', 'vietnamese_text': 'Hai.'}]}}
        with patch('hanviet.alignment.backends.clc_aligner.request_clc', return_value=payload) as api, patch('hanviet.alignment.notebook_helpers.show_alignment'):
            result = run_cp024(self.root, mode='nhap', file_number=5, confirmed=True)
        self.assertEqual(len(api.call_args.args[0]['han'].splitlines()), 1)
        links = result['results']['bai0005_muc0001']['links']['nghia']
        self.assertEqual(len(links), 2)
        self.assertTrue(all(len(link['han_ids']) == len(link['nghia_ids']) == 1 for link in links))

    def test_clc_can_match_omitted_terminal_quotes_without_losing_source_text(self):
        from hanviet.alignment.backends.clc_aligner import clc_response, CLCTextMismatch
        han = [{'id': 'h', 'text': '曰：「甲。」'}]
        viet = [{'id': 'v', 'text': 'Nói: “Một.”'}]
        row = {'han_start': 0, 'han_end': 0, 'vi_start': 0, 'vi_end': 0,
               'han_text': '曰：「甲。', 'vietnamese_text': 'Nói: “Một.'}
        payload = {'is_success': True, 'code': '000000', 'data': {'result': [row]}}
        with self.assertRaises(CLCTextMismatch):
            clc_response(payload, han, viet)
        links = clc_response(payload, han, viet, allow_terminal_quote_omission=True)
        self.assertEqual(links[0]['han_ids'], ['h'])
        self.assertEqual(han[0]['text'], '曰：「甲。」')
        row['han_text'] = '曰：「。'
        with self.assertRaises(CLCTextMismatch):
            clc_response(payload, han, viet, allow_terminal_quote_omission=True)

    def test_clc_shifted_and_standalone_closing_quotes(self):
        from hanviet.alignment.backends.clc_aligner import clc_response
        han = [{'id': 'h1', 'text': '曰：「甲。」'}, {'id': 'h2', 'text': '乙。'}]
        viet = [{'id': 'v1', 'text': 'Nói: “Một.”'}, {'id': 'v2', 'text': 'Hai.'}]
        def row(h, v, i):
            return {'han_start': i, 'han_end': i, 'vi_start': i, 'vi_end': i,
                    'han_text': h, 'vietnamese_text': v}
        def payload(rows):
            return {'is_success': True, 'code': '000000', 'data': {'result': rows}}
        first = row('曰：「甲。', 'Nói: “Một.', 0)
        for rows in ([first, row('」乙。', '” Hai.', 1)],
                     [first, row('」', '”', 1), row('乙。', 'Hai.', 2)]):
            links = clc_response(payload(rows), han, viet, allow_terminal_quote_omission=True)
            self.assertEqual([x['han_ids'] for x in links], [['h1'], ['h2']])
            self.assertEqual([x['nghia_ids'] for x in links], [['v1'], ['v2']])
        with self.assertRaises(ValueError):
            clc_response(payload([row('」', '”', 0)]), han, viet, allow_terminal_quote_omission=True)


if __name__ == '__main__': unittest.main()
