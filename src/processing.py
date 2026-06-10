import csv

# Carrega os dados do CSV
def load_energy_data(file_path):
    records = []
    with open(file_path, "r", newline="") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            records.append(row)
    return records

# Produção diária total
def calculate_daily_production(records):
    daily_totals = {}
    for record in records:
        date = record["date"]
        quantity = int(record["production_mwh"])
        if date in daily_totals:
            daily_totals[date] += quantity
        else:
            daily_totals[date] = quantity
    return daily_totals

# Produção por fonte e região
def calculate_production_by_source_and_region(records):
    result = {}
    for record in records:
        date = record["date"]
        region = record["region"]
        source = record["energy_source"]
        quantity = int(record["production_mwh"])

        if date not in result:
            result[date] = {}
        if region not in result[date]:
            result[date][region] = {}
        result[date][region][source] = quantity
    return result

# Total de produção por fonte
def calculate_total_by_source(records):
    totals = {}
    for record in records:
        source = record["energy_source"]
        quantity = int(record["production_mwh"])
        if source in totals:
            totals[source] += quantity
        else:
            totals[source] = quantity
    return totals

# Total de produção por região
def calculate_total_by_region(records):
    totals = {}
    for record in records:
        region = record["region"]
        quantity = int(record["production_mwh"])
        if region in totals:
            totals[region] += quantity
        else:
            totals[region] = quantity
    return totals

# Média mensal
def calculate_monthly_average(records):
    monthly_totals = {}
    monthly_counts = {}

    for record in records:
        month = record["date"][:7]  # YYYY-MM
        quantity = int(record["production_mwh"])
        if month in monthly_totals:
            monthly_totals[month] += quantity
            monthly_counts[month] += 1
        else:
            monthly_totals[month] = quantity
            monthly_counts[month] = 1

    monthly_avg = {month: monthly_totals[month] // monthly_counts[month] for month in monthly_totals}
    return monthly_avg
