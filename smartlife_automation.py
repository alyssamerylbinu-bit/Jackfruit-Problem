import streamlit as st
import json
import datetime
from collections import Counter
import matplotlib.pyplot as plt
import pandas as pd
import requests
import os
import random
from dotenv import load_dotenv

# -------------------- CONFIGURATION --------------------
load_dotenv()
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
NEWS_API_KEY = os.getenv("NEWS_API_KEY")

REMINDER_FILE = "reminders.json"
EXPENSE_FILE = "expenses.csv"
GOALS_FILE = "goals.json"
BUDGET_FILE = "budget.json"
CSV_FILE = "Bengaluru_Restaurants.csv"


# -------------------- CHART STYLING --------------------
def apply_chart_style():
    """Apply consistent dark, modern styling to all charts"""
    # Dark charcoal background that complements Streamlit
    plt.rcParams['figure.facecolor'] = '#1E1E1E'  # Dark charcoal background
    plt.rcParams['axes.facecolor'] = '#2D2D2D'  # Dark gray chart background
    plt.rcParams['axes.edgecolor'] = '#404040'  # Medium gray borders
    plt.rcParams['grid.color'] = '#404040'  # Medium gray grid
    plt.rcParams['text.color'] = '#E0E0E0'  # Light gray text
    plt.rcParams['axes.labelcolor'] = '#E0E0E0'
    plt.rcParams['xtick.color'] = '#B0B0B0'  # Light gray ticks
    plt.rcParams['ytick.color'] = '#B0B0B0'
    plt.rcParams['font.size'] = 10
    plt.rcParams['axes.titleweight'] = 'medium'
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.linestyle'] = '--'


# Call this once at the beginning
apply_chart_style()

# -------------------- STREAMLIT SETUP --------------------
st.set_page_config(page_title="Smart Life Hub", layout="wide")
st.sidebar.title("🌙 Smart Life Hub")


# -------------------- DATA MANAGERS --------------------
class ReminderManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        try:
            with open(self.file_path, "r") as f:
                data = json.load(f)
                for task in data:
                    if "completed" not in task:
                        task["completed"] = False
                return data
        except FileNotFoundError:
            return []

    def save(self, tasks):
        with open(self.file_path, "w") as f:
            json.dump(tasks, f, indent=4)

    def add(self, task_text, date_time):
        tasks = self.load()
        tasks.append({
            "task": task_text.strip(),
            "time": date_time,
            "completed": False
        })
        self.save(tasks)

    def check_reminders(self):
        """Check and show notifications for due reminders"""
        tasks = self.load()
        now = datetime.datetime.now()
        notifications = []

        for task in tasks:
            if not task["completed"]:
                try:
                    task_time = datetime.datetime.strptime(task["time"], "%Y-%m-%d %H:%M")
                    if task_time <= now:
                        notifications.append(task["task"])
                except:
                    try:
                        task_time = datetime.datetime.strptime(task["time"], "%Y-%m-%d")
                        if task_time.date() <= now.date():
                            notifications.append(task["task"])
                    except:
                        continue

        return notifications


class ExpenseManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        try:
            df = pd.read_csv(self.file_path)
            # Convert Date column to datetime if it exists
            if 'Date' in df.columns:
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            return df
        except FileNotFoundError:
            # Return empty dataframe with required columns
            return pd.DataFrame(columns=["Item", "Amount", "Date"])

    def save(self, df):
        df.to_csv(self.file_path, index=False)

    def add(self, item, amount):
        df = self.load()

        new_row = pd.DataFrame({
            "Item": [item],
            "Amount": [amount],
            "Date": [datetime.date.today().isoformat()]
        })
        df = pd.concat([df, new_row], ignore_index=True)
        self.save(df)

    def get_spending_insights(self):
        """Generate simple spending insights"""
        df = self.load()

        if df.empty:
            return ["No expenses yet to analyze"]

        insights = []

        # Ensure Date column exists
        if 'Date' not in df.columns:
            return ["Add more expenses for insights"]

        df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
        df = df.dropna(subset=['Date'])

        # Day of week analysis
        df['Day'] = df['Date'].dt.day_name()
        day_spending = df.groupby('Day')['Amount'].sum()
        if not day_spending.empty:
            highest_day = day_spending.idxmax()
            insights.append(f"💰 Highest spending day: {highest_day}")

        # Weekly spending trend
        df['Week'] = df['Date'].dt.isocalendar().week
        weekly_spending = df.groupby('Week')['Amount'].sum()

        if len(weekly_spending) >= 2:
            last_week = weekly_spending.iloc[-1]
            second_last = weekly_spending.iloc[-2]
            if last_week > second_last:
                increase = ((last_week - second_last) / second_last) * 100
                insights.append(f"📈 Spending increased by {increase:.0f}% this week")

        # Recent vs previous period
        today = datetime.date.today()
        start_of_month = today.replace(day=1)
        last_month = (start_of_month - datetime.timedelta(days=1)).replace(day=1)

        # This month's spending
        this_month = df[df['Date'].dt.date >= start_of_month]['Amount'].sum()

        # Last month's spending (if we have data)
        last_month_mask = (df['Date'].dt.date >= last_month) & (df['Date'].dt.date < start_of_month)
        last_month_spent = df[last_month_mask]['Amount'].sum()

        if last_month_spent > 0 and this_month > 0:
            change = ((this_month - last_month_spent) / last_month_spent) * 100
            if change > 10:
                insights.append(f"⚠️ Spending {abs(change):.0f}% {'higher' if change > 0 else 'lower'} than last month")

        return insights


class BudgetManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}

    def save(self, budget_data):
        with open(self.file_path, "w") as f:
            json.dump(budget_data, f, indent=4)

    def set_weekly_budget(self, amount):
        budget_data = self.load()
        budget_data["weekly_budget"] = amount
        budget_data["week_start"] = datetime.date.today().isoformat()
        self.save(budget_data)

    def get_budget_alerts(self, expenses_df):
        """Check if spending exceeds budget"""
        budget_data = self.load()

        if "weekly_budget" not in budget_data:
            return []

        weekly_budget = budget_data["weekly_budget"]
        week_start = datetime.datetime.strptime(budget_data["week_start"], "%Y-%m-%d").date()

        # Calculate this week's spending
        if expenses_df.empty or 'Date' not in expenses_df.columns:
            return []

        expenses_df['Date'] = pd.to_datetime(expenses_df['Date'], errors='coerce')
        this_week_expenses = expenses_df[
            expenses_df['Date'].dt.date >= week_start
            ]['Amount'].sum()

        alerts = []
        percentage = (this_week_expenses / weekly_budget) * 100

        if percentage >= 100:
            alerts.append(f"❌ Budget exceeded! Spent ₹{this_week_expenses:.0f} of ₹{weekly_budget} ({percentage:.0f}%)")
        elif percentage >= 80:
            alerts.append(f"⚠️ Budget at {percentage:.0f}% (₹{this_week_expenses:.0f}/₹{weekly_budget})")

        return alerts


class GoalManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load(self):
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return []

    def save(self, goals):
        with open(self.file_path, "w") as f:
            json.dump(goals, f, indent=4)

    def add(self, name, target_amount, timeframe_months):
        goals = self.load()
        goals.append({
            "name": name,
            "target_amount": target_amount,
            "current_amount": 0,
            "timeframe_months": timeframe_months,
            "created": datetime.date.today().isoformat(),
            "target_date": (datetime.date.today() + datetime.timedelta(days=30 * timeframe_months)).isoformat()
        })
        self.save(goals)

    def update_progress(self, goal_index, amount_added):
        goals = self.load()
        if 0 <= goal_index < len(goals):
            goals[goal_index]["current_amount"] += amount_added
            self.save(goals)

    def get_progress(self, expenses_df):
        """Calculate progress towards goals"""
        goals = self.load()
        if not goals:
            return goals

        total_spent = expenses_df['Amount'].sum() if not expenses_df.empty else 0

        for goal in goals:
            # Calculate monthly saving needed
            try:
                target_date = datetime.datetime.strptime(goal["target_date"], "%Y-%m-%d").date()
                days_left = (target_date - datetime.date.today()).days
                if days_left > 0:
                    daily_saving_needed = (goal["target_amount"] - goal["current_amount"]) / days_left
                    goal["daily_saving"] = daily_saving_needed
                    goal["days_left"] = days_left

                    # Simple warning based on average spending
                    if total_spent > 0 and expenses_df.shape[0] > 10:
                        avg_daily_spend = total_spent / expenses_df.shape[0]  # Rough average
                        if avg_daily_spend > daily_saving_needed * 2:
                            goal["warning"] = "You might need to save more to reach this goal"
            except:
                pass

        return goals


class RestaurantManager:
    def __init__(self, file_path):
        self.file_path = file_path

    def load_data(self):
        try:
            return pd.read_csv(self.file_path)
        except:
            return pd.DataFrame()

    def get_occasion_suggestions(self, occasion):
        """Get restaurant suggestions based on occasion"""
        suggestions = {
            "Romantic Dinner": ["Fine Dining", "Italian", "French", "Candle Light"],
            "Family Dinner": ["North Indian", "Chinese", "Multi-cuisine", "Vegetarian"],
            "Business Lunch": ["Quick Bites", "Cafe", "Sandwiches", "Salads"],
            "Birthday Party": ["Pub", "Barbeque", "Multi-cuisine", "Desserts"],
            "Quick Lunch": ["Fast Food", "South Indian", "Street Food", "Snacks"],
            "Date Night": ["Italian", "Chinese", "Continental", "Wine Bar"]
        }
        return suggestions.get(occasion, ["Indian", "Chinese", "Italian"])


# -------------------- NOTIFICATION SYSTEM --------------------
def show_notifications():
    """Display notifications at the top of the app"""
    rm = ReminderManager(REMINDER_FILE)
    notifications = rm.check_reminders()

    if notifications:
        with st.container():
            st.markdown("""
            <style>
            .notification {
                background-color: #2D2D2D;
                border-left: 5px solid #4ECDC4;
                padding: 12px;
                margin: 10px 0;
                border-radius: 6px;
                color: #E0E0E0;
                box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            }
            </style>
            """, unsafe_allow_html=True)

            for notification in notifications:
                st.markdown(f'<div class="notification">🔔 {notification}</div>', unsafe_allow_html=True)


# -------------------- PAGE: HOME --------------------
def show_home():
    st.header("Welcome to Smart Life Hub! 🏠")

    # Show notifications at top
    show_notifications()

    # Quick stats
    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Current Time", datetime.datetime.now().strftime("%H:%M:%S"))

    with col2:
        rm = ReminderManager(REMINDER_FILE)
        pending = sum(1 for t in rm.load() if not t["completed"])
        st.metric("Pending Reminders", pending)

    with col3:
        em = ExpenseManager(EXPENSE_FILE)
        df = em.load()
        total = df["Amount"].sum() if not df.empty and "Amount" in df.columns else 0
        st.metric("Total Expenses", f"₹{total:.2f}")

    st.markdown("---")

    # Features overview
    st.subheader("✨ Features")
    cols = st.columns(4)

    features = [
        ("📅 Reminders", "Smart notifications & tracking"),
        ("💰 Expenses", "Budget alerts & savings goals"),
        ("🌤 Weather", "Live weather updates"),
        ("🍽 Restaurants", "Occasion-based recommendations")
    ]

    for col, (icon, desc) in zip(cols, features):
        with col:
            st.markdown(f"### {icon}")
            st.write(desc)


# -------------------- PAGE: REMINDERS --------------------
def show_reminders():
    st.header("📅 Smart Reminders")

    # Show notifications
    show_notifications()

    rm = ReminderManager(REMINDER_FILE)
    tasks = rm.load()

    # Add new reminder
    with st.expander("➕ Add New Reminder", expanded=True):
        col1, col2 = st.columns(2)
        with col1:
            task_text = st.text_input("Reminder", placeholder="E.g., 'Call Mom'")
        with col2:
            task_date = st.date_input("Date", datetime.date.today())
            task_time = st.time_input("Time", datetime.time(9, 0))

        if st.button("Add Reminder", type="primary") and task_text:
            date_str = datetime.datetime.combine(task_date, task_time).strftime("%Y-%m-%d %H:%M")
            rm.add(task_text, date_str)
            st.success("✅ Reminder added!")
            st.rerun()

    # Task frequency bar chart
    if tasks:
        st.subheader("📊 Reminder Frequency")
        task_names = [t["task"] for t in tasks]
        freq = Counter(task_names)

        fig, ax = plt.subplots(figsize=(8, 3))

        # Dark teal bars with glowing effect for dark background
        colors = ['#4ECDC4' for _ in freq.keys()]  # Bright teal that pops on dark
        bars = ax.bar(freq.keys(), freq.values(), color=colors,
                      edgecolor='#2D2D2D', linewidth=2, alpha=0.9)

        # Add subtle glow effect
        for i, bar in enumerate(bars):
            # Create gradient from teal to light teal
            bar.set_color(plt.cm.summer(0.4 + i * 0.03))
            bar.set_edgecolor('#4ECDC4')
            bar.set_linewidth(1.5)

        ax.set_ylabel("Count", fontsize=11, labelpad=10, color='#E0E0E0')
        ax.yaxis.grid(True, linestyle='--', alpha=0.2, color='#404040')
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color('#404040')
        ax.spines['bottom'].set_color('#404040')

        # Set tick colors for dark theme
        ax.tick_params(axis='x', colors='#B0B0B0', rotation=45)
        ax.tick_params(axis='y', colors='#B0B0B0')

        plt.xticks(rotation=45, ha='right', fontsize=10)
        plt.yticks(fontsize=10)
        plt.tight_layout()
        st.pyplot(fig)

    # Display reminders
    st.subheader("📋 Your Reminders")

    if not tasks:
        st.info("No reminders yet. Add one above!")
    else:
        view = st.radio("View:", ["All", "Pending", "Completed"], horizontal=True)

        filtered_tasks = tasks
        if view == "Pending":
            filtered_tasks = [t for t in tasks if not t["completed"]]
        elif view == "Completed":
            filtered_tasks = [t for t in tasks if t["completed"]]

        for i, task in enumerate(filtered_tasks):
            col1, col2, col3 = st.columns([4, 2, 1])

            with col1:
                status = "✅" if task["completed"] else "⏰"
                st.write(f"{status} {task['task']}")

            with col2:
                try:
                    dt = datetime.datetime.strptime(task["time"], "%Y-%m-%d %H:%M")
                    time_str = dt.strftime("%b %d, %I:%M %p")
                except:
                    time_str = task["time"]
                st.write(f"📅 {time_str}")

            with col3:
                if st.button("Toggle", key=f"toggle_{i}"):
                    # Mark as completed
                    task["completed"] = not task["completed"]
                    rm.save(tasks)
                    st.rerun()


# -------------------- PAGE: EXPENSES --------------------
def show_expenses():
    st.header("💰 Smart Expense Tracker")

    em = ExpenseManager(EXPENSE_FILE)
    gm = GoalManager(GOALS_FILE)
    bm = BudgetManager(BUDGET_FILE)

    # Show budget alerts at top
    df = em.load()
    budget_alerts = bm.get_budget_alerts(df)
    if budget_alerts:
        for alert in budget_alerts:
            if "❌" in alert:
                st.error(alert)
            else:
                st.warning(alert)

    # Tabs for different sections
    tab1, tab2, tab3 = st.tabs(["Add Expense", "Savings Goals", "Budget & Insights"])

    with tab1:
        # Add expense - SIMPLIFIED (no categories)
        with st.expander("➕ Add Expense", expanded=True):
            col1, col2 = st.columns([2, 1])
            with col1:
                item = st.text_input("Item", placeholder="E.g., Groceries, Zomato, Fuel")
            with col2:
                amount = st.number_input("Amount (₹)", min_value=0.0, value=0.0)

            if st.button("Add Expense", type="primary") and item and amount > 0:
                em.add(item, amount)
                st.success(f"✅ Added: {item} - ₹{amount:.2f}")
                st.rerun()

        # Display expenses
        df = em.load()
        if not df.empty:
            st.subheader("📋 Expense History")
            st.dataframe(df.sort_values("Date", ascending=False))

    with tab2:
        # Savings Goals
        st.subheader("🎯 Savings Goals")

        # Add new goal
        with st.expander("➕ Set New Goal"):
            col1, col2, col3 = st.columns(3)
            with col1:
                goal_name = st.text_input("Goal Name", placeholder="E.g., New Laptop")
            with col2:
                target_amount = st.number_input("Target Amount (₹)", min_value=100.0, value=10000.0)
            with col3:
                timeframe = st.selectbox("Timeframe", [1, 2, 3, 6, 12],
                                         format_func=lambda x: f"{x} month{'s' if x > 1 else ''}")

            if st.button("Set Goal", key="set_goal") and goal_name:
                gm.add(goal_name, target_amount, timeframe)
                st.success(f"✅ Goal '{goal_name}' set!")
                st.rerun()

        # Display goals progress
        goals = gm.get_progress(df)

        if not goals:
            st.info("No savings goals yet. Set one above!")
        else:
            for i, goal in enumerate(goals):
                progress = min(100, (goal["current_amount"] / goal["target_amount"]) * 100)

                st.write(f"**{goal['name']}** - ₹{goal['current_amount']:.0f}/₹{goal['target_amount']:.0f}")
                st.progress(progress / 100)

                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"Progress: {progress:.1f}%")
                with col2:
                    if "days_left" in goal:
                        st.write(f"Days left: {goal['days_left']}")
                        if "daily_saving" in goal:
                            st.write(f"Save ₹{goal['daily_saving']:.0f}/day")

                if "warning" in goal:
                    st.error(goal["warning"])

                # Add money to goal
                with st.expander(f"Add to {goal['name']}"):
                    add_amount = st.number_input("Amount to add (₹)", min_value=0.0, key=f"add_{i}")
                    if st.button("Add", key=f"add_btn_{i}"):
                        gm.update_progress(i, add_amount)
                        st.success(f"✅ Added ₹{add_amount:.0f} to {goal['name']}")
                        st.rerun()

                st.divider()

    with tab3:
        # Budget Setting
        st.subheader("📊 Set Weekly Budget")

        current_budget = bm.load().get("weekly_budget", 0)
        if current_budget > 0:
            st.info(f"Current weekly budget: ₹{current_budget:.0f}")

        new_budget = st.number_input("New Weekly Budget (₹)", min_value=100.0, value=5000.0)

        if st.button("Set Budget"):
            bm.set_weekly_budget(new_budget)
            st.success(f"✅ Weekly budget set to ₹{new_budget:.0f}")
            st.rerun()

        st.markdown("---")

        # Insights
        st.subheader("💡 Spending Insights")

        insights = em.get_spending_insights()
        if insights:
            for insight in insights:
                st.info(insight)
        else:
            st.info("Add more expenses to get insights!")

        # Simple spending chart
        df = em.load()
        if not df.empty and 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'], errors='coerce')
            df = df.dropna(subset=['Date'])

            if not df.empty:
                # Weekly spending chart
                df['Week'] = df['Date'].dt.strftime('%Y-%U')
                weekly = df.groupby('Week')['Amount'].sum().tail(8)

                if not weekly.empty:
                    fig, ax = plt.subplots(figsize=(8, 3))

                    # Coral pink that pops on dark background
                    colors = ['#FF6B8B' for _ in range(len(weekly))]  # Bright coral pink
                    bars = ax.bar(weekly.index, weekly.values, color=colors,
                                  edgecolor='#2D2D2D', linewidth=2, alpha=0.9)

                    # Add glow gradient effect
                    for i, bar in enumerate(bars):
                        # Create gradient from coral to light coral
                        intensity = 0.5 + (weekly.values[i] / weekly.values.max()) * 0.3
                        bar.set_color(plt.cm.Reds(0.3 + intensity * 0.2))
                        bar.set_edgecolor('#FF6B8B')
                        bar.set_linewidth(1.5)

                    ax.set_ylabel("Amount (₹)", fontsize=11, labelpad=10, color='#E0E0E0')
                    ax.set_xlabel("Week", fontsize=11, labelpad=10, color='#E0E0E0')
                    ax.yaxis.grid(True, linestyle='--', alpha=0.2, color='#404040')
                    ax.spines['top'].set_visible(False)
                    ax.spines['right'].set_visible(False)
                    ax.spines['left'].set_color('#404040')
                    ax.spines['bottom'].set_color('#404040')

                    # Set tick colors for dark theme
                    ax.tick_params(axis='x', colors='#B0B0B0', rotation=45)
                    ax.tick_params(axis='y', colors='#B0B0B0')

                    plt.xticks(rotation=45, ha='right', fontsize=10)
                    plt.yticks(fontsize=10)

                    # Format y-axis with ₹ symbol
                    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'₹{int(x):,}'))

                    plt.tight_layout()
                    st.pyplot(fig)


# -------------------- PAGE: WEATHER & NEWS --------------------
def show_weather_news():
    st.header("🌤 Weather & 📰 News")

    # Weather Section
    st.subheader("🌤 Live Weather")
    city = st.text_input("City", "Bangalore")

    if st.button("Get Weather") and WEATHER_API_KEY:
        try:
            url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={WEATHER_API_KEY}&units=metric"
            response = requests.get(url).json()

            if response.get("cod") == 200:
                temp = response['main']['temp']
                humidity = response['main']['humidity']
                condition = response['weather'][0]['description'].title()

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("Temperature", f"{temp}°C")
                with col2:
                    st.metric("Humidity", f"{humidity}%")
                with col3:
                    st.write(f"**Condition:** {condition}")
            else:
                st.error("City not found")
        except:
            st.error("Weather service unavailable")

    st.markdown("---")

    # News Section
    st.subheader("📰 Latest News")

    if st.button("Get News") and NEWS_API_KEY:
        try:
            url = f"https://newsdata.io/api/1/news?apikey={NEWS_API_KEY}&q=india&language=en"
            response = requests.get(url).json()
            articles = response.get("results", [])[:5]

            for article in articles:
                st.write(f"**{article.get('title', 'No title')}**")
                st.write(f"_{article.get('description', '')}_")
                st.divider()
        except:
            st.error("News service unavailable")


# -------------------- PAGE: RESTAURANTS --------------------
def show_restaurants():
    st.header("🍽 Smart Restaurant Finder")

    rm = RestaurantManager(CSV_FILE)
    df = rm.load_data()

    if df.empty:
        st.error("Restaurant database not available")
        return

    # Smart suggestions section
    st.subheader("💡 Smart Suggestions")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.write("**Occasion-Based:**")
        occasions = ["Romantic Dinner", "Family Dinner", "Business Lunch",
                     "Birthday Party", "Quick Lunch", "Date Night"]
        occasion = st.selectbox("Select Occasion", occasions)

        if st.button("Find for Occasion"):
            suggestions = rm.get_occasion_suggestions(occasion)
            st.session_state.auto_search = suggestions[0]
            st.rerun()

    with col2:
        st.write("**Feeling Lucky:**")
        if st.button("🎲 I'm Feeling Lucky"):
            # Random but good restaurant
            good_restaurants = df[df['rating'] >= 4.0]
            if not good_restaurants.empty:
                random_rest = good_restaurants.sample(1).iloc[0]
                st.session_state.lucky_restaurant = random_rest
            else:
                st.session_state.lucky_restaurant = df.sample(1).iloc[0]
            st.rerun()

        if "lucky_restaurant" in st.session_state:
            r = st.session_state.lucky_restaurant
            st.success(f"**{r['name']}** ⭐ {r['rating']:.1f}")
            st.write(f"Cuisine: {r['cuisine']}")
            st.write(f"Address: {r['localAddress'][:50]}...")

    with col3:
        st.write("**Time-Based:**")
        hour = datetime.datetime.now().hour
        if 6 <= hour < 11:
            st.info("🍳 Breakfast Time")
            time_suggestion = "Breakfast"
        elif 11 <= hour < 15:
            st.info("🍽️ Lunch Time")
            time_suggestion = "Lunch"
        elif 15 <= hour < 18:
            st.info("☕ Evening Snacks")
            time_suggestion = "Snacks"
        else:
            st.info("🌙 Dinner Time")
            time_suggestion = "Dinner"

        if st.button(f"Find {time_suggestion}"):
            st.session_state.auto_search = time_suggestion
            st.rerun()

    st.markdown("---")

    # Main search
    st.subheader("🔍 Search Restaurants")

    # Use auto-search or manual input
    default_search = st.session_state.get("auto_search", "Indian")
    cuisine = st.text_input("Cuisine or Type", value=default_search)

    col1, col2 = st.columns([2, 1])
    with col1:
        min_rating = st.slider("Minimum Rating", 0.0, 5.0, 4.0, 0.1)

    with col2:
        price_filter = st.selectbox("Price Range", ["Any", "₹₹ (Budget)", "₹₹₹ (Moderate)", "₹₹₹₹ (Premium)"])

    if st.button("Search", type="primary"):
        # Filter by cuisine and rating
        mask = (df["cuisine"].str.contains(cuisine, case=False, na=False) |
                df["description"].str.contains(cuisine, case=False, na=False))
        mask &= df["rating"] >= min_rating

        results = df[mask]

        if results.empty:
            st.warning(f"No restaurants found for '{cuisine}'")

            # Suggest similar
            all_cuisines = df["cuisine"].str.split(",").explode().str.strip().unique()
            similar = [c for c in all_cuisines if cuisine.lower() in str(c).lower()]
            if similar:
                st.write("Try similar cuisines:")
                for sim in similar[:3]:
                    if st.button(f"🔍 {sim}"):
                        st.session_state.auto_search = sim
                        st.rerun()
        else:
            st.success(f"Found {len(results)} restaurants")

            # Sort and display
            results = results.sort_values("rating", ascending=False)

            for _, row in results.head(10).iterrows():
                with st.expander(f"{row['name']} ⭐ {row['rating']:.1f}"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write(f"**Address:** {row['localAddress']}")
                        st.write(f"**Phone:** {row['phone']}")
                        st.write(f"**Cuisine:** {row['cuisine']}")
                    with col2:
                        if pd.notna(row['description']):
                            st.write(f"**Description:** {row['description'][:150]}...")


# -------------------- MAIN APP --------------------
pages = {
    "🏠 Home": show_home,
    "📅 Reminders": show_reminders,
    "💰 Expenses": show_expenses,
    "🌤 Weather & News": show_weather_news,
    "🍽 Restaurants": show_restaurants
}

# Sidebar navigation
page_name = st.sidebar.radio("Navigate", list(pages.keys()))

# Show selected page
st.title("🧠 Smart Life Hub Dashboard")
pages[page_name]()