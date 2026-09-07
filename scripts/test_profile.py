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
    def test_motion_stops_for_starvation_story(self):
        svg='''<svg xmlns="http://www.w3.org/2000/svg"><style>.s{animation:none linear 500ms infinite}@keyframes s0{0%,80%{transform:translate(0px,-16px)}20%{transform:translate(0px,0px)}40%{transform:translate(16px,0px)}60%{transform:translate(16px,-16px)}}.s.s0{animation-name:s0}</style><rect class="c" x="2" y="2"/><rect class="s s0" width="12" height="12"/></svg>'''
        result=smooth(svg)
        root=ET.fromstring(result)
        animation=root.find(f'.//{{{NS}}}animateMotion')
        self.assertEqual(animation.get('calcMode'),'linear')
        self.assertEqual(animation.get('keyPoints'),'0;1;1')
        self.assertLess(float(animation.get('keyTimes').split(';')[1]),1)
        coords=re.findall(r'-?\d+,-?\d+',animation.get('path'))
        self.assertNotEqual(coords[0],coords[-1])
        self.assertTrue(all(a!=b for a,b in zip(coords,coords[1:])))
        self.assertIn('prefers-reduced-motion',result)
        self.assertNotIn('@keyframes s0',result)
        self.assertIn('class="s still"',result)
        self.assertIn(' Q',animation.get('path'))
        self.assertIn('蛇饿死了',result)
        self.assertNotIn('class="u ',result)
        blur=root.find(f'.//{{{NS}}}feGaussianBlur')
        self.assertEqual(len(blur),0)
        self.assertIsNotNone(root.find(f'.//{{{NS}}}g[@class="scene"]'))
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

    def test_snake_eats_first_and_stops_before_second(self):
        svg='<svg xmlns="http://www.w3.org/2000/svg" viewBox="-16 -32 880 192"><style>:root{--ce:#161b22;--cs:purple}.c.c0{fill:var(--c4);animation-name:c0}@keyframes c0{50%{fill:var(--c4)}50.1%,100%{fill:var(--ce)}}.c.c1{fill:var(--c4);animation-name:c1}@keyframes c1{80%{fill:var(--c4)}80.1%,100%{fill:var(--ce)}}.s{animation:none linear 10000ms infinite}@keyframes s0{0%{transform:translate(0px,-16px)}10%{transform:translate(0px,0px)}50%{transform:translate(64px,0px)}80%{transform:translate(64px,48px)}100%{transform:translate(0px,-16px)}}</style><rect class="c c0" x="66" y="2"/><rect class="c c1" x="66" y="50"/><rect class="u u0" width="880" height="12"/><rect class="s s0" width="14" height="14"/><rect class="s s1" width="12" height="12"/></svg>'
        result=smooth(svg)
        root=ET.fromstring(result)
        motions=root.findall(f'.//{{{NS}}}animateMotion')
        self.assertTrue(motions[0].get('path').endswith('L64,24'))
        self.assertLess(float(motions[0].get('dur')[:-1]),5)
        self.assertIn('@keyframes eat-first',result)
        self.assertEqual([n.text for n in root.findall(f'.//{{{NS}}}text')],['蛇饿死了'])
        frozen=root.find(f'.//{{{NS}}}g[@data-layer="frozen-scene"]')
        self.assertEqual(len(frozen.findall(f'{{{NS}}}rect[@fill="#f85149"]')),2)
        self.assertNotIn('animate',ET.tostring(frozen,encoding='unicode'))
        self.assertNotIn('first-food',ET.tostring(frozen,encoding='unicode'))
        self.assertIsNotNone(frozen.find(f'{{{NS}}}path[@data-face="crossed-eyes"]'))
        self.assertIsNotNone(root.find(f'.//{{{NS}}}g[@class="snake-motion"]/{{{NS}}}path[@class="dead-eyes"]'))
        caption=root.find(f'.//{{{NS}}}g[@class="death"]/{{{NS}}}text')
        self.assertEqual(caption.get('fill'),'#f85149')
        css=root.find(f'{{{NS}}}style').text
        death=float(re.search(r'@keyframes starve\{0%\{[^}]+\}([\d.]+)%',css)[1])
        blur=float(re.search(r'@keyframes dead\{0%\{[^}]+\}([\d.]+)%',css)[1])
        cycle=float(motions[0].get('dur')[:-1])
        self.assertAlmostEqual((blur-death)*cycle/100,2,places=5)
        self.assertIn(f'{death:.6f}%,100%{{opacity:1}}',css)
        self.assertNotIn('.dead-eyes{visibility:visible',css)

        self.assertTrue(motions[1].get('path').endswith('L64,8'))
        self.assertNotIn('@keyframes c0',result)
        self.assertNotIn('class="u ',result)
        self.assertEqual(root.get('height'),'168')

    def test_unknown_generator_fails_closed(self):
        with self.assertRaises(ValueError):
            smooth('<svg xmlns="http://www.w3.org/2000/svg"><style>.s{}</style></svg>')

if __name__=='__main__':
    unittest.main()
