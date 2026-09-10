"""Contract tests for public output, layout data and animation continuity."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from weekly_report import card as report
from update_wakatime import save_cards,overview
import re
import unittest
import xml.etree.ElementTree as ET
from coding_card import card
from update_wakatime import duration,label,aggregate
from update_activity import activity

class ProfileTests(unittest.TestCase):
    def test_overview_matches_report_and_preserves_other_sections(self):
        data={'total_seconds':3600,'start':'2026-09-04','end':'2026-09-10','languages':[{'name':'Vue','total_seconds':3600,'percent':100}]}
        self.assertIn('Activity time: 1h 00m',overview(data))
        self.assertIn('2026-09-04 — 2026-09-10',overview(data))
        with TemporaryDirectory() as directory:
            root=Path(directory)
            readme=root/'README.md'
            readme.write_text('before\n~~~text\n📊 Last 7 days\nstale\n~~~\nafter')
            with patch('update_wakatime.ROOT',root):
                save_cards({},data)
                first=readme.read_text()
                save_cards({},data)
            self.assertEqual(first,readme.read_text())
            self.assertTrue(first.startswith('before\n') and first.endswith('\nafter'))
            self.assertNotIn('stale',first)
    def test_card_real_and_empty(self):
        data={'total_seconds':7200,'languages':[{'name':'TypeScript','total_seconds':5400,'percent':75},{'name':'Vue','total_seconds':1800,'percent':25}],'editors':[{'name':'Qoder','total_seconds':7200}],'start':'2026-09-01T00:00:00Z','end':'2026-09-07T23:59:59Z'}
        for theme in ('light','dark'):
            svg=card(data,theme,duration,label)
            ET.fromstring(svg)
            self.assertIn('75.0%',svg)
            self.assertIn('2h 00m',svg)
            self.assertNotIn('Qoder',svg)
            empty=card({'total_seconds':0},theme,duration,label)
            self.assertIn('Waiting for the first',empty)
            self.assertNotIn('2h',empty)
    def test_seven_days_include_today(self):
        days=[{'range':{'date':f'2026-09-{day:02d}'},'grand_total':{'total_seconds':60},'languages':[{'name':'Python','total_seconds':60}]} for day in range(2,9)]
        result=aggregate({'data':days},'2026-09-02','2026-09-08')
        self.assertEqual(result['total_seconds'],420)
        self.assertEqual(result['languages'][0]['percent'],100)
        with self.assertRaises(ValueError):
            aggregate({'data':days[:-1]},'2026-09-02','2026-09-08')
    def test_public_feed_privacy_and_limit(self):
        def event(repo,public=True,kind='PushEvent',payload=None):
            return {'public':public,'type':kind,'repo':{'name':repo},'payload':payload or {},'created_at':'2026-09-08T00:00:00Z'}
        events=[event('owner/private',False),event('LZSMIAO/LZSMIAO'),event('owner/one'),event('owner/one'),event('owner/two'),event('owner/three')]
        result=activity(events)
        self.assertNotIn('private',result)
        self.assertNotIn('LZSMIAO/LZSMIAO',result)
        self.assertEqual(len(result.splitlines()),2)
        self.assertNotIn('three',result)
        self.assertIn('No public activity',activity([]))
    def test_report_uses_complete_real_ai_totals(self):
        days=[{'range':{'date':f'2026-09-{day:02d}'},'grand_total':{'total_seconds':3600,'ai_input_tokens':1000,'ai_output_tokens':50,'ai_additions':4,'ai_prompt_events_total':2,'ai_model_total_cost':1.5},'languages':[{'name':'Vue','total_seconds':3600}]} for day in range(2,9)]
        data=aggregate({'data':days},'2026-09-02','2026-09-08')
        self.assertEqual(data['ai']['ai_model_total_cost'],10.5)
        self.assertEqual(data['ai']['ai_input_tokens'],7000)
        self.assertEqual(len(data['days']),7)
        for theme in ('light','dark'):
            for mobile in (False,True):
                svg=report(data,theme,duration,label,mobile)
                root=ET.fromstring(svg)
                self.assertEqual(root.get('width'),'480' if mobile else '880')
                self.assertIn('$10.50',svg)
                self.assertIn('API pricing',svg)
                self.assertIn('7K / 350',svg)
                self.assertNotIn('Qoder',svg)
        del days[0]['grand_total']['ai_model_total_cost']
        missing=aggregate({'data':days},'2026-09-02','2026-09-08')
        self.assertIsNone(missing['ai']['ai_model_total_cost'])
        self.assertNotIn('$9.00',report(missing,'dark',duration,label))
        empty=report({'total_seconds':0},'dark',duration,label)
        self.assertNotIn('AI collaboration',empty)
        self.assertIn('Waiting for the first',empty)

    def test_report_asset_refresh_preserves_overview(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            readme=root/'README.md'
            readme.write_text('assets/coding-dark.svg assets/report-dark.svg assets/report-dark-mobile.svg')
            with patch('update_wakatime.ROOT',root):
                save_cards({'dark':'overview','report-dark':'report','report-dark-mobile':'mobile'})
                original=readme.read_text()
                save_cards({'dark':'overview','report-dark':'report','report-dark-mobile':'mobile'})
                self.assertEqual(readme.read_text(),original)
                save_cards({'dark':'overview','report-dark':'new report','report-dark-mobile':'new mobile'})
            self.assertEqual(len(list((root/'assets').glob('*.svg'))),5)
            self.assertEqual(readme.read_text().split()[0],original.split()[0])
            self.assertNotEqual(readme.read_text().split()[1:],original.split()[1:])
            for path in readme.read_text().split():
                self.assertTrue((root/path).is_file())


if __name__=='__main__':
    unittest.main()
