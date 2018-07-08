# coding: utf-8
from __future__ import unicode_literals

import re
import base64

from .adobepass import AdobePassIE
from ..utils import (
    float_or_none,
    int_or_none,
    determine_ext,
    parse_age_limit,
    parse_duration,
)

class OprahIE(AdobePassIE):
    _VALID_URL = r'https?://(?:www\.)?oprah\.com/(?P<show_path>[^/]+)/(?P<episode_path>[^?]+)'

    def _real_extract(self, url):
        show_path, episode_path = re.match(self._VALID_URL, url).groups()
        display_id = episode_path
        
        #webpage = self._download_webpage(url, display_id)
        print('Open view-source:%s in your browser, '
            'find "O20.api_data_hash", copy big base64 data block, save as .txt '
            'with ASCII encoding. Enter the name of the saved file when done.' % url)
        bdfilename = input()
        with open(bdfilename, 'r', encoding='ascii') as f:
            base64_data = f.read()
        initial_data = self._parse_json(base64_data, display_id, transform_source=base64.b64decode)

        clip_data = initial_data.get('clip_data')
        feed_data = self._parse_json(clip_data.get('feed_data'), display_id).get('channel').get('item')
        m3u8_url = clip_data.get('contentPath')
        if clip_data.get('tve_auth_required') == 'y':
            token_url = 'https://tve-tv.oprah.com/tvs/v1/sign'
            query = {
                'cdn': 'akamai',
                'resource': 'T1dO',
                'format': 'json',
                'url': m3u8_url,
            }
            query['mediaToken'] = base64.b64encode(self._extract_mvpd_auth(url, display_id, 'OWN', 'OWN').encode())
            auth = self._download_json(
                token_url, display_id, 'Downloading JSON with auth. token', query=query)
            m3u8_url = auth.get('url', m3u8_url)

        formats = []
        m3u8_formats = self._extract_m3u8_formats(
            m3u8_url, display_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
        if '?hdnea=' in m3u8_url:
            for f in m3u8_formats:
                f['_seekable'] = False
        formats.extend(m3u8_formats)
        self._sort_formats(formats)

        subtitles = {}
        cc_url = clip_data.get('captionPath')
        if cc_url:
            ext = determine_ext(cc_url)
            if ext == 'xml':
                ext = 'ttml'
            subtitles.setdefault('en-us', []).append({
                'url': cc_url,
                'ext': ext,
            })

        chapters = []
        npchap = feed_data.get('media-scenes', {}).get('media-scene', [])
        if len(npchap) > 1:
            for chapter in npchap:
                chapters.append({
                    'start_time': parse_duration(chapter.get('sceneStartTime')),
                    'end_time': parse_duration(chapter.get('sceneEndTime')),
                })

        return {
            'id': display_id,
            'formats': formats,
            'title': clip_data.get('title'),
            'description': clip_data.get('description'),
            'duration': float_or_none(clip_data.get('playingTime')),
            'thumbnail': clip_data.get('thumbnailPath'),
            'season_number': int_or_none(initial_data.get('own_season_number')),
            'episode_number': int_or_none(initial_data.get('own_episode_number')),
            'series': initial_data.get('app').get('title'),
            'subtitles': subtitles,
            'age_limit': parse_age_limit(clip_data.get('tve_video_rating') or initial_data.get('clip_rating')),
            'chapters': chapters,
        }
