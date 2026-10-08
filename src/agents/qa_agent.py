"""
QA / Supervisor Agent (Session 7 & Session 10):
- Reviews operational output and RAG knowledge
- Formulates a polished, empathetic, and accurate final response
- Ensures no hallucination of policy or unauthorized refund promises
- Supports bilingual responses (Arabic & English) matching customer input
"""

import re
from typing import Dict, Any, Optional

class QAAgent:
    def __init__(self, llm=None):
        self.llm = llm

    def is_arabic(self, text: str) -> bool:
        """Detects if text contains Arabic characters."""
        return bool(re.search(r'[\u0600-\u06FF]', text))

    def format_final_response(
        self,
        customer_message: str,
        triage_data: Dict[str, Any],
        rag_data: Dict[str, Any],
        action_data: Dict[str, Any]
    ) -> str:
        """
        Synthesizes the final verified response.
        """
        arabic = self.is_arabic(customer_message)
        intent = triage_data.get("intent")
        action_executed = action_data.get("action_executed")
        action_res = action_data.get("result", {})

        # Scenario 1: Order Details Looked up
        if action_executed == "GET_ORDER_DETAILS":
            if not action_res.get("success"):
                err = action_res.get("error", "")
                if arabic:
                    return f"عذراً، لم نتمكن من العثور على الطلب: {err}. يرجى التأكد من رقم الطلب والمحاولة مرة أخرى."
                return f"Sorry, we could not find your order: {err}. Please verify the order number and try again."

            order = action_res["order"]
            items_str = ", ".join([f"{item['product_name']} (x{item['quantity']})" for item in action_res.get("items", [])])
            if arabic:
                status_ar = {
                    "Processing": "قيد التجهيز",
                    "Shipped": "تم الشحن (في الطريق)",
                    "Delivered": "تم التوصيل بنجاح",
                    "Cancelled": "تم الإلغاء",
                    "Refunded": "تم استرداد المبلغ"
                }.get(order['status'], order['status'])

                return (
                    f"مرحباً بك أستاذ {order['full_name']}!\n\n"
                    f"📦 **تفاصيل الطلب [{order['order_id']}]:**\n"
                    f"• **الحالة الحالية:** {status_ar}\n"
                    f"• **المنتجات:** {items_str}\n"
                    f"• **إجمالي المبلغ:** ${order['total_amount']:.2f}\n"
                    f"• **عنوان الشحن:** {order['shipping_address']}\n\n"
                    f"هل تحتاج إلى أي مساعدة إضافية بخصوص هذا الطلب؟"
                )
            else:
                return (
                    f"Hello {order['full_name']}!\n\n"
                    f"📦 **Order Status for [{order['order_id']}]:**\n"
                    f"• **Status:** {order['status']}\n"
                    f"• **Items:** {items_str}\n"
                    f"• **Total Amount:** ${order['total_amount']:.2f}\n"
                    f"• **Shipping Address:** {order['shipping_address']}\n\n"
                    f"Is there anything else we can assist you with regarding this order?"
                )

        # Scenario 2: Cancel Order
        elif action_executed == "CANCEL_ORDER":
            if not action_res.get("success"):
                if action_res.get("action_required") == "CUSTOMER_CONFIRMATION_REQUIRED":
                    if arabic:
                        return (
                            f"⚠️ **تأكيد إلغاء الطلب:**\n"
                            f"طلبك مؤهل للإلغاء مع استرداد كامل المبلغ.\n"
                            f"هل تؤكد رغبتك في إلغاء الطلب رقم {triage_data.get('order_id')}؟ أرجو الرد بـ 'نعم أؤكد' للمتابعة."
                        )
                    return (
                        f"⚠️ **Order Cancellation Confirmation Required:**\n"
                        f"Your order is currently processing and eligible for an immediate full refund.\n"
                        f"Are you sure you want to cancel order {triage_data.get('order_id')}? Please reply with 'Yes, confirm' to proceed."
                    )
                else:
                    err = action_res.get("error", "")
                    if arabic:
                        return f"⚠️ لم نتمكن من إلغاء الطلب: {err}"
                    return f"⚠️ Unable to cancel order: {err}"

            # Successfully cancelled
            if arabic:
                return (
                    f"✅ **تم إلغاء الطلب بنجاح:**\n"
                    f"تم إلغاء طلبك رقم [{action_res['order_id']}]، وتم إصدار أمر استرداد كامل لمبلغ ${action_res['refund_amount']:.2f} "
                    f"إلى وسيلة الدفع الأصلية. سيصلك إشعار تأكيد خلال دقائق."
                )
            return (
                f"✅ **Order Successfully Cancelled:**\n"
                f"Your order [{action_res['order_id']}] has been cancelled, and a full refund of ${action_res['refund_amount']:.2f} "
                f"has been queued to your original payment method. You will receive an email confirmation shortly."
            )

        # Scenario 3: Process Refund
        elif action_executed == "PROCESS_REFUND":
            if action_res.get("escalated"):
                tck_id = action_res.get("ticket_id", "N/A")
                amt = action_res.get("refund_amount", 0.0)
                if arabic:
                    return (
                        f"ℹ️ **تم تحويل طلب الاسترداد للمشرف المختص:**\n"
                        f"نظراً لأن قيمة الاسترداد (${amt:.2f}) تتجاوز حد الموافقة الآلية، تم فتح تذكرة استثنائية رقم **[{tck_id}]** "
                        f"وإحالتها فوراً إلى مشرف العمليات للمراجعة والاعتماد. سنقوم بإبلاغك عبر البريد فور إتمام الإجراء."
                    )
                return (
                    f"ℹ️ **Refund Claim Escalated for Supervisor Review:**\n"
                    f"Because the refund amount of ${amt:.2f} exceeds standard automated approval limits, "
                    f"we have created priority ticket **[{tck_id}]** for manual supervisor authorization. "
                    f"Our operations team will review it and notify you via email."
                )
            elif action_res.get("success"):
                amt = action_res.get("refund_amount", 0.0)
                if arabic:
                    return (
                        f"✅ **تمت الموافقة على الاسترداد:**\n"
                        f"تم بنجاح اعتماد استرداد مبلغ ${amt:.2f} لطلبك رقم [{action_res.get('order_id')}]. "
                        f"يستغرق إيداع المبلغ في حسابك البنكي من 3 إلى 5 أيام عمل."
                    )
                return (
                    f"✅ **Refund Approved & Processed:**\n"
                    f"A refund of ${amt:.2f} for order [{action_res.get('order_id')}] has been approved and issued. "
                    f"Funds will reflect in your account within 3 to 5 business days."
                )
            else:
                err = action_res.get("reason") or action_res.get("error", "Not eligible under policy")
                if arabic:
                    return f"عذراً، طلبك غير مؤهل للاسترداد المباشر: {err}."
                return f"Sorry, this request is not eligible for refund: {err}."

        # Scenario 4: Greetings & System Capabilities
        if intent == "GREETING":
            if arabic:
                return (
                    "وعليكم السلام ورحمة الله وبركاته! أهلاً بك في الدعم الفني لشركة OmniTech 🛡️\n\n"
                    "أنا مساعدك الذكي المتكامل للعمليات، وأستطيع مساعدتك في:\n"
                    "• 📦 **تتبع الطلبات:** (مثل: أين طلبي ORD-2024؟)\n"
                    "• ❌ **إلغاء الطلبات قيد التجهيز:** (مع استرداد فوري للأموال مثل ORD-2025)\n"
                    "• 💰 **طلبات الاسترجاع والضمان:** (فحص الشروط وتصعيد التعويضات للمشرفين)\n"
                    "• 🔧 **استكشاف الأعطال الفنية وسياسات المنتجات**\n\n"
                    "كيف يمكنني خدمتك اليوم؟ يمكنك كتابة رقم طلبك أو سؤالك مباشرة!"
                )
            return (
                "Hello and welcome to OmniTech Customer Operations Support 🛡️\n\n"
                "I am your autonomous support agent. I can assist you with:\n"
                "• 📦 **Tracking Orders:** (e.g., 'Where is my order ORD-2024?')\n"
                "• ❌ **Cancelling Orders:** (for orders still processing, e.g., ORD-2025)\n"
                "• 💰 **Returns & Refunds:** (eligibility checks and supervisor escalations)\n"
                "• 🔧 **Technical Troubleshooting & Warranty Inquiries**\n\n"
                "How may I help you today? Feel free to ask a question or provide your Order ID!"
            )

        # Scenario 5: Troubleshooting / Policy Knowledge
        guidance = action_data.get("rag_guidance") or rag_data.get("grounded_context", "")
        if arabic:
            return (
                f"أهلاً بك! إليك المعلومات المعتمدة وفقاً لسياساتنا وكتالوج المنتجات:\n\n"
                f"{guidance}\n\n"
                f"هل تود المساعدة في فحص طلب معين أو فتح تذكرة دعم فني؟"
            )
        return (
            f"Hello! Here is the verified information from our official policies and product catalog:\n\n"
            f"{guidance}\n\n"
            f"Would you like assistance with a specific order or would you like to open a support ticket?"
        )
