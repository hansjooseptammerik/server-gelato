import logging
from app.services.gelato import GelatoService
from app.services.pdf_builder import build_pdf

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self):
        self.gelato_service = GelatoService()

    async def process_paid_order(self, shopify_order: dict):
        try:
            logger.info("Starting pipeline")

            # -----------------------------
            # 1. GET IMAGES (Shopify line items properties)
            # -----------------------------
            line_item = shopify_order["line_items"][0]

            properties = line_item.get("properties", [])

            images = [
                p["value"]
                for p in properties
                if p.get("name", "").startswith("image_")
            ]

            if not images:
                raise Exception("No images found in Shopify properties")

            # -----------------------------
            # 2. BUILD PDF
            # -----------------------------
            pdf_url = build_pdf(images)
            logger.info(f"PDF created: {pdf_url}")

            # -----------------------------
            # 3. PAGE COUNT
            # -----------------------------
            page_count = len(images) * 2

            # -----------------------------
            # 4. SHIPPING
            # -----------------------------
            shipping = shopify_order["shipping_address"]

            # -----------------------------
            # 5. PRODUCT UID (HARDCODE FOR NOW)
            # -----------------------------
            product_uid = "photobooks-hardcover_pf_200x200-mm-8x8-inch_pt_170-gsm-65lb-coated-silk_cl_4-4_coil_4-4_bt_glued-left_ct_matte-lamination_pt_1_0_cpt_130"

            # -----------------------------
            # 6. BUILD PAYLOAD
            # -----------------------------
            gelato_payload = {
                "orderType": "order",
                "orderReferenceId": str(shopify_order["id"]),
                "customerReferenceId": str(shopify_order["id"]),
                "currency": shopify_order.get("currency", "USD"),
                "items": [
                    {
                        "itemReferenceId": str(shopify_order["id"]),
                        "productUid": product_uid,
                        "files": [
                            {
                                "type": "default",
                                "url": pdf_url
                            }
                        ],
                        "pageCount": {
                            "product_file": page_count
                        },
                        "quantity": 1,
                        "shipmentMethodUid": "standard"
                    }
                ],
                "shippingAddress": {
                    "firstName": shipping["first_name"],
                    "lastName": shipping["last_name"],
                    "addressLine1": shipping["address1"],
                    "addressLine2": shipping.get("address2", ""),
                    "city": shipping["city"],
                    "state": shipping.get("province", ""),
                    "postCode": shipping["zip"],
                    "country": shipping["country_code"],
                    "email": shopify_order["email"]
                }
            }

            logger.info(f"Gelato payload: {gelato_payload}")

            # -----------------------------
            # 7. SEND
            # -----------------------------
            result = await self.gelato_service.create_order(gelato_payload)

            logger.info(f"Gelato success: {result}")

            return result

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            raise


pipeline_service = PipelineService()
