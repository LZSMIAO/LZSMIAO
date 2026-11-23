import io
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError, URLError
from unittest.mock import patch
import update_activity as activity


def response(value):
    return io.BytesIO(json.dumps(value).encode())


def http(code,headers=None):
    return HTTPError('https://example.invalid/private?secret=hidden',code,'private body',headers or {},None)


class FetchTests(unittest.TestCase):
    def tearDown(self):
        activity.repository.cache_clear()

    def fetch(self, effects, path='users/LZSMIAO/events/public', expected=list):
        with patch.object(activity,'urlopen',side_effect=effects) as request, patch.object(activity.time,'sleep') as sleep:
            result=activity.fetch_json(path,expected)
        return result,request,sleep

    def test_success_is_anonymous(self):
        result,request,sleep=self.fetch([response([])])
        self.assertEqual(result,[])
        self.assertNotIn('Authorization',request.call_args.args[0].headers)
        sleep.assert_not_called()

    def test_transient_statuses_retry(self):
        for code in (500,502,503,504,429):
            with self.subTest(code=code):
                result,request,sleep=self.fetch([http(code),response([])])
                self.assertEqual(request.call_count,2)
                sleep.assert_called_once_with(2)

    def test_network_retries_are_bounded(self):
        with patch.object(activity,'urlopen',side_effect=URLError('secret')) as request, patch.object(activity.time,'sleep') as sleep:
            with self.assertRaisesRegex(activity.ActivityFetchError,'^GitHub network error$'):
                activity.fetch_json('users/test/events/public',list)
            self.assertEqual(request.call_count,3)
            self.assertEqual([c.args[0] for c in sleep.call_args_list],[2,8])

    def test_permanent_errors_do_not_retry_or_leak(self):
        for code in (401,403,404):
            with patch.object(activity,'urlopen',side_effect=http(code)) as request:
                with self.assertRaisesRegex(activity.ActivityFetchError,f'^GitHub HTTP {code}$'):
                    activity.fetch_json('users/test/events/public',list)
                self.assertEqual(request.call_count,1)

    def test_rate_limit_wait_is_respected(self):
        result,request,sleep=self.fetch([http(403,{'Retry-After':'12','X-RateLimit-Remaining':'55','X-RateLimit-Reset':'9999999999'}),response([])])
        sleep.assert_called_once_with(12)

    def test_long_rate_limit_fails_without_early_retry(self):
        with patch.object(activity,'urlopen',side_effect=http(403,{'X-RateLimit-Remaining':'0','X-RateLimit-Reset':'200'})) as request, patch.object(activity.time,'time',return_value=100),patch.object(activity.time,'sleep') as sleep:
            with self.assertRaisesRegex(activity.ActivityFetchError,'rate limited'):
                activity.fetch_json('users/test/events/public',list)
            self.assertEqual(request.call_count,1)
            sleep.assert_not_called()

    def test_invalid_payloads_fail(self):
        for body in (b'not-json',b'{}'):
            with patch.object(activity,'urlopen',return_value=io.BytesIO(body)):
                with self.assertRaises(activity.ActivityFetchError):
                    activity.fetch_json('users/test/events/public',list)

    def test_repo_404_is_excluded(self):
        result,request,sleep=self.fetch([http(404)],'repos/test/repo',dict)
        self.assertIsNone(result)

    def test_repository_failure_not_swallowed(self):
        with patch.object(activity,'fetch_json',side_effect=activity.ActivityFetchError('GitHub HTTP 503')):
            with self.assertRaises(activity.ActivityFetchError):
                activity.repository_is_public('test/repo')

    def test_failed_metadata_preserves_all_files(self):
        with TemporaryDirectory() as tmp:
            root=Path(tmp); (root/'assets').mkdir()
            readme=root/'README.md'; readme.write_text(activity.START+'old'+activity.END)
            feed=root/'assets/activity.json'; feed.write_text('old-feed')
            events=[{'public':True,'repo':{'name':'test/repo'},'type':'PushEvent','created_at':'2099-01-01'}]
            with patch.object(activity,'README',readme),patch.object(activity,'fetch_json',side_effect=[events,activity.ActivityFetchError('GitHub HTTP 503')]):
                with self.assertRaises(activity.ActivityFetchError):activity.main()
            self.assertEqual(readme.read_text(),activity.START+'old'+activity.END)
            self.assertEqual(feed.read_text(),'old-feed')
            self.assertEqual(len(list((root/'assets').iterdir())),1)

if __name__=='__main__':unittest.main()
