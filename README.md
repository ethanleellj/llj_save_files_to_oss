# LLJ Odoo Modules

两个 Odoo 19 模块，实现商品附件按编号存储到阿里云 OSS 的完整解决方案。

## 模块概述

### 1. llj_save_filestore_to_oss

将阿里云 OSS 作为 `ir.attachment` 的存储后端。

**主要功能：**
- OSS 读写：附件的读取/写入/删除操作通过阿里云 OSS 进行
- 多数据库共享：文件按 `[数据库名]/[store_fname]` 路径存储
- 迁移向导：将现有本地文件存储迁移到 OSS
- 图片扩展名自动检测：根据二进制内容自动追加正确的文件扩展名
- OSS URL 访问：支持 CDN 域名配置，提供直接 URL 访问

### 2. llj_save_product_file_with_id_code

为商品档案添加编号字段，并按编号组织附件存储。

**主要功能：**
- ID Code 字段：在商品模板上添加唯一编号字段 `llj_id_code`
- 附件存储路径：商品附件存储在 `/products/[编号]/[文件名]` 目录下
- 后端验证：禁止在无编号商品上上传附件
- 编号变更处理：自动重命名文件夹并更新附件引用
- 前端按钮禁用：ID Code 为空时禁用"编辑图片"和"Attach files"按钮
- 原始高清图：新增 `llj_image_original` 字段存储未压缩原始图片
- OSS URL 访问：原始高清图可通过 OSS URL 直接访问

## 安装要求

```bash
pip install oss2
```

## 配置

在 Odoo 设置中配置阿里云 OSS 参数：
- `llj_oss.enabled`: 是否启用 OSS 存储（True/False）
- `llj_oss.access_key_id`: Access Key ID
- `llj_oss.access_key_secret`: Access Key Secret
- `llj_oss.endpoint`: OSS Endpoint
- `llj_oss.bucket_name`: Bucket 名称
- `llj_oss.cdn_domain`: CDN 域名（可选）

## 使用流程

1. 安装两个模块
2. 在设置中配置 OSS 参数
3. 打开商品档案，填写 ID Code
4. 保存商品后即可上传图片和附件
5. 上传的图片会自动存储到 OSS，并带有正确的文件扩展名

## 文件结构

```
llj_save_filestore_to_oss/
├── models/
│   ├── ir_attachment.py      # OSS 存储核心逻辑
│   └── res_config_settings.py # OSS 配置参数
├── views/                    # 配置视图
├── wizards/                  # 迁移向导
└── __manifest__.py           # 模块元数据

llj_save_product_file_with_id_code/
├── models/
│   ├── product_template.py   # 商品模板扩展
│   ├── product_product.py    # 商品变体验证
│   └── ir_attachment.py      # 附件存储路径重写
├── views/                    # 商品视图扩展
├── static/src/js/
│   └── product_form.js       # 前端按钮禁用逻辑
└── __manifest__.py           # 模块元数据
```

## 版本

- llj_save_filestore_to_oss: 19.0.1.0.0
- llj_save_product_file_with_id_code: 19.0.1.1.0
