import pandas as pd
import numpy as np

def detailed_analysis():
    print("=" * 80)
    print("DETAILED GEORGIA WATER QUALITY DATA ANALYSIS")
    print("=" * 80)
    
    # Load key files
    print("Loading data files...")
    
    # Water Systems
    pws_df = pd.read_csv('data/SDWA_PUB_WATER_SYSTEMS.csv')
    
    # Violations
    violations_df = pd.read_csv('data/SDWA_VIOLATIONS_ENFORCEMENT.csv', low_memory=False)
    
    # Samples
    samples_df = pd.read_csv('data/SDWA_LCR_SAMPLES.csv')
    
    # Geographic
    geo_df = pd.read_csv('data/SDWA_GEOGRAPHIC_AREAS.csv')
    
    # Facilities
    facilities_df = pd.read_csv('data/SDWA_FACILITIES.csv')
    
    print("Analysis complete!")
    print()
    
    # 1. WATER SYSTEMS ANALYSIS
    print("1. WATER SYSTEMS OVERVIEW")
    print("-" * 40)
    active_systems = pws_df[pws_df['PWS_ACTIVITY_CODE'] == 'A']
    print(f"• Total water systems: {len(pws_df):,}")
    print(f"• Active systems: {len(active_systems):,}")
    print(f"• Inactive systems: {len(pws_df) - len(active_systems):,}")
    
    # System types
    system_types = active_systems['PWS_TYPE_CODE'].value_counts()
    print("\nSystem Types:")
    for sys_type, count in system_types.items():
        print(f"  - {sys_type}: {count:,}")
    
    # Population served
    total_pop = active_systems['POPULATION_SERVED_COUNT'].sum()
    avg_pop = active_systems['POPULATION_SERVED_COUNT'].mean()
    print(f"\nPopulation Served:")
    print(f"  - Total: {total_pop:,.0f}")
    print(f"  - Average per system: {avg_pop:,.0f}")
    
    # Source types
    source_types = active_systems['PRIMARY_SOURCE_CODE'].value_counts()
    print("\nWater Sources:")
    for source, count in source_types.items():
        print(f"  - {source}: {count:,}")
    
    print()
    
    # 2. VIOLATIONS ANALYSIS
    print("2. VIOLATIONS OVERVIEW")
    print("-" * 40)
    print(f"• Total violations: {len(violations_df):,}")
    
    # Violation categories
    violation_cats = violations_df['VIOLATION_CATEGORY_CODE'].value_counts()
    print("\nViolation Categories:")
    for cat, count in violation_cats.head(10).items():
        print(f"  - {cat}: {count:,}")
    
    # Health-based violations
    health_violations = violations_df[violations_df['IS_HEALTH_BASED_IND'] == 'Y']
    print(f"\nHealth-based violations: {len(health_violations):,}")
    
    # Violation status
    status_counts = violations_df['VIOLATION_STATUS'].value_counts()
    print("\nViolation Status:")
    for status, count in status_counts.items():
        print(f"  - {status}: {count:,}")
    
    print()
    
    # 3. SAMPLING DATA
    print("3. LEAD & COPPER SAMPLING")
    print("-" * 40)
    print(f"• Total samples: {len(samples_df):,}")
    
    # Contaminants
    contaminants = samples_df['CONTAMINANT_CODE'].value_counts()
    print("\nContaminants sampled:")
    for cont, count in contaminants.items():
        print(f"  - {cont}: {count:,}")
    
    # Sample measures (if available)
    if 'SAMPLE_MEASURE' in samples_df.columns:
        valid_measures = samples_df['SAMPLE_MEASURE'].dropna()
        if len(valid_measures) > 0:
            print(f"\nSample measurements:")
            print(f"  - Valid measurements: {len(valid_measures):,}")
            print(f"  - Average: {valid_measures.mean():.4f}")
            print(f"  - Max: {valid_measures.max():.4f}")
    
    print()
    
    # 4. GEOGRAPHIC COVERAGE
    print("4. GEOGRAPHIC COVERAGE")
    print("-" * 40)
    counties = geo_df[geo_df['AREA_TYPE_CODE'] == 'CN']['COUNTY_SERVED'].nunique()
    cities = geo_df[geo_df['AREA_TYPE_CODE'] == 'CT']['CITY_SERVED'].nunique()
    zip_codes = geo_df[geo_df['AREA_TYPE_CODE'] == 'ZC']['ZIP_CODE_SERVED'].nunique()
    
    print(f"• Counties covered: {counties}")
    print(f"• Cities covered: {cities}")
    print(f"• ZIP codes covered: {zip_codes}")
    
    # Top counties
    top_counties = geo_df[geo_df['AREA_TYPE_CODE'] == 'CN']['COUNTY_SERVED'].value_counts().head(5)
    print("\nTop counties by water systems:")
    for county, count in top_counties.items():
        print(f"  - {county}: {count}")
    
    print()
    
    # 5. FACILITIES ANALYSIS
    print("5. FACILITIES OVERVIEW")
    print("-" * 40)
    active_facilities = facilities_df[facilities_df['FACILITY_ACTIVITY_CODE'] == 'A']
    print(f"• Total facilities: {len(facilities_df):,}")
    print(f"• Active facilities: {len(active_facilities):,}")
    
    # Facility types
    facility_types = active_facilities['FACILITY_TYPE_CODE'].value_counts()
    print("\nTop facility types:")
    for ftype, count in facility_types.head(10).items():
        print(f"  - {ftype}: {count:,}")
    
    print()
    
    # 6. DATA QUALITY ASSESSMENT
    print("6. DATA QUALITY ASSESSMENT")
    print("-" * 40)
    
    # Missing data analysis
    print("Missing data percentages:")
    for col in ['PWS_NAME', 'POPULATION_SERVED_COUNT', 'EMAIL_ADDR', 'PHONE_NUMBER']:
        if col in pws_df.columns:
            missing_pct = (pws_df[col].isna().sum() / len(pws_df)) * 100
            print(f"  - {col}: {missing_pct:.1f}% missing")
    
    # Recent data
    print(f"\nData currency:")
    print(f"  - Submission quarter: {pws_df['SUBMISSIONYEARQUARTER'].iloc[0]}")
    print(f"  - Last reported dates range: {pws_df['LAST_REPORTED_DATE'].min()} to {pws_df['LAST_REPORTED_DATE'].max()}")
    
    print()
    print("=" * 80)
    print("DETAILED ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    detailed_analysis() 