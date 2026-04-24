"""
Smart-Boutique/genai/tools.py
-------------------------------
Custom LangChain Tools — from your notes Section 9
@tool decorator, ReAct loop, custom boutique database tools.
"""

import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

import datetime

# ── TOOL DECORATOR ────────────────────────────────────────────────────────────
try:
    from langchain.tools import tool
except ImportError:
    try:
        from langchain_core.tools import tool
    except ImportError:
        # Ultimate fallback — plain decorator
        def tool(func):
            func.name        = func.__name__
            func.description = func.__doc__ or ""
            func.run         = func
            return func

# Import boutique DB
try:
    from database.db import run_query
    DB_AVAILABLE = True
except Exception:
    DB_AVAILABLE = False


@tool
def get_sales_summary(period: str = "all") -> str:
    """
    Get boutique sales summary from the database.
    Use when user asks about revenue, orders, or business performance.
    Input: period = 'all', 'spring', 'summer', 'autumn', or 'winter'
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        if period.lower() in ["spring", "summer", "autumn", "winter"]:
            df = run_query(f"""
                SELECT COUNT(DISTINCT order_id) AS orders,
                       SUM(amount) AS revenue, AVG(amount) AS avg_order
                FROM orders
                WHERE season = '{period.title()}' AND status NOT IN ('Cancelled')
            """)
        else:
            df = run_query("""
                SELECT COUNT(DISTINCT order_id) AS orders,
                       SUM(amount) AS revenue, AVG(amount) AS avg_order,
                       COUNT(DISTINCT cust_id) AS customers
                FROM orders WHERE status NOT IN ('Cancelled')
            """)
        if df.empty:
            return "No sales data found."
        r = df.iloc[0]
        return (f"Sales ({period}): Orders={int(r.get('orders',0) or 0):,}, "
                f"Revenue=Rs{int(r.get('revenue',0) or 0):,}, "
                f"Avg=Rs{int(r.get('avg_order',0) or 0):,}")
    except Exception as e:
        return f"Error: {e}"


@tool
def get_top_categories(top_n: int = 5) -> str:
    """
    Get top selling product categories by order volume.
    Use when user asks which categories are most popular or sell best.
    Input: top_n = number of categories to return (default 5)
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        df = run_query(f"""
            SELECT category, COUNT(*) AS orders,
                   SUM(amount) AS revenue, ROUND(AVG(amount)) AS avg_price
            FROM orders WHERE category IS NOT NULL
            GROUP BY category ORDER BY orders DESC LIMIT {int(top_n)}
        """)
        if df.empty:
            return "No category data."
        result = "Top Categories:\n"
        for _, row in df.iterrows():
            result += f"  {row['category']}: {int(row['orders']):,} orders, Rs{int(row['revenue']):,}\n"
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
def get_customer_info(customer_id: str) -> str:
    """
    Get details about a specific customer including order history.
    Use when user asks about a specific customer by their ID.
    Input: customer_id = numeric customer ID like '1029312'
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        df = run_query(f"""
            SELECT c.name, c.gender, c.age, c.age_group,
                   COUNT(o.order_id) AS total_orders,
                   SUM(o.amount) AS total_spent,
                   GROUP_CONCAT(DISTINCT o.category) AS categories,
                   GROUP_CONCAT(DISTINCT o.size) AS sizes
            FROM customers c
            LEFT JOIN orders o ON c.cust_id = o.cust_id
            WHERE c.cust_id = {customer_id}
            GROUP BY c.cust_id
        """)
        if df.empty:
            return f"No customer found with ID {customer_id}."
        r = df.iloc[0]
        return (f"Customer {customer_id}: {r.get('name','Unknown')}, "
                f"Gender={r.get('gender','?')}, Age={r.get('age','?')}, "
                f"Orders={int(r.get('total_orders',0))}, "
                f"Spent=Rs{int(r.get('total_spent',0) or 0):,}, "
                f"Categories={r.get('categories','none')}")
    except Exception as e:
        return f"Error: {e}"


@tool
def get_supplier_performance(supplier_name: str = "all") -> str:
    """
    Get performance data for retail suppliers.
    Use when user asks about Myntra, Ajio, Amazon, Flipkart, Meesho.
    Input: supplier_name = specific name or 'all' for all suppliers
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        where = f"AND retail_supplier = '{supplier_name}'" if supplier_name.lower() != "all" else ""
        df = run_query(f"""
            SELECT retail_supplier, COUNT(*) AS orders,
                   SUM(amount) AS revenue,
                   ROUND(100.0*SUM(return_flag)/COUNT(*),1) AS return_rate
            FROM orders WHERE retail_supplier IS NOT NULL {where}
            GROUP BY retail_supplier ORDER BY orders DESC
        """)
        if df.empty:
            return "No supplier data."
        result = "Supplier Performance:\n"
        for _, row in df.iterrows():
            result += (f"  {row['retail_supplier']}: {int(row['orders']):,} orders, "
                      f"Rs{int(row['revenue']):,}, Return Rate {row['return_rate']}%\n")
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
def get_seasonal_demand(season: str) -> str:
    """
    Get product demand for a specific season.
    Use when user asks what to stock for summer, winter, Diwali season etc.
    Input: season = 'Spring', 'Summer', 'Autumn', or 'Winter'
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        df = run_query(f"""
            SELECT category, COUNT(*) AS orders,
                   SUM(qty) AS units, SUM(amount) AS revenue
            FROM orders
            WHERE season = '{season.title()}' AND category IS NOT NULL
            GROUP BY category ORDER BY orders DESC
        """)
        if df.empty:
            return f"No data for {season}."
        result = f"Demand in {season.title()}:\n"
        for _, row in df.iterrows():
            result += f"  {row['category']}: {int(row['orders']):,} orders, {int(row['units']):,} units\n"
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
def get_return_analysis(category: str = "all") -> str:
    """
    Get return and cancellation rates by category or overall.
    Use when user asks about returns, cancellations, or problematic products.
    Input: category = specific category like 'kurta', 'set', or 'all'
    """
    if not DB_AVAILABLE:
        return "Database not available."
    try:
        where = f"AND category = '{category}'" if category.lower() != "all" else ""
        df = run_query(f"""
            SELECT category, COUNT(*) AS total_orders,
                   SUM(return_flag) AS returns,
                   ROUND(100.0*SUM(return_flag)/COUNT(*),1) AS return_rate
            FROM orders WHERE category IS NOT NULL {where}
            GROUP BY category ORDER BY return_rate DESC
        """)
        if df.empty:
            return "No return data."
        result = "Return Analysis:\n"
        for _, row in df.iterrows():
            result += (f"  {row['category']}: {int(row['returns'])} returns / "
                      f"{int(row['total_orders'])} orders ({row['return_rate']}%)\n")
        return result
    except Exception as e:
        return f"Error: {e}"


@tool
def get_current_date_and_season(query: str = "") -> str:
    """
    Get current date, season, and upcoming Indian festivals.
    Use when user asks about current season, festivals, or what to stock now.
    Input: any string — this tool just returns current date and festival info
    """
    today  = datetime.date.today()
    month  = today.month
    season_map = {
        1:"Winter",2:"Winter",3:"Spring",4:"Spring",5:"Spring",
        6:"Summer",7:"Summer",8:"Summer",9:"Autumn",10:"Autumn",
        11:"Autumn",12:"Winter"
    }
    festivals = {
        1:"Pongal, Makar Sankranti", 2:"Valentine's Day, Maha Shivratri",
        3:"Holi, Ugadi", 4:"Baisakhi, Ram Navami", 5:"Mother's Day",
        6:"Eid al-Adha", 7:"Guru Purnima",
        8:"Independence Day, Raksha Bandhan, Janmashtami",
        9:"Ganesh Chaturthi, Navratri", 10:"Navratri, Dussehra, Karwa Chauth",
        11:"Diwali, Bhai Dooj", 12:"Christmas, New Year Eve"
    }
    next_m = (month % 12) + 1
    return (f"Today: {today.strftime('%d %B %Y')} | Season: {season_map[month]} | "
            f"This month: {festivals.get(month,'None')} | "
            f"Next month: {festivals.get(next_m,'None')}")


ALL_TOOLS = [
    get_sales_summary,
    get_top_categories,
    get_customer_info,
    get_supplier_performance,
    get_seasonal_demand,
    get_return_analysis,
    get_current_date_and_season,
]
