import re
from decimal import Decimal
from typing import List, Dict, Any
from app.domain.models import BOQItem


class BOQAnalyticsEngine:
    """Computes aggregates and performs category categorization on lists of BOQItem domain models."""

    @staticmethod
    def classify_item(description: str) -> str:
        desc = description.lower()
        
        # OFC Patterns
        if re.search(r"\b(ofc|optical\s+fiber|fiber\s+optic|fibre\s+optic|fiber\s+cable|fibre\s+cable|armoured\s+fiber)\b", desc):
            return "OFC"
            
        # UPS Patterns
        if re.search(r"\b(ups|uninterruptible\s+power|inverter|battery\s+bank|smf\s+battery|lead\s+acid\s+battery)\b", desc):
            return "UPS"
            
        # Networking Patterns
        if re.search(r"\b(switch|router|rj45|networking|patch\s+panel|cat6|cat-6|transceiver|media\s+converter|rack|patch\s+cord|lan)\b", desc):
            return "Networking"
            
        # Display Systems Patterns
        if re.search(r"\b(display|monitor|screen|led\s+board|video\s+wall|signage\s+board|indicator|digital\s+board|fids)\b", desc):
            return "Display Systems"
            
        # Civil Work Patterns
        if re.search(r"\b(excavation|concrete|cement|brick|foundation|plaster|sand|gravel|painting|tile|masonry|drainage|earthwork|fencing)\b", desc):
            return "Civil Work"
            
        # Electrical Work Patterns
        if re.search(r"\b(wiring|conduit|switchgear|earthing|light\s+fitting|db\s+board|mcb|transformer|substation|insulator|junction\s+box|electrical)\b", desc):
            return "Electrical Work"
            
        return "Others"


    def compute_summary(self, items: List[BOQItem]) -> dict:
        total_items = len(items)
        total_quantity = sum(item.quantity for item in items if item.quantity is not None)
        total_estimated_value = sum(item.amount for item in items if item.amount is not None)
        
        # Sort items by amount descending, handling None amounts by pushing them to the end
        sorted_items = sorted(
            items,
            key=lambda x: x.amount if x.amount is not None else Decimal("-1.0"),
            reverse=True
        )
        top_items = sorted_items[:10]
        
        return {
            "total_items": total_items,
            "total_quantity": Decimal(str(total_quantity)) if total_quantity is not None else Decimal("0.0"),
            "total_estimated_value": Decimal(str(total_estimated_value)) if total_estimated_value is not None else Decimal("0.0"),
            "top_items": top_items,
        }

    def compute_category_analysis(self, items: List[BOQItem]) -> List[dict]:
        categories = ["OFC", "UPS", "Networking", "Display Systems", "Civil Work", "Electrical Work", "Others"]
        
        # Initialize aggregates
        category_data = {
            cat: {"item_count": 0, "total_value": Decimal("0.0")}
            for cat in categories
        }
        
        total_value = Decimal("0.0")
        
        for item in items:
            cat = self.classify_item(item.item_name)
            category_data[cat]["item_count"] += 1
            if item.amount is not None:
                amt = Decimal(str(item.amount))
                category_data[cat]["total_value"] += amt
                total_value += amt

        # Format output
        results = []
        for cat in categories:
            cat_val = category_data[cat]["total_value"]
            percentage = Decimal("0.0")
            if total_value > Decimal("0.0"):
                percentage = (cat_val / total_value) * Decimal("100.0")
            
            results.append({
                "category": cat,
                "item_count": category_data[cat]["item_count"],
                "total_value": cat_val,
                "percentage": round(percentage, 2),
            })
            
        return results
