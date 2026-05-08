# -*- coding: utf-8 -*-
import logging
import requests

from odoo import fields, models, _
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models"
    "/gemini-2.5-flash-image:generateContent"
)

GEMINI_PROMPT = (
    "You are an expert product photo editor. "
    "Extract the main product from the provided image precisely. "
    "Remove all background elements and replace them with a solid pure white (#FFFFFF) background. "
    "Preserve the original product's exact shape, texture, color, and lighting. "
    "DO NOT add any new details, hallucinate, or modify the product itself. "
    "Output ONLY the final edited image."
)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def _ensure_quota_fresh(self):
        ICP = self.env['ir.config_parameter'].sudo()
        today = fields.Date.context_today(self).isoformat()
        last = ICP.get_param('andykanoz_gemini_integration_auto_edit.quota_date', '')
        if last != today:
            ICP.set_param('andykanoz_gemini_integration_auto_edit.quota_date', today)
            ICP.set_param('andykanoz_gemini_integration_auto_edit.quota_used', '0')

    def _increment_quota(self):
        ICP = self.env['ir.config_parameter'].sudo()
        self._ensure_quota_fresh()
        used = int(ICP.get_param('andykanoz_gemini_integration_auto_edit.quota_used', '0') or '0')
        ICP.set_param('andykanoz_gemini_integration_auto_edit.quota_used', str(used + 1))

    def _gemini_remove_white_bg(
        self,
        image_b64,
        preset_override=None,
        custom_prompt_override=None,
        output_format_override=None,
        refine_edges_override=None,
        preserve_shadows_override=None,
        max_dimension_override=None,
    ):
        """Call Gemini API to replace background or perform auto-edit.

        Optional override arguments allow callers (buttons/actions) to force
        a specific preset or output format without changing system settings.

        Returns: new image as base64 ascii bytes (ready for image_1920).
        Raises: UserError on any failure.
        """
        self.ensure_one()

        ICP = self.env['ir.config_parameter'].sudo()
        api_key = ICP.get_param('andykanoz_gemini_integration_auto_edit.gemini_api_key', '')
        if not api_key:
            raise UserError(_(
                "Gemini API key is not configured.\n"
                "Go to Settings → General Settings → Integrations → Gemini AI (Auto Edit)."
            ))

        # Read editor settings (stored as config params) unless overridden
        preset = preset_override or ICP.get_param('andykanoz_gemini_integration_auto_edit.preset', 'default') or 'default'
        custom_prompt = custom_prompt_override or ICP.get_param('andykanoz_gemini_integration_auto_edit.custom_prompt', '') or ''
        output_format = (output_format_override or ICP.get_param('andykanoz_gemini_integration_auto_edit.output_format', 'jpeg') or 'jpeg')
        if refine_edges_override is None:
            refine_edges = str(ICP.get_param('andykanoz_gemini_integration_auto_edit.refine_edges', 'False')).lower() in ('1', 'true', 'yes')
        else:
            refine_edges = bool(refine_edges_override)
        if preserve_shadows_override is None:
            preserve_shadows = str(ICP.get_param('andykanoz_gemini_integration_auto_edit.preserve_shadows', 'True')).lower() in ('1', 'true', 'yes')
        else:
            preserve_shadows = bool(preserve_shadows_override)

        # Build prompt based on selected preset
        if preset == 'default':
            prompt_text = GEMINI_PROMPT
        elif preset == 'refine_white':
            prompt_text = (
                "You are an expert product photo editor. Remove the background and replace it with a solid pure white (#FFFFFF) background. "
                "Remove any visible hands or occluding objects if present. Preserve the product's exact shape, color, texture, and natural lighting. "
                "Refine the cutout edges to avoid halos and produce a crisp silhouette. Output ONLY the final edited image."
            )
        elif preset == 'transparent':
            prompt_text = (
                "You are an expert product photo editor. Extract the main product from the provided image precisely. "
                "Remove all background elements and output a PNG image with a transparent background (alpha channel). "
                "Preserve product shape, texture, color, and natural lighting. Output ONLY the final edited PNG image with transparency."
            )
        elif preset == 'remove_hands':
            prompt_text = (
                "You are an expert product photo editor. Extract the main product and remove any human hands, fingers, or occlusions holding or touching the product. "
                "Preserve the product's shape, texture, color, and natural shadows. Output ONLY the final edited image with a pure white background (#FFFFFF)."
            )
        elif preset == 'custom' and custom_prompt.strip():
            prompt_text = custom_prompt
        else:
            prompt_text = GEMINI_PROMPT

        # Append optional modifiers if not already present
        if refine_edges and 'refine' not in prompt_text.lower():
            prompt_text += " Refine cutout edges and avoid halos; produce a crisp result."
        if preserve_shadows and 'shadow' not in prompt_text.lower():
            prompt_text += " Preserve natural shadows and subtle reflections to maintain a realistic look."

        # Choose mime type according to desired output format
        mime_type = 'image/png' if str(output_format).lower() == 'png' else 'image/jpeg'

        # Optional preprocessing: resize/convert image locally to reduce API upload size/cost.
        processed_b64 = image_b64

        # Determine max dimension (override has priority)
        if max_dimension_override is not None:
            try:
                max_dim = int(max_dimension_override) if int(max_dimension_override) > 0 else 0
            except Exception:
                max_dim = 0
        else:
            try:
                max_dim = int(ICP.get_param('andykanoz_gemini_integration_auto_edit.max_dimension', '0') or '0')
            except Exception:
                max_dim = 0

        if max_dim and max_dim > 0:
            try:
                import base64
                import io
                from PIL import Image

                decoded = base64.b64decode(image_b64)
                img = Image.open(io.BytesIO(decoded))
                img.load()
                w, h = img.size
                max_side = max(w, h)
                if max_side > max_dim:
                    scale = float(max_dim) / float(max_side)
                    new_size = (max(1, int(w * scale)), max(1, int(h * scale)))
                    img = img.resize(new_size, Image.LANCZOS)

                # Convert for requested output format
                buf = io.BytesIO()
                if mime_type == 'image/png':
                    # Preserve alpha when saving PNG
                    if img.mode == 'P':
                        img = img.convert('RGBA')
                    img.save(buf, format='PNG', optimize=True)
                else:
                    # JPEG: ensure RGB and composite alpha over white if necessary
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in getattr(img, 'info', {})):
                        alpha = img.convert('RGBA').split()[-1]
                        from PIL import Image as _Image
                        bg = _Image.new('RGB', img.size, (255, 255, 255))
                        bg.paste(img.convert('RGBA'), mask=alpha)
                        out_img = bg
                    else:
                        out_img = img.convert('RGB')
                    out_img.save(buf, format='JPEG', quality=90, optimize=True)

                buf.seek(0)
                import base64 as _b64
                processed_b64 = _b64.b64encode(buf.read()).decode('ascii')
                _logger.info(
                    "Auto Edit — Preprocessed image for product %s (%sx%s -> %s)",
                    self.id, w, h, img.size,
                )
            except ImportError:
                _logger.info("Auto Edit — Pillow not installed, skipping preprocessing/resizing")
            except Exception:
                _logger.exception("Auto Edit — Preprocessing failed, sending original image")

        payload = {
            "contents": [{
                "parts": [
                    {"text": prompt_text},
                    {
                        "inlineData": {
                            "mimeType": mime_type,
                            "data": processed_b64,
                        }
                    },
                ]
            }],
            "generationConfig": {
                "responseModalities": ["IMAGE"],
            },
        }

        _logger.info("Auto Edit — Sending image to Gemini API for product %s", self.id)

        try:
            resp = requests.post(
                GEMINI_API_URL,
                params={"key": api_key},
                json=payload,
                timeout=120,
            )
            resp.raise_for_status()
        except requests.exceptions.Timeout:
            raise UserError(_("Gemini API request timed out. Please try again."))
        except requests.exceptions.RequestException as e:
            _logger.exception("Auto Edit — Gemini API request failed")
            raise UserError(_("Gemini API request failed: %s") % str(e))

        result = resp.json()

        if "error" in result:
            msg = result["error"].get("message", str(result["error"]))
            raise UserError(_("Gemini API error: %s") % msg)

        candidates = result.get("candidates", [])
        if not candidates:
            raise UserError(_("Gemini API returned no result."))

        parts = candidates[0].get("content", {}).get("parts", [])
        for part in parts:
            inline_data = part.get("inline_data") or part.get("inlineData")
            if inline_data and inline_data.get("data"):
                new_image_b64 = inline_data["data"]
                self._increment_quota()
                _logger.info("Auto Edit — Done for product %s", self.id)
                return new_image_b64.encode('ascii')

        raise UserError(_("Gemini API did not return an image. Please try again."))

    def action_auto_white_background(self):
        """Single-product button — remove background using Gemini AI."""
        self.ensure_one()
        if not self.image_1920:
            raise UserError(_("This product has no image."))
        new_b64 = self._gemini_remove_white_bg(self.image_1920.decode('ascii'))
        self.write({'image_1920': new_b64})
        return True

    def action_auto_professional_edit(self):
        """Single-product button — run a professional preset (remove hands + refine).

        This method forces a stronger preset without changing global settings.
        """
        self.ensure_one()
        if not self.image_1920:
            raise UserError(_("This product has no image."))

        new_b64 = self._gemini_remove_white_bg(
            self.image_1920.decode('ascii'),
            preset_override='remove_hands',
            refine_edges_override=True,
            preserve_shadows_override=True,
            output_format_override='jpeg',
        )
        self.write({'image_1920': new_b64})
        return True
