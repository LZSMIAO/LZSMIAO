# Music update reliability

Weekly history requests make at most three attempts, with 1-second and 2-second
backoff and a 20-second timeout per attempt. HTTP 429/5xx, transient network
errors, business 429/5xx, and missing weekly data are retried. Authentication or
other permanent business errors are not retried. An empty weekData array is valid.

Diagnostics contain only stage, bounded numeric business/HTTP code, and attempt
count. URLs, account IDs, response messages, and payloads are never logged.
Examples: BUSINESS_403, BUSINESS_503, WEEK_DATA_MISSING, TIMEOUT.

assets/netease-covers.json stores validated inline images keyed by SHA-256 of the
exact normalized public cover URL. The next successful update populates it;
subsequent updates reuse matching covers without a network request. Corrupt
entries are fetched again. Only the current five covers are retained, so old
albums cannot accumulate indefinitely. A new cover that fails all retries still
fails the update; an unrelated cached cover is never substituted.

On exhausted errors, the existing card is retained and the job still fails.
Notifications are not muted. All checkout actions are pinned to v5 (Node 24).

Tests:

```sh
node --test scripts/test_music_request.mjs scripts/test_music_cover.mjs scripts/test_music.mjs
python3 -m unittest discover -s scripts -p test_profile.py
```
