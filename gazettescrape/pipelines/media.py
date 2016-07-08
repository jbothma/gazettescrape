"""
Override MediaPipeline to set request.meta['handle_httpstatus_all'] = True
"""

import scrapy.pipelines.media
from scrapy.utils.defer import mustbe_deferred


class MediaPipeline(scrapy.pipelines.media.MediaPipeline):
    def _check_media_to_download(self, result, request, info):
        if result is not None:
            return result
        if self.download_func:
            # this ugly code was left only to support tests. TODO: remove
            dfd = mustbe_deferred(self.download_func, request, info.spider)
            dfd.addCallbacks(
                callback=self.media_downloaded, callbackArgs=(request, info),
                errback=self.media_failed, errbackArgs=(request, info))
        else:
            request.meta['handle_httpstatus_all'] = False
            dfd = self.crawler.engine.download(request, info.spider)
            dfd.addCallbacks(
                callback=self.media_downloaded, callbackArgs=(request, info),
                errback=self.media_failed, errbackArgs=(request, info))
        return dfd
