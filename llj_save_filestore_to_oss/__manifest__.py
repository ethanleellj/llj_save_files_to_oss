{
    "name": "LLJ Save Filestore To OSS / 文件存储到阿里云OSS",
    "version": "19.0.1.0.0",
    "summary": "Use Alibaba Cloud OSS as the ir.attachment storage backend. / 将阿里云OSS作为ir.attachment的存储后端。",
    "description": """
LLJ Save Filestore To OSS / 文件存储到阿里云OSS
================================================

[English]
Turns Alibaba Cloud OSS into the storage backend for ``ir.attachment``.

Features:
* Reads/writes/deletes of attachment binary content go through OSS instead of
  the local filestore when the backend is enabled (``llj_oss.enabled``).
* Files are stored in the bucket under ``[database_name]/[store_fname]`` so
  several databases can share the same bucket without colliding.
* A migration wizard walks the existing local filestore and uploads every
  file to OSS, preserving the same relative path (and therefore the same
  ``store_fname`` reference), then optionally switches reads to OSS.
* Compatible with ``llj_save_product_file_with_id_code``: when both modules
  are installed, product attachments are stored on OSS under
  ``[database]/products/[llj_id_code]/[name]``.
* Auto-detects image format from binary content and appends the correct file
  extension (e.g., .jpg, .png) to ensure files are viewable directly from OSS.
* Provides direct OSS URL access for product attachments via ``llj_oss_url``
  field, supporting CDN domain configuration.

Requirements:
* Requires the ``oss2`` python package (``pip install oss2``).

[中文]
将阿里云OSS作为 ``ir.attachment`` 的存储后端。

功能特点：
* 启用后端（设置 ``llj_oss.enabled``）后，附件二进制内容的读取/写入/删除操作
  通过OSS进行，而非本地文件存储。
* 文件在存储桶中按 ``[数据库名]/[store_fname]`` 路径存储，多个数据库可共享
  同一存储桶而不发生冲突。
* 迁移向导可遍历现有本地文件存储并将所有文件上传到OSS，保持相同的相对路径
  （因此也保持相同的 ``store_fname`` 引用），然后可选择切换读取到OSS。
* 与 ``llj_save_product_file_with_id_code`` 模块兼容：当两个模块都安装时，
  商品附件存储在OSS的 ``[数据库]/products/[编号]/[文件名]`` 路径下。
* 自动从二进制内容检测图片格式并追加正确的文件扩展名（如 .jpg、.png），
  确保文件可直接从OSS查看。
* 通过 ``llj_oss_url`` 字段提供商品附件的直接OSS URL访问，支持CDN域名配置。

依赖要求：
* 需要安装 ``oss2`` Python包（``pip install oss2``）。
""",
    "author": "LLJ",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "category": "Technical/Storage",
    "depends": ["base"],
    "data": [
        "security/ir.model.access.csv",
        "wizards/oss_migrate_wizard_views.xml",
        "views/res_config_settings_views.xml",
        "views/ir_attachment_views.xml",
    ],
    "installable": True,
    "application": False,
    "auto_install": False,
}
