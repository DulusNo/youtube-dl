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
    _VALID_URL = r'https?://(?:www\.)?trutv\.com(?:(?P<path>/shows/[^/]+/videos/[^/?#]+?)\.html|/full-episodes/[^/]+/(?P<id>\d+))'
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
        path, video_id = re.match(self._VALID_URL, url).groups()
        auth_required = False
        webpage = self._download_webpage(url, video_id or path)
        info = {}
        initial_data = {}
        if path:
            data_src = 'http://www.trutv.com/video/cvp/v2/xml/content.xml?id=%s.xml' % path
            info = self._extract_cvp_info(
                data_src, path, {
                    'default': {
                        'media_src': 'http:',
                    },
                })
            media_id = self._search_regex(
                r"TTV\.video\.clip\.mediaId\s*=\s*'([^']+)';",
                webpage, 'media id', default=None)
        else:
            raw_data = self._html_search_regex(
                r"TTV\.TVE\.analytics\s*=\s*'([^']+)';",
                webpage, 'initial data')
            initial_data = self._parse_json(codecs.decode(raw_data.encode(), 'unicode_escape'), video_id)
            video_id = initial_data.get('id') or self._search_regex(
                r"TTV\.TVE\.episodeId\s*=\s*'([^']+)';",
                webpage, 'video id', default=video_id)
            auth_required = self._search_regex(
                r'TTV\.TVE\.authRequired\s*=\s*(true|false);',
                webpage, 'auth required', default='false') == 'true'
            media_id = initial_data.get('mediaId') or self._search_regex(
                r"TTV\.TVE\.mediaId\s*=\s*'([^']+)';",
                webpage, 'media id', default=None)
            title = initial_data.get('title') or self._search_regex(
                r"<div\s+class\s*=\s*\"clip-title\"[^>]*>([^<]*)</div>",
                webpage, 'title', default=video_id)

        formats = info.pop('formats', [])
        info.update(self._extract_ngtv_info(
            media_id, None, {
                'url': url,
                'site_name': 'truTV',
                'auth_required': auth_required,
            }))
        formats.extend(info.pop('formats', []))
        self._sort_formats(formats)

        info.update({
            'formats': formats,
            'title': info.get('title') or str_or_none(title),
            'description': info.get('description') or str_or_none(initial_data.get('description')),
            'series': info.get('series') or str_or_none(initial_data.get('franchise')),
            'season_number': info.get('season_number') or int_or_none(initial_data.get('seasonNumber')),
            'episode_number': info.get('episode_number') or int_or_none(initial_data.get('episodeNumber')),
        })

        return info

