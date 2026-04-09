import logging
from app.services.gelato import GelatoService
from app.services.pdf_builder import PDFBuilderService

logger = logging.getLogger(__name__)


class PipelineService:
    def __init__(self):
        self.gelato_service = GelatoService()
        self.pdf_builder = PDFBuilderService()

    async def process_paid_order(self, shopify_order: dict):
        try:
            logger.info("Starting pipeline")

            line_item = shopify_order["line_items"][0]
            properties = line_item.get("properties", [])

            images = [
                p["value"]
                for p in properties
                if p.get("name", "").startswith("image_")
            ]

            if not images:
                raise Exception("No images found in Shopify properties")

            pdf_url = await self.pdf_builder.build_pdf(images)
            logger.info(f"PDF created: {pdf_url}")

            page_count = 30  # FIXED

            shipping = shopify_order["shipping_address"]

            product_uid = "photobooks-hardcover_pf_200x200-mm-8x8-inch_pt_170-gsm-65lb-coated-silk_cl_4-4_ccl_4-4_bt_glued-left_ct_matt-lamination_prt_1-0_cpt_130-gsm-65-lb-cover-coated-silk_ver"

            gelato_payload = {
                "orderType": "order",
                "orderReferenceId": str(shopify_order["id"]),
                "customerReferenceId": str(shopify_order.get("customer", {}).get("id") or shopify_order["id"]),
                "currency": "USD",
                "items": [
                    {
                        "itemReferenceId": str(line_item["id"]),
                        "productUid": product_uid,
                        "files": [
                            {
                                "type": "default",
                                "url": pdf_url,
                            }
                        ],
                        "pageCount": page_count,
                        "quantity": 1,
                    }
                ],
                "shipmentMethodUid": "standard",
                "shippingAddress": {
                    "firstName": shipping["first_name"],
                    "lastName": shipping["last_name"],
                    "addressLine1": shipping["address1"],
                    "addressLine2": shipping.get("address2", ""),
                    "city": shipping["city"],
                    "state": shipping.get("province", ""),
                    "postCode": shipping["zip"],
                    "country": shipping["country_code"],
                    "email": shopify_order["email"],
                },
            }

            logger.info(f"Gelato payload: {gelato_payload}")

            result = await self.gelato_service.create_order(gelato_payload)

            logger.info(f"Gelato success: {result}")

            return result

        except Exception as e:
            logger.exception(f"Pipeline failed: {e}")
            raise


pipeline_service = PipelineService()
