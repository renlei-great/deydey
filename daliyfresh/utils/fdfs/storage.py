from  django.core.files.storage import Storage
from daliyfresh import settings
from fdfs_client.client import Fdfs_client


class FDFSStorage(Storage):
    """fast dfs文件存储类"""
    def __init__(self, client_conf = None, base_url = None):
        """初始化client配置文件地址和nginx网址"""

        if client_conf is None:
            client_conf = settings.FDFS_CLIENT_CONF
        if base_url is None:
            base_url = settings.FDFS_UTL
        self.client_conf = client_conf
        self.base_url = base_url

    def _open(self, name, mode='rb'):
        """打开文件时使用"""
        pass

    def _save(self, name, content):
        """保存文件时使用"""
        # name：你选择的上传文件的名字
        # content：包含你上传文件内容的file对象
        # 创建一个Fdfs_client对象
        client = Fdfs_client(self.client_conf)

        # 上传文件到fast dfs系统中
        res = client.upload_by_buffer(content.read())

        # 获取上传状态
        # dict
        # {
        #     'Group name': group_name,
        #     'Remote file_id': remote_file_id,
        #     'Status': 'Upload successed.',
        #     'Local file name': '',
        #     'Uploaded size': upload_size,
        #     'Storage IP': storage_ip
        #  }
        # print(res.get('Status'))

        if res.get('Status') != 'Upload successed.':
            raise Exception('上传文件失败')

        # # 获取上传文件成功后的id名
        res_id = res.get('Remote file_id')

        return res_id

    def exists(self, name):
        """判断django中文件名是否存在"""
        return False

    def url(self, name):
        """返回访问文件的url路径"""
        return self.base_url + name