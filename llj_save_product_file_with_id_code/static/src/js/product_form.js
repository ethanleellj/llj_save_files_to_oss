/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";
import { onMounted, onPatched } from "@odoo/owl";

patch(FormController.prototype, {
    setup() {
        super.setup();
        this._lljInterceptorsBound = false;
        this._lljOnClickInterceptor = this._lljOnClickInterceptor.bind(this);
        onMounted(() => {
            this._lljUpdateUploadBlocks();
        });
        onPatched(() => {
            this._lljUpdateUploadBlocks();
        });
    },

    _lljUpdateUploadBlocks() {
        const el = this.rootRef?.el;
        if (!el) return;

        const record = this.model.root;
        if (
            record.resModel !== "product.template" &&
            record.resModel !== "product.product"
        ) {
            return;
        }

        const idCode = record.data.llj_id_code;
        const shouldBlock = !idCode;

        if (shouldBlock && !this._lljInterceptorsBound) {
            el.addEventListener("click", this._lljOnClickInterceptor, true);
            this._lljInterceptorsBound = true;
        } else if (!shouldBlock && this._lljInterceptorsBound) {
            el.removeEventListener("click", this._lljOnClickInterceptor, true);
            this._lljInterceptorsBound = false;
        }

        this._lljUpdateButtonStates(shouldBlock);
    },

    _lljUpdateButtonStates(shouldBlock) {
        const el = this.rootRef?.el;
        if (!el) return;

        const imageEditButtons = el.querySelectorAll(
            ".o_field_image .o_form_image_controls button, .o_field_image .o_field_image_edit"
        );
        imageEditButtons.forEach((btn) => {
            if (shouldBlock) {
                btn.disabled = true;
                btn.style.opacity = "0.5";
                btn.style.cursor = "not-allowed";
                btn.title = "Please set the ID Code and save the product first";
            } else {
                btn.disabled = false;
                btn.style.opacity = "";
                btn.style.cursor = "";
                btn.title = "";
            }
        });

        const attachButtons = el.querySelectorAll(
            '.o_Composer_buttonAttachFiles, button[title="Attach files"], .o_Chatter_composer .fa-paperclip, .o-mail-Composer-attachFiles, button i.fa-paperclip'
        );
        attachButtons.forEach((btn) => {
            const button = btn.closest("button") || btn;
            if (shouldBlock) {
                button.disabled = true;
                button.style.opacity = "0.5";
                button.style.cursor = "not-allowed";
                if (button.tagName === "BUTTON") {
                    button.title = "Please set the ID Code and save the product first";
                }
            } else {
                button.disabled = false;
                button.style.opacity = "";
                button.style.cursor = "";
                if (button.tagName === "BUTTON") {
                    button.title = "";
                }
            }
        });
    },

    _lljOnClickInterceptor(ev) {
        const record = this.model.root;
        if (
            record.resModel !== "product.template" &&
            record.resModel !== "product.product"
        ) {
            return;
        }

        const idCode = record.data.llj_id_code;
        if (idCode) return;

        const target = ev.target;

        const isImageEdit =
            target.closest(".o_field_image .o_form_image_controls button") ||
            target.closest(".o_field_image .o_field_image_edit") ||
            target.closest(".o_field_image .fa-pencil");

        const isAttachFile =
            target.closest(".o_Composer_buttonAttachFiles") ||
            target.closest('button[title="Attach files"]') ||
            target.closest(".o_Chatter_composer .fa-paperclip") ||
            target.closest(".o-mail-Composer-attachFiles") ||
            target.closest("button i.fa-paperclip");

        if (isImageEdit || isAttachFile) {
            ev.preventDefault();
            ev.stopPropagation();
            const msg =
                "Please set the ID Code and save the product first, then upload images or attachments.";
            window.alert(msg);
            return false;
        }
    },
});
