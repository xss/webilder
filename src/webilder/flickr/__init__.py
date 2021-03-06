'''
File    : __init__.py
Author  : Nadav Samet
Contact : thesamet@gmail.com
Date    : 2010 Jun 17

Description : Webilder flickr plugin package
'''

from webilder.flickr import flickrapi
import re
import urllib2
from datetime import date
from PIL import Image
import cStringIO
import gc

API_KEY = '045379bc5368502f749af23d95a17c83'

flickr = flickrapi.FlickrProxy(api_key = API_KEY)  # pylint: disable=C0103

def get_download_list(config):
    """Get list of photos to download."""
    if not config.get('flickr.enabled'):
        return []
    rules = config.get('flickr.rules')
    images = []
    all_photos = []
    for rule in rules:
        if not rule.get('enabled', True):
            continue
        sort_method = rule.get('sort', 'Interestingness')
        sort_method = {'Interestingness': 'interestingness-desc',
                       'Date': 'date-posted-desc'}[sort_method]

        for tag_term in rule['tags'].split(';'):
            tag_term = ','.join([tag.strip() for tag in tag_term.split(',')])
            params_dict = dict(per_page=20, sort=sort_method,
                               extras='original_format')
            if tag_term:
                params_dict['tags'] = tag_term
                params_dict['tag_mode'] = 'all'

            user_id = rule['user_id'].strip()
            if user_id:
                if 'nsid' not in rule:
                    rule['nsid'] = flickr.get_user_nsid(user_id)
                    config.save_config()
                params_dict['user_id'] = rule['nsid']

            photos = flickr.photos_search(**params_dict) # pylint: disable=W0142
            for photo in photos:
                photo._album = rule['album']
            all_photos.extend(photos)

    if config.get('flickr.download_interesting'):
        photos = flickr.interestingness_search(per_page=20,
                                               extras='original_format')
        for photo in photos:
            photo._album = 'Interestingness - '+date.today().strftime('%B %Y')
        all_photos.extend(photos)

    for photo in all_photos:
        title = photo.title
        photo_id = str(photo.photo_id)
        images.append({
            'name': 'flickr_%s.jpg' % photo_id,
            'title': title,
            'data': {
                'photo': photo,
                'album': photo._album,
            }})
    return images

def fetch_photo_info(config, photo):
    """Get photo info."""
    photo_obj = photo['data']['photo']
    photo['data']['info'] = photo_obj.get_info()
    photo['data']['sizes'] = photo_obj.get_sizes()
    if config.get('filter.only_landscape'):
        photo['data']['aspect_ratio'] = photo_obj.get_aspect_ratio()

def get_photo_stream(_config, photo):
    """Starts downloading the given photo."""
    request = urllib2.Request(photo['data']['info']['image_url'])
    opener = urllib2.build_opener()
    return opener.open(request)

def process_photo(config, photo, fileobj):
    """Process the photo and save it in the collection."""
    info = photo['data']['info']
    metadata = {
            'albumTitle': photo['data']['album'],
            'title': info['title'],
            'credit': info['owner'],
            'url': info['url'],
            'tags': ' '.join(info['tags'])
            }

    data = fileobj.read()
    if config.get('flickr.scale_down'):
        scale_size = config.get('flickr.scale_down')
        image = Image.open(cStringIO.StringIO(data))
        size = image.size
        if size[0] > scale_size[0] or size[1] > scale_size[1]:
            image.thumbnail(scale_size, Image.ANTIALIAS)
            data = image.tostring('jpeg', image.mode)

    gc.collect()
    return data, metadata
