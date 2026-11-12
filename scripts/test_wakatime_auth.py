"""OAuth reads, independent refreshes and unchanged-data failure contracts."""
from contextlib import redirect_stderr
from datetime import datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from zoneinfo import ZoneInfo
import json
import os
import unittest
import update_wakatime as subject


def failure(code):
    return HTTPError('https://api.wakatime.com/private', code, 'private', {}, BytesIO(b'private'))


class OAuthTests(unittest.TestCase):
    def test_bearer_only_and_no_credential_in_url(self):
        response=BytesIO(b'{"data":[]}');response.status=200
        with patch.object(subject,'urlopen',return_value=response) as request:
            self.assertEqual(subject.fetch('test-token','users/current/summaries'),{'data':[]})
        req=request.call_args.args[0]
        self.assertEqual(req.get_header('Authorization'),'Bearer test-token')
        self.assertNotIn('test-token',req.full_url)

    def test_calculating_response_retries_and_recovers(self):
        pending=BytesIO(b'');pending.status=202
        complete=BytesIO(b'{"data":[]}');complete.status=200
        with patch.object(subject,'urlopen',side_effect=[pending,complete]) as request, patch.object(subject.time,'sleep') as sleep:
            self.assertEqual(subject.fetch('test-token','users/current/summaries'),{'data':[]})
        self.assertEqual(request.call_count,2)
        sleep.assert_called_once_with(1)

    def test_calculating_response_exhaustion_is_bounded(self):
        responses=[]
        for _ in range(3):
            response=BytesIO(b'');response.status=202;responses.append(response)
        with patch.object(subject,'urlopen',side_effect=responses) as request, patch.object(subject.time,'sleep'):
            self.assertIsNone(subject.fetch('test-token','users/current/summaries'))
        self.assertEqual(request.call_count,3)

    def test_authentication_failures_are_not_retried(self):
        for code in (401,403):
            with patch.object(subject,'urlopen',side_effect=failure(code)) as request, patch.object(subject.time,'sleep') as sleep:
                with self.assertRaises(HTTPError):subject.fetch('test-token','users/current/summaries')
            self.assertEqual(request.call_count,1);sleep.assert_not_called()

    def test_server_failures_have_bounded_retries(self):
        with patch.object(subject,'urlopen',side_effect=[failure(503) for _ in range(3)]) as request, patch.object(subject.time,'sleep') as sleep:
            with self.assertRaises(HTTPError):subject.fetch('test-token','users/current/summaries')
        self.assertEqual(request.call_count,3)
        self.assertEqual([c.args[0] for c in sleep.call_args_list],[1,2])

    def test_network_errors_have_bounded_retries(self):
        with patch.object(subject,'urlopen',side_effect=URLError('private')) as request, patch.object(subject.time,'sleep'):
            with self.assertRaises(URLError):subject.fetch('test-token','users/current/summaries')
        self.assertEqual(request.call_count,3)

    def test_pending_is_not_reported_as_fresh_success(self):
        with patch.dict(os.environ,{'WAKATIME_ACCESS_TOKEN':'test-token'},clear=True), patch.object(subject,'fetch',return_value=None), patch.object(subject,'save_cards') as save:
            with self.assertRaises(ValueError):subject.main()
        save.assert_not_called()

    def test_missing_token_does_not_fall_back_to_write_only_api_key(self):
        with patch.dict(os.environ,{'WAKATIME_API_KEY':'old-key'},clear=True), patch.object(subject,'fetch') as fetch, redirect_stderr(StringIO()):
            with self.assertRaises(ValueError):subject.main()
        fetch.assert_not_called()

    def test_forbidden_preserves_history_and_cards(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets').mkdir();history=root/'assets/coding-history.json'
            history.write_text('{"days":[]}');readme=root/'README.md';readme.write_text('previous card')
            with patch.dict(os.environ,{'WAKATIME_ACCESS_TOKEN':'test-token'},clear=True), patch.object(subject,'ROOT',root), patch.object(subject,'HISTORY',history), patch.object(subject,'fetch',side_effect=failure(403)):
                with self.assertRaises(HTTPError):subject.main()
            self.assertEqual(history.read_text(),'{"days":[]}')
            self.assertEqual(readme.read_text(),'previous card')

    def test_summaries_only_token_refreshes_without_profile_scope(self):
        end=datetime.now(ZoneInfo('Asia/Hong_Kong')).date()
        payload={'data':[{'range':{'date':str(end-timedelta(days=i))},'grand_total':{'total_seconds':60},'languages':[{'name':'Python','total_seconds':60}],'editors':[{'name':'Codex','total_seconds':60}]} for i in range(7)]}
        def fetch(key,path,params=None):
            if path=='users/current':raise failure(403)
            self.assertEqual(path,'users/current/summaries')
            return payload
        with TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'assets').mkdir();history=root/'assets/coding-history.json'
            readme=root/'README.md';readme.write_text('assets/report-dark.svg')
            with patch.dict(os.environ,{'WAKATIME_ACCESS_TOKEN':'test-token'},clear=True), patch.object(subject,'ROOT',root), patch.object(subject,'HISTORY',history), patch.object(subject,'fetch',side_effect=fetch):
                subject.main()
            self.assertEqual(len(json.loads(history.read_text())['days']),7)
            self.assertRegex(readme.read_text(),r'assets/report-dark-[a-f0-9]+\.svg')
            self.assertEqual(len(list((root/'assets').glob('*.svg'))),8)

    def test_workflow_keeps_activity_independent_and_failures_visible(self):
        workflow=(subject.ROOT/'.github/workflows/wakatime.yml').read_text()
        self.assertIn('WAKATIME_ACCESS_TOKEN: ${{ secrets.WAKATIME_ACCESS_TOKEN }}',workflow)
        self.assertNotIn('WAKATIME_API_KEY',workflow)
        self.assertIn('name: Fetch recent public activity\n        if: ${{ !cancelled() }}',workflow)
        self.assertNotIn('continue-on-error',workflow)
        self.assertIn('git diff --cached --quiet',workflow)

if __name__=='__main__':unittest.main()
