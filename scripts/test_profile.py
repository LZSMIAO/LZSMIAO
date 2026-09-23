"""Contract tests for public output, layout data and animation continuity."""
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from weekly_report import card as report,languages
from update_wakatime import save_cards
import re
import unittest
import xml.etree.ElementTree as ET
from coding_card import card
from update_wakatime import duration,label,aggregate,merge_remainder
from update_activity import activity,activity_card
from daily_art import card as art,shape
from drift_bottle import sentence,card as bottle,update_content as bottle_content,local_day
from publish import publish
from ocean import SEAS
from flowfield import card as flow,field,STYLES

class ProfileTests(unittest.TestCase):
    def test_cards_refresh_without_an_overview_block(self):
        # The plain-text overview repeated the report word for word; it is gone,
        # and refreshing cards must not demand or recreate it.
        with TemporaryDirectory() as directory:
            root=Path(directory)
            readme=root/'README.md'
            readme.write_text('before assets/report-dark.svg after')
            with patch('update_wakatime.ROOT',root):
                save_cards({'report-dark':'report'})
            self.assertNotIn('~~~',readme.read_text())
            self.assertTrue(readme.read_text().startswith('before assets/report-dark-'))

    def test_remainder_folds_into_the_language_wakatime_already_calls_other(self):
        rows=[{'name':'Other','total_seconds':1800,'percent':50.0},
              {'name':'Rust','total_seconds':900,'percent':25.0}]
        merged=merge_remainder(rows,900,3600)
        self.assertEqual([r['name'] for r in merged],['Other','Rust'])
        self.assertEqual(merged[0]['total_seconds'],2700)
        self.assertEqual(merged[0]['percent'],75.0)
        self.assertEqual(rows[0]['total_seconds'],1800)
        added=merge_remainder([{'name':'Rust','total_seconds':2700,'percent':75.0}],900,3600)
        self.assertEqual([r['name'] for r in added],['Rust','Other'])
        data={'total_seconds':3600,'start':'2026-09-15','end':'2026-09-21','languages':[
            {'name':'Other','total_seconds':1800,'percent':50.0},
            {'name':'Rust','total_seconds':900,'percent':25.0},
            {'name':'Vue','total_seconds':450,'percent':12.5},
            {'name':'Go','total_seconds':300,'percent':8.3},
            {'name':'C','total_seconds':150,'percent':4.2}]}
        rows=languages(data)
        self.assertEqual([r['name'] for r in rows].count('Other'),1)
        # Folding the tail in can lift Other past a row it trailed; the order, and
        # so the accent, must follow the merged totals.
        lifted={'total_seconds':1000,'languages':[
            {'name':'TypeScript','total_seconds':300,'percent':30.0},
            {'name':'Other','total_seconds':250,'percent':25.0},
            {'name':'Vue','total_seconds':150,'percent':15.0},
            {'name':'Go','total_seconds':100,'percent':10.0},
            {'name':'C','total_seconds':100,'percent':10.0},
            {'name':'Rust','total_seconds':100,'percent':10.0}]}
        self.assertEqual([r['name'] for r in languages(lifted)][:2],['Other','TypeScript'])

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
        # Only drawn text counts: the embedded @font-face rule has an @ of its own.
        drawn=''.join(''.join(node.itertext()) for node in ET.fromstring(empty).iter('{http://www.w3.org/2000/svg}text'))
        self.assertNotIn('@',drawn)

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
                self.assertIn(SEAS[theme]['accent'],svg)
                self.assertGreaterEqual(svg.count('<path'),3)
                # Line work like the header: no filled sea, sky, moon or gradient.
                self.assertNotIn('Gradient',svg)
        # An empty sea still moves, but nothing is floating on it.
        empty=bottle('','','','dark')
        ET.fromstring(empty)
        self.assertIn('animateTransform',empty)
        self.assertNotIn(SEAS['dark']['accent'],empty)

    def test_flow_field_is_deterministic_and_animated(self):
        for theme in ('light','dark'):
            svg=flow(theme)
            ET.fromstring(svg)
            self.assertEqual(svg,flow(theme))
            self.assertNotEqual(svg,flow(theme,seed='other'))
            self.assertIn('@keyframes',svg)
            # Each dash style must travel exactly one period, or the loop visibly jumps.
            for i,(dash,gap,_) in enumerate(STYLES):
                self.assertIn(f'@keyframes k{i}{{to{{stroke-dashoffset:{-(dash+gap)}}}}}',svg)
        self.assertEqual(ET.fromstring(flow('dark',480,200,mobile=True)).get('width'),'480')

    def test_flow_field_stays_gentle_enough_to_avoid_a_crease(self):
        # Beyond about a radian of swing the streamlines fold into a hard diagonal.
        for seed in ('2026','a','b','c','d'):
            angle=field(seed)
            values=[angle(x/24,y/12) for x in range(25) for y in range(13)]
            self.assertLess(max(values)-min(values),3.2)

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
