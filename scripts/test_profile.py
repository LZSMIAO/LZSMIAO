"""Contract tests for public output, layout data and animation continuity."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from weekly_report import card as report
from update_wakatime import save_cards
import re
import unittest
import xml.etree.ElementTree as ET
from coding_card import card
from update_wakatime import duration,label,aggregate
from update_activity import activity
from smooth_snake import smooth,NS

class ProfileTests(unittest.TestCase):
    def test_card_real_and_empty(self):
        data={'total_seconds':7200,'languages':[{'name':'TypeScript','total_seconds':5400,'percent':75},{'name':'Vue','total_seconds':1800,'percent':25}],'editors':[{'name':'Qoder','total_seconds':7200}],'start':'2026-09-01T00:00:00Z','end':'2026-09-07T23:59:59Z'}
        for theme in ('light','dark'):
            svg=card(data,theme,duration,label)
            ET.fromstring(svg)
            self.assertIn('75.0%',svg)
            self.assertIn('2h 00m',svg)
            self.assertNotIn('Qoder',svg)
            empty=card({'total_seconds':0},theme,duration,label)
            self.assertIn('等待第一筆',empty)
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
        self.assertIn('暫無',activity([]))
    def test_motion_has_no_loop_hold(self):
        svg='''<svg xmlns="http://www.w3.org/2000/svg"><style>.s{animation:none linear 500ms infinite}@keyframes s0{0%,80%{transform:translate(0px,-16px)}20%{transform:translate(0px,0px)}40%{transform:translate(16px,0px)}60%{transform:translate(16px,-16px)}}.s.s0{animation-name:s0}</style><rect class="c" x="2" y="2"/><rect class="s s0" width="12" height="12"/></svg>'''
        result=smooth(svg)
        root=ET.fromstring(result)
        animation=root.find(f'.//{{{NS}}}animateMotion')
        self.assertEqual(animation.get('calcMode'),'paced')
        coords=re.findall(r'-?\d+,-?\d+',animation.get('path'))
        self.assertEqual(coords[0],coords[-1])
        self.assertTrue(all(a!=b for a,b in zip(coords,coords[1:])))
        self.assertIn('prefers-reduced-motion',result)
        self.assertNotIn('@keyframes s0',result)
        self.assertIn('class="s still"',result)
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
                self.assertIn('價格估算',svg)
                self.assertIn('7K / 350',svg)
                self.assertNotIn('Qoder',svg)
        del days[0]['grand_total']['ai_model_total_cost']
        missing=aggregate({'data':days},'2026-09-02','2026-09-08')
        self.assertIsNone(missing['ai']['ai_model_total_cost'])
        self.assertNotIn('$9.00',report(missing,'dark',duration,label))
        empty=report({'total_seconds':0},'dark',duration,label)
        self.assertNotIn('AI 協作',empty)
        self.assertIn('等待第一筆',empty)

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

    def test_unknown_generator_fails_closed(self):
        with self.assertRaises(ValueError):
            smooth('<svg xmlns="http://www.w3.org/2000/svg"><style>.s{}</style></svg>')

if __name__=='__main__':
    unittest.main()
