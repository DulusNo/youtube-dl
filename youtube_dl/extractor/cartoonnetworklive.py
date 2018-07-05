# coding: utf-8
from __future__ import unicode_literals

import re

from .turner import TurnerBaseIE
from ..utils import (
    float_or_none,
    parse_duration,
    xpath_text,
    xpath_attr,
    int_or_none,
    strip_or_none,
    str_or_none,
)


class CartoonNetworkLiveIE(TurnerBaseIE):
    # _VALID_URL = r'https?://(?:www\.)?cartoonnetwork\.com/video/(?:[^/]+/)+(?P<id>[^/?#]+)-(?:clip|episode)\.html'
    _VALID_URL = r"https?://(?:www\.)?cartoonnetwork\.com/livetv(?:/(pacific))?/index\.html"
    _TEST = {
        'url': 'http://www.cartoonnetwork.com/video/teen-titans-go/starfire-the-cat-lady-clip.html',
        'info_dict': {
            'id': '8a250ab04ed07e6c014ef3f1e2f9016c',
            'ext': 'mp4',
            'title': 'Starfire the Cat Lady',
            'description': 'Robin decides to become a cat so that Starfire will finally love him.',
        },
        'params': {
            # m3u8 download
            'skip_download': True,
        },
    }

    def _real_extract(self, url):
        display_id = 'livetv'
        webpage = self._download_webpage(url, display_id)
        # id_type, video_id = re.search(r"_cnglobal\.cvp(Video|Title)Id\s*=\s*'([^']+)';", webpage).groups()
        video_id = re.search(r"_cnglobal\.videoMediaId\s*=\s*'([^']+)';", webpage).group(1)
        # video_data = self._download_xml('http://video-api.cartoonnetwork.com/contentXML/' + video_id, video_id)
        # title = self._search_regex(r"<meta\s+property=\"og:title\"\s*content=\"(.*)\"\s*/>", webpage)

        streams_data = self._download_json(
            'http://medium.ngtv.io/media/%s/tv' % video_id,
            video_id)['media']['tv']
        duration = None
        chapters = []
        formats = []
        for supported_type in ('unprotected', 'bulkaes'):
            stream_data = streams_data.get(supported_type, {})
            m3u8_url = stream_data.get('url') or stream_data.get('secureUrl')
            if not m3u8_url:
                continue
            if stream_data.get('playlistProtection') == 'spe':
                m3u8_url = self._add_akamai_spe_token(
                    'http://token.vgtf.net/token/token_spe',
                    m3u8_url, video_id, {
                        'url': url,
                        'site_name': 'CartoonNetwork',
                        'auth_required': True,
                    })
            m3u8_formats = self._extract_m3u8_formats(
                m3u8_url, video_id, 'mp4', 'm3u8_native', m3u8_id='hls', fatal=False)
            if '?hdnea=' in m3u8_url:
                for f in m3u8_formats:
                    f['_seekable'] = False
            formats.extend(m3u8_formats)

            # duration = float_or_none(stream_data.get('totalRuntime') or
            #     parse_duration(xpath_text(video_data, 'length') or
            #     xpath_text(video_data, 'trt')))
            duration = float_or_none(stream_data.get('totalRuntime'))# or video_data.get('duration'))
        self._sort_formats(formats)

        # thumbnails = [{
        #     'id': image.get('cut'),
        #     'url': image.text,
        #     'width': int_or_none(image.get('width')),
        #     'height': int_or_none(image.get('height')),
        # } for image in video_data.findall('images/image')]

        return {
            'id': video_id,
            'title': 'livetv',
            'is_live': True,
            #'description': str_or_none(video_data.get('description')),
            #'duration': duration,
            #'timestamp': float_or_none(int_or_none(video_data.get('pubdateasmilliseconds'))/1000),
            # 'upload_date': xpath_attr(video_data, 'metas', 'version'),
            #'series': str_or_none(video_data.get('seriesname')),
            #'season_number': int_or_none(video_data.get('seasonnumber')),
            #'episode_number': int_or_none(video_data.get('episodenumber')),
            #'chapters': chapters,
            #'thumbnail': video_data.get('thumbnailurl'),
            'formats': formats,
        }
