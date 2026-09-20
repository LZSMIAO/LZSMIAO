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
from update_activity import activity,activity_card
from daily_art import card as art,shape
from drift_bottle import sentence,card as bottle,update_content as bottle_content,local_day
from publish import publish
from ocean import SEAS

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
    def test_overview_stays_narrow_enough_for_a_phone(self):
        # A 390px phone shows about 45 monospace columns before the block scrolls.
        data={'total_seconds':82800,'start':'2026-09-15','end':'2026-09-21','languages':[
            {'name':'WebGPU Shading Language','total_seconds':40000,'percent':48.3},
            {'name':'Objective-C++','total_seconds':30000,'percent':36.2},
            {'name':'TypeScript','total_seconds':12800,'percent':15.5}]}
        for line in overview(data).split('\n'):
            self.assertLessEqual(len(line),45,line)
        self.assertIn('23h 00m',overview(data))

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
        result=activity(events, visibility_check=lambda repo: True)
        self.assertNotIn('private',result)
        self.assertNotIn('LZSMIAO/LZSMIAO',result)
        self.assertEqual(result.count('<picture>'),2)
        self.assertNotIn('three',result)
        self.assertIn('No public activity',activity([]))
    def test_activity_card_date_is_right_aligned_without_wrapping(self):
        for mobile,width in [(False,880),(True,480)]:
            svg=activity_card('organization/project','Updated project','2026-09-20',True,mobile)
            root=ET.fromstring(svg)
            date=root.findall('.//{http://www.w3.org/2000/svg}text')[-1]
            self.assertEqual(date.text,'2026-09-20')
            self.assertEqual(date.get('text-anchor'),'end')
            self.assertEqual(int(date.get('x')),width-20)

    def test_public_organization_activity_is_included(self):
        events=[{'public':True,'type':'PushEvent','repo':{'name':'my-organization/public-project'},'payload':{},'created_at':'2026-09-20T00:00:00Z'}]
        result=activity(events, visibility_check=lambda repo: repo=='my-organization/public-project')
        self.assertIn('https://github.com/my-organization/public-project',result)

    def test_public_event_from_now_private_repository_is_hidden(self):
        events=[{'public':True,'type':'PushEvent','repo':{'name':'owner/now-private'},'payload':{},'created_at':'2026-09-20T00:00:00Z'}]
        result=activity(events, visibility_check=lambda repo: False)
        self.assertNotIn('owner/now-private',result)
        self.assertIn('No public activity',result)

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

    def test_daily_art_is_stable_within_a_day_and_moves_between_days(self):
        for theme in ('light','dark'):
            for mobile in (False,True):
                svg=art('2026-09-21',theme,mobile)
                self.assertEqual(ET.fromstring(svg).get('width'),'480' if mobile else '880')
                self.assertEqual(svg,art('2026-09-21',theme,mobile))
                self.assertIn('2026-09-21',svg)
                self.assertNotEqual(svg,art('2026-09-22',theme,mobile))
        # Peaks are fractions, so one silhouette serves both widths.
        self.assertEqual(shape('2026-09-21'),shape('2026-09-21'))
        self.assertNotEqual(shape('2026-09-21')['peaks'],shape('2026-09-22')['peaks'])

    def test_daily_art_keeps_every_crest_inside_the_frame(self):
        for day in ('2026-09-21','2026-09-22','2026-09-23','2026-09-24','2026-09-25'):
            for mobile in (False,True):
                root=ET.fromstring(art(day,'light',mobile))
                height=float(root.get('height'))
                for path in root.findall('.//{http://www.w3.org/2000/svg}path'):
                    # The final two points close the shape below the viewBox on purpose.
                    for point in path.get('d').lstrip('M').split('L')[:-2]:
                        self.assertGreaterEqual(float(point.split(',')[1]),0)
                        self.assertLess(float(point.split(',')[1]),height)

    def test_bottle_keeps_only_plain_text_from_a_stranger(self):
        self.assertEqual(sentence('### Your one line\n\nreal words'),'real words')
        self.assertEqual(sentence('a'+chr(0x200B)+'b'+chr(0x07)+'c'),'abc')
        self.assertEqual(sentence(chr(0x202E)+'flip'+chr(0x202C)+' me'),'flip me')
        self.assertEqual(sentence('first\nsecond'),'first')
        self.assertEqual(sentence('_No response_'),'')
        self.assertEqual(sentence('   \n\t '),'')
        self.assertEqual(len(sentence('x'*200)),48)

    def test_bottle_escapes_markup_in_every_variant(self):
        hostile=sentence('</text><script>alert(1)</script>')
        for theme in ('light','dark'):
            for mobile in (False,True):
                svg=bottle(hostile,'octocat','2026-09-21',theme,mobile)
                ET.fromstring(svg)
                self.assertNotIn('<script>',svg)
                self.assertIn('&lt;script&gt;',svg)
        empty=bottle('','','','light')
        ET.fromstring(empty)
        self.assertNotIn('@',empty)

    def test_bottle_replaces_the_previous_one(self):
        original='head\n<!-- BOTTLE:START -->\nold\n<!-- BOTTLE:END -->\ntail'
        first={}
        once=bottle_content(original,'first line','someone','2026-09-21',1,first)
        self.assertEqual(len(first),4)
        second={}
        twice=bottle_content(once,'second line','other','2026-09-22',2,second)
        self.assertIn('issues/2',twice)
        self.assertNotIn('issues/1',twice)
        self.assertNotIn('old',twice)
        self.assertEqual(set(first)&set(second),set())
        self.assertTrue(twice.startswith('head\n') and twice.endswith('\ntail'))

    def test_bottle_dates_follow_Hong_Kong_not_UTC(self):
        # 01:57 in Hong Kong is still the previous afternoon in UTC.
        self.assertEqual(local_day('2026-09-20T17:57:24Z'),'2026-09-21')
        self.assertEqual(local_day('2026-09-21T12:00:00Z'),'2026-09-21')
        self.assertEqual(local_day('2026-09-21T15:59:59Z'),'2026-09-21')
        self.assertEqual(local_day('2026-09-21T16:00:00Z'),'2026-09-22')
        with self.assertRaises(ValueError):
            local_day('not a timestamp')

    def test_daily_art_keeps_its_peaks_away_from_the_edges(self):
        from datetime import date,timedelta
        for step in range(120):
            day=str(date(2026,9,21)+timedelta(days=step))
            peaks=shape(day)['peaks']
            self.assertTrue(peaks)
            for across,_,amplitude,_,_ in peaks:
                # An edge peak reads as a half-cropped accident, a flat one as no drawing at all.
                self.assertGreaterEqual(across,.24)
                self.assertLessEqual(across,.76)
                self.assertGreaterEqual(amplitude,.30)

    def test_bottle_floats_on_an_animated_sea(self):
        for theme in ('light','dark'):
            for mobile in (False,True):
                svg=bottle('a line from a stranger','octocat','2026-09-21',theme,mobile)
                ET.fromstring(svg)
                self.assertIn('animateTransform',svg)
                self.assertIn(SEAS[theme]['cork'],svg)
                self.assertGreaterEqual(svg.count('<path'),3)
        # An empty sea still moves, but nothing is floating on it.
        empty=bottle('','','','dark')
        ET.fromstring(empty)
        self.assertIn('animateTransform',empty)
        self.assertNotIn(SEAS['dark']['cork'],empty)
        self.assertNotIn(SEAS['dark']['note'],empty)

    def test_publish_rotates_history_and_prunes_only_its_own_stem(self):
        with TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'assets').mkdir()
            readme=root/'README.md'
            readme.write_text('assets/art-light.svg assets/art-light-mobile.svg')
            publish({'art-light':'one','art-light-mobile':'m'},root)
            first=readme.read_text()
            publish({'art-light':'one','art-light-mobile':'m'},root)
            self.assertEqual(readme.read_text(),first)
            for body in ('two','three','four'):
                publish({'art-light':body,'art-light-mobile':'m'},root)
            kept=[p.name for p in (root/'assets').glob('art-light-*.svg') if re.fullmatch(r'art-light-[a-f0-9]+\.svg',p.name)]
            self.assertEqual(len(kept),3)
            self.assertEqual(len(list((root/'assets').glob('art-light-mobile-*.svg'))),1)
            for path in readme.read_text().split():
                self.assertTrue((root/path).is_file())


if __name__=='__main__':
    unittest.main()
