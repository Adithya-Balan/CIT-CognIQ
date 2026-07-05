from storages.backends.s3 import S3Storage

    
class MediaFileStorage(S3Storage):
    # helpers.cloudflare.storages.MediaFileStorage
    location = "media"
    