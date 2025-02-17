# coding: utf-8
from __future__ import unicode_literals

import re

from .adobepass import AdobePassIE
from ..utils import (
    float_or_none,
    int_or_none,
    determine_ext,
    parse_age_limit,
    urlencode_postdata,
    unified_strdate,
    ExtractorError,
)


class GoIE(AdobePassIE):
    _SITE_INFO = {
        'abc': {
            'brand': '001',
            'requestor_id': 'ABC',
        },
        'disneynow': {
            'brand': '011',
            'requestor_id': None,
        },
        'freeform': {
            'brand': '002',
            'requestor_id': 'ABCFamily',
        },
        'watchdisneychannel': {
            'brand': '004',
            'requestor_id': 'Disney',
        },
        'watchdisneyjunior': {
            'brand': '008',
            'requestor_id': 'DisneyJunior',
        },
        'watchdisneyxd': {
            'brand': '009',
            'requestor_id': 'DisneyXD',
        }
    } # http://disneynow.go.com/watch-live?brand=disney-channel,-junior,-xd
    _VALID_URL = r'https?://(?:(?P<sub_domain>%s)\.)?go\.com/(?:(?:[^/]+/)*(?P<id>(?:vdka|VDKA)\w+)|(?:[^/]+/)*(?P<display_id>[^/?#]+))' % '|'.join(_SITE_INFO.keys())
    _TESTS = [{
        'url': 'http://abc.go.com/shows/designated-survivor/video/most-recent/VDKA3807643',
        'info_dict': {
            'id': 'VDKA3807643',
            'ext': 'mp4',
            'title': 'The Traitor in the White House',
            'description': 'md5:05b009d2d145a1e85d25111bd37222e8',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }, {
        'url': 'http://watchdisneyxd.go.com/doraemon',
        'info_dict': {
            'title': 'Doraemon',
            'id': 'SH55574025',
        },
        'playlist_mincount': 51,
    }, {
        'url': 'http://abc.go.com/shows/the-catch/episode-guide/season-01/10-the-wedding',
        'only_matching': True,
    }, {
        'url': 'http://abc.go.com/shows/world-news-tonight/episode-guide/2017-02/17-021717-intense-stand-off-between-man-with-rifle-and-police-in-oakland',
        'only_matching': True,
    }]

    # https://api.contents.watchabc.go.com/vp2/ws/s/contents/3000/channels/011/001/-1

    def _extract_videos(self, brand, video_id='-1', show_id='-1'):
        display_id = video_id if video_id != '-1' else show_id
        return self._download_json(
            'http://api.contents.watchabc.go.com/vp2/ws/contents/3000/videos/%s/001/-1/%s/-1/%s/-1/-1.json' % (brand, show_id, video_id),
            display_id)['video']

    def _real_extract(self, url):
        sub_domain, video_id, display_id = re.match(self._VALID_URL, url).groups()
        site_info = self._SITE_INFO[sub_domain]
        brand = site_info['brand']
        video_data = None

        if display_id == 'watch-live':
            channel = self._search_regex(r'[\?&]brand=disney-([a-zA-Z]+)', url, 'channel', default='channel')
            site_info = self._SITE_INFO['watchdisney' + channel]
            brand = site_info['brand']
            video_data = self._download_json(
                'http://api.contents.watchabc.go.com/vp2/ws/s/contents/3000/channels/%s/001/-1.json' % brand, display_id)['channel'][0]
        elif not video_id:
            webpage = self._download_webpage(url, display_id)
            video_id = self._search_regex(
                # There may be inner quotes, e.g. data-video-id="'VDKA3609139'"
                # from http://freeform.go.com/shows/shadowhunters/episodes/season-2/1-this-guilty-blood
                r'data-video-id=["\']*(VDKA\w+)', webpage, 'video id', default=None)
            if not video_id:
                # show extraction works for Disney, DisneyJunior and DisneyXD
                # ABC and Freeform has different layout
                show_id = self._search_regex(r'data-show-id=["\']*(SH\d+)', webpage, 'show id')
                videos = self._extract_videos(brand, show_id=show_id)
                show_title = self._search_regex(r'data-show-title="([^"]+)"', webpage, 'show title', fatal=False)
                entries = []
                for video in videos:
                    entries.append(self.url_result(
                        video['url'], 'Go', video.get('id'), video.get('title')))
                entries.reverse()
                return self.playlist_result(entries, show_id, show_title)
        video_data = video_data or self._extract_videos(brand, video_id)[0]
        video_id = video_data['id']
        title = video_data['title']

        if not site_info['requestor_id']:
            for sub_domain in ['watchdisneychannel', 'watchdisneyjunior', 'watchdisneyxd']:
                if self._SITE_INFO[sub_domain]['brand'] == video_data.get('show', {}).get('brand'):
                    site_info['requestor_id'] = self._SITE_INFO[sub_domain]['requestor_id']

        formats = []
        chapters = []
        for asset in video_data.get('assets', {}).get('asset', []):
            asset_url = asset.get('value')
            if not asset_url:
                continue
            format_id = asset.get('format')
            ext = determine_ext(asset_url)
            if ext == 'm3u8':
                video_type = video_data.get('type', 'live' if display_id == 'watch-live' else None)
                data = {
                    'video_id': video_data['id'],
                    'video_type': video_type,
                    'brand': brand,
                    'device': '022',
                }
                if video_data.get('accesslevel') == '1':
                    #requestor_id = None
                    #if site_info['requestor_id'] == 'DisneyJunior':
                    requestor_id = 'DisneyChannels'
                    resource = self._get_mvpd_resource(
                        site_info['requestor_id'], title, video_id, None)
                    auth = self._extract_mvpd_auth(
                        url, video_id, requestor_id or site_info['requestor_id'], resource)
                    data.update({
                        'token': auth,
                        'token_type': 'ap',
                        'adobe_requestor_id': requestor_id,
                    })
                else:
                    self._initialize_geo_bypass({'countries': ['US']})
                entitlement = self._download_json(
                    'https://api.entitlement.watchabc.go.com/vp2/ws-secure/entitlement/2020/authorize.json',
                    video_id, data=urlencode_postdata(data))
                errors = entitlement.get('errors', {}).get('errors', [])
                if errors:
                    for error in errors:
                        if error.get('code') == 1002:
                            self.raise_geo_restricted(
                                error['message'], countries=['US'])
                    error_message = ', '.join([error['message'] for error in errors])
                    raise ExtractorError('%s said: %s' % (self.IE_NAME, error_message), expected=True)
                asset_url += '?' + entitlement['uplynkData']['sessionKey']
                formats.extend(self._extract_m3u8_formats(
                    asset_url, video_id, 'mp4', m3u8_id=format_id or 'hls', fatal=False))
            else:
                f = {
                    'format_id': format_id,
                    'url': asset_url,
                    'ext': ext,
                }
                if re.search(r'(?:/mp4/source/|_source\.mp4)', asset_url):
                    f.update({
                        'format_id': ('%s-' % format_id if format_id else '') + 'SOURCE',
                        'preference': 1,
                    })
                else:
                    mobj = re.search(r'/(\d+)x(\d+)/', asset_url)
                    if mobj:
                        height = int(mobj.group(2))
                        f.update({
                            'format_id': ('%s-' % format_id if format_id else '') + '%dP' % height,
                            'width': int(mobj.group(1)),
                            'height': height,
                        })
                formats.append(f)
            if not chapters and len(video_data.get('cues', {}).get('cue', [])) > 2:
                start_time = None
                for chapter in video_data.get('cues', {}).get('cue', []):
                    end_time = float_or_none(chapter.get('value'), 1000)
                    if start_time is None:
                        start_time = end_time
                        continue
                    chapters.append({
                        'start_time': start_time,
                        'end_time': end_time,
                    })
                    start_time = end_time
        self._sort_formats(formats)

        subtitles = {}
        for cc in video_data.get('closedcaption', {}).get('src', []):
            cc_url = cc.get('value')
            if not cc_url:
                continue
            ext = determine_ext(cc_url)
            if ext == 'xml':
                ext = 'ttml'
            subtitles.setdefault(cc.get('lang'), []).append({
                'url': cc_url,
                'ext': ext,
            })

        thumbnails = []
        for thumbnail in video_data.get('thumbnails', {}).get('thumbnail', []):
            thumbnail_url = thumbnail.get('value')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(thumbnail.get('width')),
                'height': int_or_none(thumbnail.get('height')),
            })

        return {
            'id': video_id,
            'title': title,
            'description': video_data.get('longdescription') or video_data.get('description'),
            'duration': float_or_none(video_data.get('duration', {}).get('value'), 1000),
            'age_limit': parse_age_limit(video_data.get('tvrating', {}).get('rating')),
            'episode_number': int_or_none(video_data.get('episodenumber')),
            'release_date': unified_strdate(video_data.get('availdate')),
            'series': video_data.get('show', {}).get('title'),
            'season_number': int_or_none(video_data.get('season', {}).get('num')),
            'thumbnails': thumbnails,
            'formats': formats,
            'chapters': chapters,
            'subtitles': subtitles,
        }
