# coding: utf-8
from __future__ import unicode_literals

import re

from .turner import TurnerBaseIE
from ..utils import (
    int_or_none,
    float_or_none,
    strip_or_none,
    str_or_none,
)


class AdultSwimIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?adultswim\.com/videos/(?P<show_path>[^/?#]+)(?:/(?P<episode_path>[^/?#]+))?'

    _TESTS = [{
        'url': 'http://adultswim.com/videos/rick-and-morty/pilot',
        'info_dict': {
            'id': 'rQxZvXQ4ROaSOqq-or2Mow',
            'ext': 'mp4',
            'title': 'Rick and Morty - Pilot',
            'description': 'Rick moves in with his daughter\'s family and establishes himself as a bad influence on his grandson, Morty.',
            'timestamp': 1493267400,
            'upload_date': '20170427',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://www.adultswim.com/videos/tim-and-eric-awesome-show-great-job/dr-steve-brule-for-your-wine/',
        'info_dict': {
            'id': 'sY3cMUR_TbuE4YmdjzbIcQ',
            'ext': 'mp4',
            'title': 'Tim and Eric Awesome Show Great Job! - Dr. Steve Brule, For Your Wine',
            'description': 'Dr. Brule reports live from Wine Country with a special report on wines.  \nWatch Tim and Eric Awesome Show Great Job! episode #20, "Embarrassed" on Adult Swim.',
            'upload_date': '20080124',
            'timestamp': 1201150800,
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://www.adultswim.com/videos/decker/inside-decker-a-new-hero/',
        'info_dict': {
            'id': 'I0LQFQkaSUaFp8PnAWHhoQ',
            'ext': 'mp4',
            'title': 'Decker - Inside Decker: A New Hero',
            'description': 'The guys recap the conclusion of the season. They announce a new hero, take a peek into the Victorville Film Archive and welcome back the talented James Dean.',
            'timestamp': 1469480460,
            'upload_date': '20160725',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
        'expected_warnings': ['Unable to download f4m manifest'],
    }, {
        'url': 'http://www.adultswim.com/videos/attack-on-titan',
        'info_dict': {
            'id': 'b7A69dzfRzuaXIECdxW8XQ',
            'title': 'Attack on Titan',
            'description': 'md5:6c8e003ea0777b47013e894767f5e114',
        },
        'playlist_mincount': 12,
    }, {
        'url': 'http://www.adultswim.com/videos/streams/williams-stream',
        'info_dict': {
            'id': 'd8DEBj7QRfetLsRgFnGEyg',
            'ext': 'mp4',
            'title': r're:^Williams Stream \d{4}-\d{2}-\d{2} \d{2}:\d{2}$',
            'description': 'original programming',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }]

    def _real_extract(self, url):
        show_path, episode_path = re.match(self._VALID_URL, url).groups()
        display_id = episode_path or show_path
        webpage = self._download_webpage(url, display_id)
        initial_data = self._parse_json(self._search_regex(
            r'AS_INITIAL_DATA(?:__)?\s*=\s*({.+?});',
            webpage, 'initial data'), display_id)

        info = {}
        is_stream = show_path == 'streams'
        if is_stream:
            if not episode_path:
                episode_path = 'live-stream'

            video_data = next(stream for stream_path, stream in initial_data['streams'].items() if stream_path == episode_path)
            video_id = video_data.get('stream')

            if not video_id:
                entries = []
                for episode in video_data.get('archiveEpisodes', []):
                    episode_url = episode.get('url')
                    if not episode_url:
                        continue
                    entries.append(self.url_result(
                        episode_url, 'AdultSwim', episode.get('id')))
                return self.playlist_result(
                    entries, video_data.get('id'), video_data.get('title'),
                    strip_or_none(video_data.get('description')))
        else:
            show_data = initial_data['show']

            if not episode_path:
                entries = []
                for video in show_data.get('videos', []):
                    slug = video.get('slug')
                    if not slug:
                        continue
                    entries.append(self.url_result(
                        'http://adultswim.com/videos/%s/%s' % (show_path, slug),
                        'AdultSwim', video.get('id')))
                return self.playlist_result(
                    entries, show_data.get('id'), show_data.get('title'),
                    strip_or_none(show_data.get('metadata', {}).get('description')))

            video_data = show_data['sluggedVideo']
            if len(video_data['media_id']):
                video_id = video_data['media_id']
                try:
                    info = self._extract_ngtv_info(
                        video_id, {'appId':'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhcHBJZCI6InRicy13ZWItMTVldWRlIiwicHJvZHVjdCI6InR2ZSIsIm5ldHdvcmsiOiJ0YnMiLCJwbGF0Zm9ybSI6IndlYiIsImlhdCI6MTUyMTU3MDE0Mn0.MWPtrJsU2E0LvPPyAd_-8vxwtRz6Fgs7P4lZlRf7HY8'}, {
                            'url': url,
                            'site_name': 'AdultSwim',
                            'auth_required': video_data.get('auth'),
                        })
                except:
                    pass
            video_id = video_data['id']

        streams_data = self._download_json(
            'http://www.adultswim.com/videos/api/v3/videos/' + video_id + \
            '?fields=title,type,duration,collection_title,poster,stream,segments,title_id',
            video_id, 'Downloading JSON with m3u8 links')['data']
        duration = None
        chapters = []
        formats = []
        subtitles = {}
        for asset in streams_data.get('stream', {}).get('assets', []):
            try:
                asset_url = asset.get('url')
            except:
                continue
            if asset['mime_type'] == 'application/x-mpegURL':
                m3u8_url = asset_url
                if 'adultswim-ott' in m3u8_url:
                    continue # duplicated streams
                    m3u8_url = self._add_akamai_spe_token(
                        'http://token.vgtf.net/token/token_spe',
                        m3u8_url, video_id, {
                            'url': url,
                            'site_name': 'AdultSwim',
                            'auth_required': video_data.get('auth'),
                        })
                m3u8_formats = self._extract_m3u8_formats(
                    m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls-amd', fatal=False)
                if '?hdnea=' in m3u8_url:
                    for f in m3u8_formats:
                        f['_seekable'] = False
                formats.extend(m3u8_formats)
                if not duration:
                    duration = float_or_none(asset.get('duration'))
            elif asset['mime_type'] == 'text/vtt':
                if not self._request_webpage(asset_url, video_id, note='Checking subtitles availability', fatal=False):
                    continue
                subtitles.setdefault('en-us', []).append({'url': asset_url})
            elif 'ad_cue_points_hls' in asset_url:
                try:
                    cues = self._download_xml(
                        asset_url, video_id, 'Downloading ad cues for chapters')
                except:
                    continue
                if len(cues) < 2:
                    continue
                for cue in cues:
                    chapters.append({
                        'start_time': float_or_none(cue.find('start').get('milliseconds'), 1000),
                        'end_time': float_or_none(cue.find('end').get('milliseconds'), 1000)
                    })
        formats.extend(info.pop('formats', []))
        self._sort_formats(formats)

        info.update({
            'id': video_id,
            'title': str_or_none(video_data.get('title')),
            'display_id': display_id,
            'description': info.get('description') or strip_or_none(video_data.get('description')),
            'formats': formats,
        })
        if not is_stream:
            info.update({
                'duration': info.get('duration') or duration or int_or_none(video_data.get('duration')),
                'timestamp': info.get('timestamp') or int_or_none(video_data.get('launch_date')),
                'season_number': info.get('season_number') or int_or_none(video_data.get('season_number')),
                'episode_number': info.get('episode_number') or int_or_none(video_data.get('episode_number')),
                'subtitles': subtitles,
                'chapters': info.get('chapters') or chapters,
                'thumbnail': video_data.get('poster')
            })

            info['series'] = video_data.get('collection_title') or info.get('series')

        return info
