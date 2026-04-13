# ISSUES.md

Known ingestion issues and limitations. Auto-appended during `ingest-list` runs.

## Known Limitations

### YouTube
- Videos with transcripts **disabled** (age-restricted, creator-disabled): falls back to page metadata only
- Private/unlisted videos: will fail entirely
- **IP rate-limiting**: YouTube blocks repeated transcript requests from the same IP. First 2 requests typically succeed; subsequent ones fail with `RequestBlocked`.

**Fix for rate-limiting — use browser cookies:**
1. Install the **"Get cookies.txt LOCALLY"** Chrome extension
2. Go to `youtube.com` while logged in
3. Click the extension → Export cookies → save as `data/youtube_cookies.txt`
4. Add to `.env`: `YOUTUBE_COOKIES_FILE=data/youtube_cookies.txt`
5. Re-run: `uv run second-brain ingest-list /tmp/remaining_youtube.txt`

A 2-second delay between YouTube fetches is now applied automatically to reduce rate limiting.

### JS-rendered documentation sites
- TrueFoundry docs (`truefoundry.com/docs`): Mintlify SPA — uses DuckDuckGo fallback to fetch sub-pages
- Claude Agent SDK (`code.claude.com`): likely JS-rendered — uses DuckDuckGo fallback
- LangChain docs (`docs.langchain.com`): JS-rendered — uses DuckDuckGo fallback

### Workaround for JS docs
Use **Obsidian Web Clipper** (browser extension) to manually clip a doc page to markdown and save it to `data/raw/`. Then `second-brain ingest data/raw/<filename>.md`.

---

## [2026-04-12 19:48 UTC] Issues from: /tmp/youtube_urls.txt
- [https://youtu.be/xlUIiTSaFKI] ERROR: Could not fetch YouTube video https://youtu.be/xlUIiTSaFKI: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=xlUIiTSaFKI! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
- [https://youtu.be/HvBCcmzS_vs] ERROR: Could not fetch YouTube video https://youtu.be/HvBCcmzS_vs: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=HvBCcmzS_vs! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
- [https://youtu.be/zvWIfROm-uE] ERROR: Could not fetch YouTube video https://youtu.be/zvWIfROm-uE: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=zvWIfROm-uE! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
- [https://youtu.be/v-qDbpNeluk] ERROR: Could not fetch YouTube video https://youtu.be/v-qDbpNeluk: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=v-qDbpNeluk! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
- [https://youtu.be/LLDkAr5MZR8] ERROR: Could not fetch YouTube video https://youtu.be/LLDkAr5MZR8: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=LLDkAr5MZR8! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!
- [https://youtu.be/WWTngf_OqaY] ERROR: Could not fetch YouTube video https://youtu.be/WWTngf_OqaY: 
Could not retrieve a transcript for the video https://www.youtube.com/watch?v=WWTngf_OqaY! This is most likely caused by:

YouTube is blocking requests from your IP. This usually is due to one of the following reasons:
- You have done too many requests and your IP has been blocked by YouTube
- You are doing requests from an IP belonging to a cloud provider (like AWS, Google Cloud Platform, Azure, etc.). Unfortunately, most IPs from cloud providers are blocked by YouTube.

Ways to work around this are explained in the "Working around IP bans" section of the README (https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception).


If you are sure that the described cause is not responsible for this error and that a transcript should be retrievable, please create an issue at https://github.com/jdepoix/youtube-transcript-api/issues. Please add which version of youtube_transcript_api you are using and provide the information needed to replicate the error. Also make sure that there are no open issues which already describe your problem!

## [2026-04-13 08:41 UTC] Issues from: /tmp/yt_remaining.txt
- [https://youtu.be/v-qDbpNeluk] ERROR: Connection error.
