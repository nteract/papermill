"""Utilities for working with Azure blob storage"""
import io
import re

from azure.identity import EnvironmentCredential
from azure.storage.blob import BlobServiceClient


class AzureBlobStore:
    """
    Represents a Blob of storage on Azure

    Methods
    -------
    The following are wrapped utilities for Azure storage:
        - read
        - listdir
        - write
    """

    def _blob_service_client(self, account_name, sas_token=None):
        blob_service_client = BlobServiceClient(
            account_url=f"{account_name}.blob.core.windows.net",
            credential=sas_token or EnvironmentCredential(),
        )

        return blob_service_client

    @classmethod
    def _split_url(self, url):
        """
        see: https://docs.microsoft.com/en-us/azure/storage/common/storage-dotnet-shared-access-signature-part-1
        abs://myaccount.blob.core.windows.net/sascontainer/sasblob.txt?sastoken
        """
        match = re.match(r"abs://(.*)\.blob\.core\.windows\.net\/(.*?)\/([^\?]*)\??(.*)$", url)
        if not match:
            raise Exception(f"Invalid azure blob url '{url}'")
        else:
            params = {
                "account": match.group(1),
                "container": match.group(2),
                "blob": match.group(3),
                "sas_token": match.group(4),
            }
            return params

    def read(self, url):
        """Read storage at a given url"""
        params = self._split_url(url)
        output_stream = io.BytesIO()
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        blob_client = blob_service_client.get_blob_client(params['container'], params['blob'])
        blob_client.download_blob().readinto(output_stream)
        output_stream.seek(0)
        return [line.decode("utf-8") for line in output_stream]

    def listdir(self, url):
        """Returns a list of the files under the specified path"""
        params = self._split_url(url)
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        container_client = blob_service_client.get_container_client(params["container"])
        return list(container_client.list_blobs(params["blob"]))

    def write(self, buf, url):
        """Write buffer to storage at a given url"""
        params = self._split_url(url)
        blob_service_client = self._blob_service_client(params["account"], params["sas_token"])
        blob_client = blob_service_client.get_blob_client(params['container'], params['blob'])
        blob_client.upload_blob(data=buf, overwrite=True)
