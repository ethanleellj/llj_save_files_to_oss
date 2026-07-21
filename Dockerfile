FROM odoo:19

USER root

RUN pip install oss2

USER odoo