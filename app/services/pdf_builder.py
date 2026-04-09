from __future__ import annotations

import json
import logging
from io import BytesIO
from pathlib import Path
from typing import Any

import httpx
from PIL import Image
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas

from app.utils.page_text import fit_font_size

logger = logging.getLogger(__name__)


class PDFBuilderService:
    def __init__(self) -> None:
        self._font_cache: set[str] = set()

    def load_book_config(self, path: str | Path) -> dict[str, Any]:
        with open(path, 'r', encoding='utf-8') as fh:
            return json.load(fh)

    def _register_font_if_needed(self, font_name: str, font_path: str | None) -> str:
        if not font_path:
            return font_name
        if font_name in self._font_cache:
            return font_name
        pdfmetrics.registerFont(TTFont(font_name, font_path))
        self._font_cache.add(font_name)
        return font_name

    async def _download_image_bytes(self, url: str) -> bytes:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.content

    async def build_book_pdf(
        self,
        *,
        child_name: str,
        config_path: str | Path,
        output_path: str | Path,
    ) -> Path:
        config = self.load_book_config(config_path)
        pages: list[dict[str, Any]] = config['pages']
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        pdf = None
        try:
            for idx, page in enumerate(pages):
                image_url = page['image_url']
                image_bytes = await self._download_image_bytes(image_url)
                image = Image.open(BytesIO(image_bytes)).convert('RGB')
                width_px, height_px = image.size

                if pdf is None:
                    pdf = canvas.Canvas(str(output_path), pagesize=(width_px, height_px))
                else:
                    pdf.setPageSize((width_px, height_px))

                pdf.drawImage(ImageReader(image), 0, 0, width=width_px, height=height_px)

                text_cfg = page.get('text')
                if text_cfg and child_name:
                    await self._draw_name(pdf, child_name, text_cfg, width_px, height_px)

                if idx < len(pages) - 1:
                    pdf.showPage()

            if pdf is None:
                raise RuntimeError('Book config had no pages.')
            pdf.save()
            return output_path
        except Exception:
            logger.exception('PDF build failed')
            raise

    async def _draw_name(
        self,
        pdf: canvas.Canvas,
        child_name: str,
        text_cfg: dict[str, Any],
        page_width: float,
        page_height: float,
    ) -> None:
        font_name = text_cfg.get('font_name', 'Times-Italic')
        font_path = text_cfg.get('font_path')
        font_name = self._register_font_if_needed(font_name, font_path)

        color = text_cfg.get('color', '#4D3516')
        color = color.lstrip('#')
        if len(color) != 6:
            color = '4D3516'
        r = int(color[0:2], 16) / 255.0
        g = int(color[2:4], 16) / 255.0
        b = int(color[4:6], 16) / 255.0
        pdf.setFillColorRGB(r, g, b)

        font_size = float(text_cfg.get('font_size', 32))
        min_font_size = float(text_cfg.get('min_font_size', 8))
        center_x = page_width * (float(text_cfg['x_percent']) / 100.0)
        center_y_from_top = page_height * (float(text_cfg['y_percent']) / 100.0)
        baseline_y = page_height - center_y_from_top
        max_width = page_width * (float(text_cfg.get('width_percent', 25.0)) / 100.0)
        auto_shrink = bool(text_cfg.get('shrink_to_fit', True))

        final_font_size = font_size
        if auto_shrink:
            final_font_size = fit_font_size(
                child_name,
                font_name,
                font_size,
                max_width=max_width,
                min_font_size=min_font_size,
            )

        pdf.setFont(font_name, final_font_size)
        text_width = pdfmetrics.stringWidth(child_name, font_name, final_font_size)
        x = center_x - (text_width / 2.0)
        y = baseline_y - (final_font_size * 0.35)
        pdf.drawString(x, y, child_name)


pdf_builder_service = PDFBuilderService()
