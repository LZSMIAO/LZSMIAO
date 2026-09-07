"""Contract tests for public output, layout data and animation continuity."""
from pathlib import Path
import re
import unittest
import xml.etree.ElementTree as ET
from coding_card import card
from update_wakatime import duration,label,render
from update_activity import activity
from smooth_snake import smooth,NS

class ProfileTests(unittest.TestCase):
    def test_card_real_and_empty(self):
        data={'total_seconds':7200,'languages':[{'name':'TypeScript','total_seconds':5400,'percent':75},{'name':'Vue','total_seconds':1800,'percent':25}],'editors':[{'name':'Qoder','total_seconds':7200}],'start':'2026-09-01T00:00:00Z','end':'2026-09-07T23:59:59Z'}
        render(data)
        for theme in ('light','dark'):
            svg=card(data,theme,duration,label)
            ET.fromstring(svg)
            self.assertIn('75.0%',svg)
            self.assertIn('2h 00m',svg)
            empty=card({'total_seconds':0},theme,duration,label)
            self.assertIn('等待第一筆',empty)
            self.assertNotIn('2h',empty)
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
    def test_unknown_generator_fails_closed(self):
        with self.assertRaises(ValueError):
            smooth('<svg xmlns="http://www.w3.org/2000/svg"><style>.s{}</style></svg>')

if __name__=='__main__':
    unittest.main()
