{
    "name": "LLJ Save Product File With ID Code / 商品档案按编号存储",
    "version": "19.0.1.1.0",
    "summary": "Store product attachments under /products/[llj_id_code]/ instead of the default hash folders. / 将商品附件存储在 /products/[编号]/ 目录下，替代默认的哈希目录结构。",
    "description": """
LLJ Save Product File With ID Code / 商品档案按编号存储
========================================================

[English]
Adds a unique `llj_id_code` text field on product.template and rewrites the
attachment storage path for product attachments.

Instead of the default filestore/[db]/[sha[:2]]/[sha] layout, product images
and attachments are stored under filestore/[db]/products/[llj_id_code]/[name].

Features:
* Forbids uploading any attachment on a product without an ID Code (backend validation).
* When the ID Code is changed, the physical folder is renamed and the
  ir.attachment.store_fname references are updated accordingly.
* Only product.template / product.product attachments are affected. Every
  other model keeps using Odoo's default storage logic.
* Frontend: Disables "Edit Image" and "Attach files" buttons when ID Code is empty,
  providing visual feedback (greyed-out appearance, not-allowed cursor, tooltip).
* Frontend: Intercepts clicks on disabled buttons and shows an informative alert message.
* Auto-detects image format and appends the correct file extension (e.g. .jpg, .png)
  based on binary content analysis.
* Original high-resolution image: New `llj_image_original` field stores the
  uncompressed original image directly to OSS, preserving full quality and original filename.
* Works alongside the llj_save_filestore_to_oss module through context-based
  path convention propagation.

[中文]
在 product.template 上添加唯一的 `llj_id_code` 文本字段，并重写商品附件的存储路径。
与默认的 filestore/[db]/[sha[:2]]/[sha] 布局不同，商品图片和附件存储在
filestore/[db]/products/[编号]/[文件名] 目录下。

功能特点：
* 禁止在没有编号的商品上上传附件（后端验证）。
* 当编号变更时，自动重命名物理文件夹并更新 ir.attachment.store_fname 引用。
* 仅影响 product.template / product.product 的附件，其他模型保持 Odoo 默认存储逻辑。
* 前端：当 ID Code 为空时，禁用"编辑图片"和"Attach files"按钮，
  提供视觉反馈（灰色外观、禁止光标、悬停提示）。
* 前端：拦截禁用按钮的点击事件，显示友好的提示信息。
* 自动检测图片格式，根据二进制内容分析追加正确的文件扩展名（如 .jpg、.png）。
* 原始高清图：新增 `llj_image_original` 字段，直接将未压缩的原始图片存储到 OSS，
  完整保留图片质量和原始文件名，可通过 OSS URL 直接访问。
* 通过上下文路径约定与 llj_save_filestore_to_oss 模块协作。

Module Structure:
-----------------
* models/product_template.py: Adds llj_id_code field, validates image updates,
  handles folder renaming on code change. Includes llj_image_original field
  for storing uncompressed original images with proper extension detection.
* models/product_product.py: Validates variant image updates against template ID Code.
* models/ir_attachment.py: Overrides _get_path and _file_write to implement
  custom storage layout, ID Code validation, and automatic image extension detection.
* views/product_template_views.xml: Adds llj_id_code field and llj_image_original
  field (with filename and OSS URL display) to product form and search views.
* static/src/js/product_form.js: Patches FormController to intercept and
  disable image/attachment buttons when ID Code is empty.
""",
    "author": "LLJ",
    "website": "https://www.odoo.com",
    "license": "LGPL-3",
    "category": "Technical/Storage",
    "depends": ["product", "base"],
    "data": [
        "views/product_template_views.xml",
    ],
    "assets": {
        "web.assets_backend": [
            "llj_save_product_file_with_id_code/static/src/js/product_form.js",
        ],
    },
    "installable": True,
    "application": False,
    "auto_install": False,
}
