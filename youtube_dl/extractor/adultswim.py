# coding: utf-8
from __future__ import unicode_literals

import base64
import re
import time

from .turner import TurnerBaseIE
from ..utils import (
    int_or_none,
    float_or_none,
    parse_iso8601,
    strip_or_none,
    str_or_none,
    ExtractorError,
    unified_timestamp,
)


class AdultSwimIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?adultswim\.com/(?P<as_type>videos|streams)/(?P<show_path>[^/?#]+)?(?:/(?P<episode_path>[^/?#]+))?'

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
        as_type, show_path, episode_path = re.match(self._VALID_URL, url).groups()
        display_id = episode_path or show_path or as_type
        webpage = self._download_webpage(url, display_id)
        initial_data = self._parse_json(self._search_regex(
            #r'AS_INITIAL_DATA(?:__)?\s*=\s*({.+?});',
            r'(?:NEXT_DATA|INITIAL_STATE)(?:__)?\s*=\s*({.+?});',
            webpage, 'initial data'), display_id)

        info = {}
        is_stream = as_type == 'streams'
        if is_stream:
            if not show_path:
                show_path = 'live-stream'

            video_data = next(stream for stream in initial_data['streams'] if stream['id'] == show_path)
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
            props = initial_data['props']
            apollo_state = props['__APOLLO_STATE__']

            if not episode_path:
                entries = []
                playlist_title = None
                playlist_id = None
                playlist_description = None
                for k, v in apollo_state.items():
                    slug = v.get('slug')
                    if k.startswith('Video:') and slug:
                        entries.append(self.url_result(
                            'http://adultswim.com/videos/%s/%s' % (show_path, slug),
                            'AdultSwim', v.get('_id')))
                    if not playlist_id and k.startswith('VideoCollection:'):
                        playlist_description = v.get('description')
                        playlist_id = base64.b64decode(v.get('id', '')).decode('ascii').split(':')[-1]
                        playlist_title = v.get('title')
                    
                return self.playlist_result(
                    entries, playlist_id, playlist_title,
                    strip_or_none(playlist_description))

            video_data = next(v for k,v in apollo_state.items() if v.get('slug', '') == episode_path)
            video_id = video_data.get('mediaID')
            if video_id:
                requestor_info = self._downloader.cache.load('ap-mvpd', 'AdultSwim') or {}
                authn_token = requestor_info.get('authn_token')
                def is_expired(token, date_ele):
                    token_expires = unified_timestamp(re.sub(r'[_ ]GMT', '', self._search_regex(
                        '<%s>(.+?)</%s>' % (date_ele, date_ele), token, date_ele)))
                    return token_expires and token_expires <= int(time.time())
                if authn_token and is_expired(authn_token, 'simpleTokenExpires'):
                    authn_token = None
                auth_required = video_data.get('auth')
                try:
                    info = self._extract_ngtv_info(
                        video_id, {'appId': initial_data.get('runtimeConfig', {}).get('TOP_APP_ID')}, 
                        {
                            'url': url,
                            'site_name': 'AdultSwim',
                            'auth_required': auth_required or authn_token is not None,
                        })
                except Exception as e:
                    if not auth_required:
                        print(''.join(e.args))
                        pass
                    else:
                        raise e
            video_id = video_data['_id']
#["id", "collection_title", "media_id", "poster", "title", "type"]
        streams_data = self._download_json(
            'http://www.adultswim.com/api/shows/v1/videos/' + video_id + \
            '?fields=id,media_id,title,type,duration,collection_title,poster,stream,segments,title_id',
            video_id, 'Downloading JSON with m3u8 links')['data']['video']
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
            if video_data.get('type') == "CLIP":
                season_number = int_or_none(video_data.get('seasonNumber'))
                season = None
            else:                
                season_id = next(k for k,v in apollo_state.items() if k.startswith('$Season:') and v.get('node', {}).get('id') == 'Video:'+video_data.get('id',''))
                season_id = season_id.split('.')[0][1:]
                season_number = apollo_state.get(season_id, {}).get('number')
                season = apollo_state.get(season_id, {}).get('name')
            info.update({
                'duration': info.get('duration') or duration or int_or_none(video_data.get('duration')),
                'timestamp': info.get('timestamp') or parse_iso8601(video_data.get('launch_date')),
                'season_number': info.get('season_number') or int_or_none(season_number),
                'season': season,
                'episode_number': info.get('episode_number') or int_or_none(video_data.get('episodeNumber')),
                'subtitles': subtitles,
                'chapters': info.get('chapters') or chapters,
                'thumbnail': video_data.get('poster')
            })

            series = apollo_state.get(video_data.get('collection', {}).get('id'), {}).get('title')
            info['series'] = series or info.get('series')

        return info
