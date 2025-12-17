# filter_bangalore_csv.py
# Run: python filter_bangalore_csv.py

import pandas as pd

CSV_FILE = "Bengaluru_Restaurants.csv"  # change if your filename differs

def load_data():
    df = pd.read_csv(CSV_FILE)
    print("Columns in CSV:", list(df.columns))

    # If rating column is string, convert to float where possible
    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(df["rating"], errors="coerce")
    return df

def filter_restaurants(df, main_menu: str, min_rating: float):
    keyword = main_menu.strip().lower()

    # Filter by keyword in cuisine or name
    mask_keyword = df["cuisine"].fillna("").str.lower().str.contains(keyword) | \
                   df["name"].fillna("").str.lower().str.contains(keyword)

    # Filter by rating
    mask_rating = df["rating"].fillna(0) >= min_rating

    filtered = df[mask_keyword & mask_rating]
    return filtered

def main():
    print("=== Bengaluru Restaurant Filter (CSV) ===")
    main_menu = input("Enter main menu keyword (e.g., pizza): ").strip()
    rating_str = input("Enter minimum rating (e.g., 4.0): ").strip()

    try:
        min_rating = float(rating_str)
    except ValueError:
        min_rating = 0.0

    print("\nYour filters:")
    print(f'  main menu: "{main_menu}"')
    print(f'  rating: "{min_rating}+"')
    print()

    df = load_data()
    result = filter_restaurants(df, main_menu, min_rating)

    if result.empty:
        print("No restaurants matched these filters.")
        return

    print(f"Found {len(result)} restaurant(s):\n")

    MAX_SHOW = 20
    for _, row in result.head(MAX_SHOW).iterrows():
        name = row.get("name", "Unknown")
        address = row.get("address", "Bangalore")
        rating = row.get("rating", "NA")
        description = row.get("description", "")
        cuisine = row.get("cuisine", "")
        print(f"- {name}")
        print(f"  Address: {address}")
        print(f"  Rating: {rating}")
        print(f"  Description: {description}")
        print(f"  Cuisine: {cuisine}")
        print()

    if len(result) > MAX_SHOW:
        print(f"...and {len(result) - MAX_SHOW} more matching restaurants not shown.")

if __name__ == "__main__":
    main()