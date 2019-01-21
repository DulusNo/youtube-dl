# coding: utf-8
from __future__ import unicode_literals

import re
import codecs

from .turner import TurnerBaseIE

from ..utils import (
    str_or_none,
    int_or_none,
)

class TruTVIE(TurnerBaseIE):
    _VALID_URL = r'https?://(?:www\.)?trutv\.com/(?:shows|full-episodes)/(?P<slug>[^/]+)/(?P<id>videos|\d+)/(?P<title>[\w-]+)\.html'
    _TEST = {
        'url': 'http://www.trutv.com/shows/10-things/videos/you-wont-believe-these-sports-bets.html',
        'md5': '2cdc844f317579fed1a7251b087ff417',
        'info_dict': {
            'id': '/shows/10-things/videos/you-wont-believe-these-sports-bets',
            'ext': 'mp4',
            'title': 'You Won\'t Believe These Sports Bets',
            'description': 'Jamie Lee sits down with a bookie to discuss the bizarre world of illegal sports betting.',
            'upload_date': '20130305',
        }
    }

    def _real_extract(self, url):
        slug, video_id, title = re.match(self._VALID_URL, url).groups()
        auth_required = False
        info = {}
        initial_data = {}
        if video_id == 'videos':
            initial_data = self._download_json(
                'https://api.trutv.com/v2/web/series/clip/%s/%s' % (slug, title),
                title).get('info', {})
            video_id = initial_data.get('slug') or title
            series = initial_data.get('series', {}).get('title')
        else:
            initial_data = self._download_json(
                'https://api.trutv.com/v2/web/episode/%s/%s' % (slug, video_id),
                video_id).get('episode', {})
            video_id = initial_data.get('titleId') or video_id
            auth_required = initial_data.get('isAuthRequired')
            series = initial_data.get('showTitle')

        media_id = initial_data.get('mediaId')
        title = initial_data.get('title')

        formats = info.pop('formats', [])
        info.update(self._extract_ngtv_info(
            media_id, None, {
                'url': url,
                'site_name': 'truTV',
                'auth_required': auth_required,
            }))
        formats.extend(info.pop('formats', []))
        self._sort_formats(formats)

        thumbnails = []
        for thumbnail in initial_data.get('images', []):
            thumbnail_url = thumbnail.get('srcUrl')
            if not thumbnail_url:
                continue
            thumbnails.append({
                'url': thumbnail_url,
                'width': int_or_none(thumbnail.get('width')),
                'height': int_or_none(thumbnail.get('height')),
            })

        info.update({
            'formats': formats,
            'title': info.get('title') or str_or_none(title),
            'description': info.get('description') or str_or_none(initial_data.get('description')),
            'series': info.get('series') or str_or_none(series),
            'season_number': info.get('season_number') or int_or_none(initial_data.get('seasonNum')),
            'episode_number': info.get('episode_number') or int_or_none(initial_data.get('episodeNum')),
            'thumbnails': thumbnails,
        })

        return info

