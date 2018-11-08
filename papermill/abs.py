import re
import io
from six.moves import urllib
from azure.storage.blob import BlockBlobService


class AzureBlobStore(object):
    def __init__(self):
        pass

    def _block_blob_service(self, account_name, sas_token):

        block_blob_service = BlockBlobService(account_name=account_name, sas_token=sas_token)
        return block_blob_service

    @classmethod
    def _split_url(self, url):
        """
        see: https://docs.microsoft.com/en-us/azure/storage/common/storage-dotnet-shared-access-signature-part-1  # noqa: E501
        abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken
        """
        match = re.match(r"abs://(.*)\.blob\.core\.windows\.net\/(.*)\/(.*)\?(.*)$", url)
        if not match:
            raise Exception("Invalid azure blob url '{0}'".format(url))
        else:
            params = {
                "account": match.group(1),
                "container": match.group(2),
                "blob": match.group(3),
                "sas_token": urllib.parse.unquote_plus(match.group(4)),
            }
            return params

    def read(self, url):
        params = self._split_url(url)
        output_stream = io.BytesIO()
        block_blob_service = self._block_blob_service(
            account_name=params["account"], sas_token=params["sas_token"]
        )

        block_blob_service.get_blob_to_stream(
            container_name=params["container"],
            blob_name=params["blob"],
            stream=output_stream,
        )

        output_stream.seek(0)
        return [
            line.decode("utf-8") for line in output_stream
        ]

    def listdir(self, url):
        params = self._split_url(url)

        block_blob_service = self._block_blob_service(
            account_name=params["account"], sas_token=params["sas_token"]
        )
        blobs = block_blob_service.list_blobs(params["container"])
        return blobs

    def write(self, buf, url):
        params = self._split_url(url)

        block_blob_service = self._block_blob_service(
            account_name=params["account"], sas_token=params["sas_token"]
        )

        block_blob_service.create_blob_from_text(
            container_name=params["container"], blob_name=params["blob"], text=buf
        )
