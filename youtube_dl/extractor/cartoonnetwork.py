# coding: utf-8
from __future__ import unicode_literals

import re

from .turner import TurnerBaseIE
from ..utils import (
    float_or_none,
    int_or_none,
    str_or_none,
)


class CartoonNetworkIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?cartoonnetwork\.com/video/(?:[^/]+/)+(?P<id>[^/?#]+)-(?:clip|episode)\.html'
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
        display_id = self._match_id(url)
        webpage = self._download_webpage(url, display_id)
        id_type, video_id = re.search(r"_cnglobal\.cvp(Video|Title)Id\s*=\s*'([^']+)';", webpage).groups()
        video_data = self._download_json(
            'https://video-api.cartoonnetwork.com/getepisode/'+ video_id,
            video_id,'Downloading JSON with video information', headers = {
                'accept': 'www.cartoonnetwork.com+json; version=3',
                'authentication': 'cngoapi',
                })[0]
        media_id = video_data.get('mediaid')
        title = video_data.get('title')

        info = self._extract_ngtv_info(
            media_id, None, {
                'url': url,
                'site_name': 'CartoonNetwork',
                'auth_required': video_data.get('authtype') == 'auth',
            })

        info.update({
            'title': str_or_none(title),
            'description': str_or_none(video_data.get('description')),
            'timestamp': float_or_none(video_data.get('pubdateasmilliseconds'), 1000),
            'series': str_or_none(video_data.get('seriesname')),
            'season_number': int_or_none(video_data.get('seasonnumber')),
            'episode_number': int_or_none(video_data.get('episodenumber')),
            'thumbnail': video_data.get('thumbnailurl'),
        })

        return info
