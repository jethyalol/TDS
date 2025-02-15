from datetime import datetime
from dateutil import parser

def count_wednesdays():
    input_file = "/data/dates.txt"
    output_file = "/data/dates-wednesdays.txt"

    try:
        with open(input_file, "r") as f:
            dates = f.readlines()

        wednesday_count = 0

        for date in dates:
            date = date.strip()
            if date:
                try:
                    parsed_date = parser.parse(date)  # Auto-detects format
                    if parsed_date.weekday() == 2:  # 2 = Wednesday
                        wednesday_count += 1
                except Exception as e:
                    print(f"Skipping invalid date: {date} - Error: {e}")

        with open(output_file, "w") as f:
            f.write(str(wednesday_count))

        return {"status": "success", "message": f"Counted {wednesday_count} Wednesdays."}

    except Exception as e:
        return {"status": "error", "message": str(e)}